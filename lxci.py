
import datetime
import json
import lxc
import os
import shutil
import socket
import stat
import subprocess
import time

import config

def list_base_containers():
    return lxc.list_containers(config_path=config.BASE_CONFIG_PATH)

def list_runtime_containers():
    return lxc.list_containers(config_path=config.RUNTIME_CONFIG_PATH)

def list_archived_containers():
    containers = []
    for name in lxc.list_containers(config_path=config.ARCHIVE_CONFIG_PATH):
        container = RuntimeContainer(lxc.Container(name, config_path=config.ARCHIVE_CONFIG_PATH))
        if container.is_archived():
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
        if config.VERBOSE:
            print("OK {}s".format(round(took, 2)), flush=True)

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
        self.container = container

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
        source_dir = os.path.realpath(source_dir) + "/"

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

    def get_metadata_filepath(self):
        return os.path.join(
            self.get_rootfs_path(),
            "lxci.json"
        )

    def write_metadata(self, meta):
        with open(self.get_metadata_filepath(), "w") as f:
            json.dump(meta, f)

    def read_metadata(self):
        with open(self.get_metadata_filepath(), "r") as f:
            return json.load(f)


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
        with timer_print("Stopping the container"):
            if self.container.state == "STOPPED":
                return
            assert_ret(self.container.stop(), "Failed to stop the container")
            self.container.wait("STOPPED", 60)

    def destroy(self):
        with timer_print("Destroying the container"):
            assert_ret(self.container.destroy())

def create_runtime_container(base_container_name, runtime_container_name):
    """
    Clone the base container and create lxci user for it
    """

    base_container = lxc.Container(base_container_name)

    container = None
    with timer_print("Cloning base container"):
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

    return RuntimeContainer(container)

