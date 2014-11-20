
import datetime
import json
import lxc
import os
import pwd
import shutil
import socket
import stat
import subprocess
import time
import sys

from lxci import config

def error_message(*a, **kw):
    print(*a, file=sys.stderr, **kw)
    sys.stderr.flush()

def verbose_message(*a, **kw):
    if config.VERBOSE:
        print(*a, file=sys.stderr, **kw)
        sys.stderr.flush()

class timer_print():
    """
    Measure how long it takes to run the with block
    """
    def __init__(self, msg):
        verbose_message(msg + "...", end="")
    def __enter__(self):
        self.started = time.time()
    def __exit__(self, type, value, traceback):
        took = time.time() - self.started
        verbose_message("OK {}s".format(round(took, 2)))

def list_base_containers():
    return lxc.list_containers(config_path=config.BASE_CONFIG_PATH)

def list_runtime_containers():
    return lxc.list_containers(config_path=config.RUNTIME_CONFIG_PATH)

def list_archived_containers(return_object=False, tag=None):
    containers = []
    for name in lxc.list_containers(config_path=config.ARCHIVE_CONFIG_PATH):
        container = RuntimeContainer(lxc.Container(name, config_path=config.ARCHIVE_CONFIG_PATH))
        if tag and tag not in container.get_tags():
            continue
        if container.is_lxci_container():
            if return_object:
                containers.append(container)
            else:
                containers.append(name)
    return containers

def make_executable(filepath):
    """
    Like chmod +x filepath
    """
    st = os.stat(filepath)
    os.chmod(filepath, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


class RuntimeContainerError(Exception):
    "RuntimeContainer Error"

def assert_ret(val, msg=""):
    """
    Raise RuntimeContainerError if the return value is not true
    """
    if not val:
        raise RuntimeContainerError(msg)

prepare_header = """#!/bin/sh
exec >> /var/log/lxci-prepare.log
exec 2>&1
set -eux
"""

command_header = """#!/bin/sh
set -eu
cd /home/lxci/workspace
"""

class RuntimeContainer():

    def __init__(self, container):
        if isinstance(container, str):
            raise TypeError("Expected container to be instance of lxc.Container not string")
        self.container = container
        self._prepare_commands = []


    def __str__(self):
        meta = self.read_meta()
        return "{name} base={base} state={state} tag={tags} ".format(
            name=self.get_name(),
            state=self.container.state,
            tags=",".join(meta.get("tags", [])),
            base=meta.get("base")
        )

    def add_tags(self, tags):
        meta = self.read_meta()
        for t in tags:
            if t not in meta["tags"]:
                meta["tags"].append(t)

    def get_tags(self):
        return self.read_meta().get("tags", [])


    def get_name(self):
        return self.container.name


    def start(self):
        """
        Start the container and wait until the SSH server is available
        """

        if self.container.state == "STOPPED":
            self.prepare()

        with timer_print("Waiting for the container to boot"):
            if self.container.state != "RUNNING":
                assert_ret(self.container.start(), "Failed to start the runtime container")
                self.container.wait("RUNNING", 60)

        started = time.time()
        ips = tuple()
        with timer_print("Waiting for the container to get network"):
            while True:
                ips = self.container.get_ips()
                if len(ips) > 0:
                    break
                time.sleep(0.1)
                if time.time() - started > 10:
                    raise RuntimeContainerError("Timeout while waiting for container ip address")

        ip = ips[0]

        started = time.time()
        with timer_print("Waiting for the container SSH server to wake up"):
            while True:
                try:
                    socket.create_connection((ip, 22)).close()
                    break
                except Exception:
                    time.sleep(0.1)
                if time.time() - started > 10:
                    raise RuntimeContainerError("Timeout while waiting for container SSH server to wake up. Are you sure it is installed?")

    def write_env(self, env):
        """
        Append environment variables from the dict env to /etc/environment in the container
        """

        env_filepath = self.get_path("/etc/environment")

        with open(env_filepath, "a") as f:
            f.write('\n')
            for k, v in env.items():
                f.write('{k}="{v}"\n'.format(k=k, v=v))


    def get_rootfs_path(self):
        return self.container.get_config_item("lxc.rootfs")

    def get_results_src_path(self):
        return self.get_path("/home/lxci/results")

    def get_results_dest_path(self):
        return os.path.join(
            config.RESULTS_PATH,
            self.get_name()
        )

    def copy_results(self):
        with timer_print("Copying result artifacts to {}".format(self.get_results_dest_path())):
            # os.makedirs(self.get_results_dest_path(), exist_ok=True)
            shutil.copytree(
                self.get_results_src_path(),
                self.get_results_dest_path()
            )

    def has_results_files(self):
        return len(os.listdir(self.get_results_src_path())) > 0


    def sync_workspace(self, source_dir):

        # sudo users can only sync files from their home directory
        if "SUDO_UID" in os.environ:
            home_dir = pwd.getpwuid(int(os.environ["SUDO_UID"])).pw_dir
            if not os.path.realpath(source_dir).startswith(home_dir):
                raise RuntimeContainerError("Permission denied: sudo users can sync only their home directories")

        with timer_print("Synchronizing {} to the container".format(source_dir)):
            subprocess.check_call([
                "rsync",
                "-a",
                source_dir,
                self.get_path("/home/lxci/workspace"),
            ])

    def run_command(self, command):
        """
        Run given command in the container using SSH
        """
        command_filepath = self.get_path("/lxci/command.sh")

        with open(command_filepath, "w") as f:
            f.write(command_header)
            f.write("\n")
            f.write(command)

        make_executable(command_filepath)

        cmd = subprocess.Popen([
            "ssh",
            "-q", # Quiet mode
            "-t", # Force pseudo-tty allocation
            "-oStrictHostKeyChecking=no", # Skip the host key prompt
            "-i", config.SSH_KEY_PATH, # Use our ssh key
            "-l", "lxci", # Login as lxci user
            self.container.get_ips()[0],
            "/lxci/command.sh",
            ], pass_fds=os.pipe()
            # stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE
        )
        cmd.wait()
        return cmd

    def add_prepare_command(self, command):
        """
        Add a prepare command. It will be executed in the container as root
        before it is actually started
        """
        if self.container.state != "STOPPED":
            raise RuntimeContainerError("Can only prepare stopped containers")
        self._prepare_commands.append(command)

    def prepare(self):
        if self.container.state != "STOPPED":
            raise RuntimeContainerError("Can only prepare stopped containers")

        prepare_sh_path = "/tmp/lxci-prepare.sh"
        prepare_sh_path_fullpath = self.get_path(prepare_sh_path)

        with open(prepare_sh_path_fullpath, "w") as f:
            f.write(prepare_header)
            f.write("\n")
            for command in self._prepare_commands:
                f.write(command)
                f.write("\n")

        make_executable(prepare_sh_path_fullpath)
        assert_ret(
            self.container.start(useinit=False, daemonize=False, close_fds=False, cmd=(prepare_sh_path,)),
            "Failed to prepare the container. Check {rootfs}/var/log/lxci-prepare.log".format(rootfs=self.get_rootfs_path())
        )

    def get_path(self, path):
        """
        Convert container absolute path to host absolute path for the rootfs of
        the container
        """
        if path[0] == "/":
            path = path[1:]
        return os.path.join(self.get_rootfs_path(), path)

    def enable_sudo(self):
        """
        Enable passwordless sudo for lxci user
        """

        verbose_message("Enabling sudo for the lxci user")
        self.add_prepare_command("usermod -a -G sudo lxci")
        with open(self.get_path("/etc/sudoers"), "a") as f:
            f.write("%lxci ALL=(ALL) NOPASSWD: ALL\n")

    def get_meta_filepath(self):
        return self.get_path("/lxci/meta")

    def is_runtime_container(self):
        return os.path.exists(self.get_meta_filepath())

    def write_meta(self, meta):
        with open(self.get_meta_filepath(), "w") as f:
            json.dump(meta, f, sort_keys=True, indent=4)

    def read_meta(self):
        """
        Read meta data from the container

        returns dict
        """
        try:
            with open(self.get_meta_filepath(), "r") as f:
                return json.load(f) or {}
        except FileNotFoundError:
            return {}

    def add_meta(self, meta):
        """
        Merge dict into meta data
        """
        old = self.read_meta()
        old.update(meta)
        self.write_meta(old)


    def archive(self):
        """
        Archive the given container to ARCHIVE_CONFIG_PATH
        """

        archived_container = None
        self.stop()

        with timer_print("Archiving the container"):
            if config.RUNTIME_CONFIG_PATH == config.ARCHIVE_CONFIG_PATH:
                archived_container = self.container
            else:
                os.makedirs(config.ARCHIVE_CONFIG_PATH, exist_ok=True)
                archived_container = self.container.clone(
                    self.container.name,
                    config_path=config.ARCHIVE_CONFIG_PATH
                )
                assert_ret(archived_container, "Failed to archive the container")
                assert_ret(self.container.destroy(), "Failed to destroy the runtime container after archiving")


        return archived_container

    def is_lxci_container(self):
        """
        Return True if the container has been created by lxci
        """
        return os.path.exists(self.get_path("/lxci"))

    def stop(self):
        if self.container.state == "STOPPED":
            return
        with timer_print("Stopping the container"):
            assert_ret(self.container.stop(), "Failed to stop the container")
            self.container.wait("STOPPED", 60)

    def destroy(self):
        self.stop()
        if self.container.state != "STOPPED":
            error_message("Cannot destroy container {} since it's not stopped".format(self.get_name()))
            return

        with timer_print("Destroying container {}".format(self.get_name())):
            assert_ret(self.container.destroy())

def create_runtime_container(base_container_name, runtime_container_name):
    """
    Clone the base container and create lxci user for it
    """

    base_container = lxc.Container(base_container_name, config_path=config.BASE_CONFIG_PATH)
    os.makedirs(config.RUNTIME_CONFIG_PATH, exist_ok=True)

    container = None
    with timer_print("Creating container '{runtime}' using '{base}'".format(runtime=runtime_container_name, base=base_container_name)):
        container = base_container.clone(
            runtime_container_name,
            config_path=config.RUNTIME_CONFIG_PATH
        )
        assert_ret(container, "Error while creating the runtime container")

    runtime_container =  RuntimeContainer(container)

    # Create lxci directory
    os.makedirs(runtime_container.get_path("/lxci"), exist_ok=True)
    os.makedirs(runtime_container.get_path("/home/lxci/.ssh"))
    os.makedirs(runtime_container.get_path("/home/lxci/results"))
    os.makedirs(runtime_container.get_path("/home/lxci/workspace"))

    runtime_container.add_prepare_command("adduser --system --uid 555 --shell /bin/bash --group lxci")
    runtime_container.add_prepare_command("echo -n 'lxci:lxci' | chpasswd")
    # Ensure the user can read everything in home
    runtime_container.add_prepare_command("chown -R lxci:lxci /home/lxci")

    shutil.copyfile(
        config.SSH_PUB_KEY_PATH,
        runtime_container.get_path("/home/lxci/.ssh/authorized_keys")
    )

    runtime_container.add_meta({
        "base": base_container_name,
        "created": datetime.datetime.now().isoformat(),
    })
    return runtime_container

