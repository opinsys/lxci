
import datetime
import json
import lxc
import os
import shutil
import socket
import stat
import subprocess
import time
import sys

from lxci import config

def error_message(*a):
    print(*a, file=sys.stderr)

def verbose_message(*a):
    if config.VERBOSE:
        print(*a, file=sys.stderr)

class timer_print():
    """
    Measure how long it takes to run the with block
    """
    def __init__(self, msg):
        if config.VERBOSE:
            print(msg + "... ", end="", flush=True)
    def __enter__(self):
        self.started = time.time()
    def __exit__(self, type, value, traceback):
        took = time.time() - self.started
        verbose_message("OK {}s".format(round(took, 2)))
        sys.stdout.flush()

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
        if container.is_archived():
            if return_object:
                containers.append(container)
            else:
                containers.append(name)
    return containers

def clear_archive():
    """
    Destroy all stopped containers in archive
    """
    containers = lxc.list_containers(config_path=config.ARCHIVE_CONFIG_PATH)

    with timer_print("Destroying {} archived containers".format(len(containers))):
        for name in  containers:
            container = lxc.Container(name, config_path=config.ARCHIVE_CONFIG_PATH)
            if container.state == "STOPPED" and RuntimeContainer(container).is_archived():
                assert_ret(container.destroy())

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

class RuntimeContainer():

    def __init__(self, container):
        if isinstance(container, str):
            raise TypeError("Expected container to be instance of lxc.Container not string")
        self.container = container

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

        with timer_print("Waiting for the container to boot"):
            if self.container.state != "RUNNING":
                assert_ret(self.container.start(), "Failed to start the runtime container")
                self.container.wait("RUNNING", 60)

        ips = tuple()
        with timer_print("Waiting for the container to get network"):
            while True:
                ips = self.container.get_ips()
                if len(ips) > 0:
                    break
                time.sleep(0.1)

        ip = ips[0]

        with timer_print("Waiting for the container SSH server to wake up"):
            while True:
                try:
                    socket.create_connection((ip, 22)).close()
                    break
                except Exception:
                    time.sleep(0.1)

    def write_env(self, env):
        """
        Append environment variables from the dict env to /etc/environment in the container
        """

        env_filepath = os.path.join(
            self.get_rootfs_path(),
            "etc/environment"
        )

        with open(env_filepath, "a") as f:
            f.write('\n')
            for k, v in env.items():
                f.write('{k}="{v}"\n'.format(k=k, v=v))


    def get_rootfs_path(self):
        return self.container.get_config_item("lxc.rootfs")

    def sync_workspace(self, source_dir):
        workspace_dirpath = os.path.join(
            self.get_rootfs_path(),
            "home/lxci/workspace"
        )

        with timer_print("Synchronizing {} to the container".format(source_dir)):
            subprocess.check_call([
                "rsync",
                "-a",
                source_dir,
                workspace_dirpath
            ])

    def run_command(self, command):
        """
        Run given command in the container using SSH
        """
        command_filepath = os.path.join(
            self.get_rootfs_path(),
            "lxci_command.sh"
        )

        with open(command_filepath, "w") as f:
            f.write("""
#!/bin/sh
set -eu
sudo chown -R lxci:lxci /home/lxci/workspace
cd /home/lxci/workspace
{command}
""".format(command=command))
        make_executable(command_filepath)

        cmd = subprocess.Popen([
            "ssh",
            "-q", # Quiet mode
            "-t", # Force pseudo-tty allocation
            "-oStrictHostKeyChecking=no", # Skip the host key prompt
            "-i", config.SSH_KEY_PATH, # Use our ssh key
            "-l", "lxci", # Login as lxci user
            self.container.get_ips()[0],
            "/lxci_command.sh",
            ], pass_fds=os.pipe()
            # stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE
        )
        cmd.wait()
        return cmd

    def get_meta_filepath(self):
        return os.path.join(
            self.get_rootfs_path(),
            "lxci.json"
        )

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

    def get_archive_flag_path(self):
        return os.path.join(
            self.get_rootfs_path(),
            "lxci_archived"
        )

    def archive(self):
        """
        Archive the given container to ARCHIVE_CONFIG_PATH
        """

        archived_container = None
        self.stop()

        with timer_print("Archiving the container"):
            with open(self.get_archive_flag_path(), "w") as f:
                f.write(datetime.datetime.now().isoformat())

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

    def is_archived(self):
        """
        Return True if the container has been once archived
        """
        return os.path.exists(self.get_archive_flag_path())

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
    with timer_print("Creating container '{runtime}' from the '{base}' container".format(runtime=runtime_container_name, base=base_container_name)):
        container = base_container.clone(
            runtime_container_name,
            config_path=config.RUNTIME_CONFIG_PATH
        )
        assert_ret(container, "Error while creating the runtime container")

    rootfs_path = container.get_config_item("lxc.rootfs")
    setup_sh_path = os.path.join(
        container.get_config_item("lxc.rootfs"),
        "lxci_prepare.sh"
    )

    with open(setup_sh_path, "w") as f:
        f.write("""
#!/bin/sh
exec >> /var/log/lxci_prepare.log
exec 2>&1
set -eux
adduser --system --shell /bin/bash --group lxci
echo -n 'lxci:lxci' | chpasswd
usermod -a -G sudo lxci
echo "%lxci ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
mkdir /home/lxci/.ssh
mkdir /home/lxci/workspace
    """)

    make_executable(setup_sh_path)

    res = None
    with timer_print("Preparing the container"):
        res = container.start(False, False, False, ("/lxci_prepare.sh",))
    if not res:
        raise Exception(
            "Failed to prepare the container. Check {rootfs}/var/log/lxci_prepare.log".format(rootfs=rootfs_path)
        )

    shutil.copyfile(
        config.SSH_PUB_KEY_PATH,
        os.path.join(rootfs_path, "home/lxci/.ssh/authorized_keys")
    )

    runtime_container =  RuntimeContainer(container)
    runtime_container.add_meta({
        "base": base_container_name,
        "created": datetime.datetime.now().isoformat(),
    })
    return runtime_container

