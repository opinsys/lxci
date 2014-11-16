
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


def make_executable(filepath):
    """
    Like chmod +x filepath
    """
    st = os.stat(filepath)
    os.chmod(filepath, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

# def list_archived_containers():
#     return lxc.list_containers(config_path=config.)


# def list_archived_containers():
# 
#     res = []
#     for name in lxc.list_containers(config_path=config.ARCHIVE_CONFIG_PATH):
#         container = lxc.Container(name)
#         vahh
# 
#     res


class timer_print():
    """
    Measure how long it takes to run the with block
    """
    def __init__(self, msg):
        print(msg + "... ", end="", flush=True)
    def __enter__(self):
        self.started = time.time()
    def __exit__(self, type, value, traceback):
        took = time.time() - self.started
        print("OK {}s".format(round(took, 2)), flush=True)


class RuntimeContainer():

    def __init__(self, container):
        self.container = container


    def start(self):
        """
        Start the container and wait until the SSH server is available
        """

        with timer_print("Waiting for the container to boot"):
            if self.container.state != "RUNNING":
                self.container.start()
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

    def run_command(self, command):
        """
        Run given command in the container using SSH
        """
        command_filepath = os.path.join(
            self.container.get_config_item("lxc.rootfs"),
            "lxci_command.sh"
        )

        with open(command_filepath, "w") as f:
            f.write("""
#!/bin/sh
set -eu
{command}
""".format(command=command))
        make_executable(command_filepath)

        cmd = subprocess.Popen([
            "ssh",
            "-t",
            "-oStrictHostKeyChecking=no",
            "-i", config.SSH_KEY_PATH,
            "-l", "lxci",
            self.container.get_ips()[0],
            "/lxci_command.sh",
            ], pass_fds=os.pipe()
            # stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE
        )
        cmd.wait()
        return cmd

    def get_metadata_filepath(self):
        return os.path.join(
            self.container.get_config_item("lxc.rootfs"),
            "lxci.json"
        )

    def write_metadata(self, meta):
        with open(self.get_metadata_filepath(), "w") as f:
            json.dump(meta, f)

    def read_metadata(self):
        with open(self.get_metadata_filepath(), "r") as f:
            return json.load(f)


    def archive(self):
        """
        Archive the given container to ARCHIVE_CONFIG_PATH
        """

        archived_container = None

        with timer_print("Archiving the container"):
            if config.RUNTIME_CONFIG_PATH == config.ARCHIVE_CONFIG_PATH:
                archived_container = self.container
            else:
                archived_container = self.container.clone(
                    self.container.name,
                    config_path=config.ARCHIVE_CONFIG_PATH
                )
                self.container.destroy()

            archive_flag_path = os.path.join(
                archived_container.get_config_item("lxc.rootfs"),
                "lxci_archived"
            )
            with open(archive_flag_path, "w") as f:
                f.write(datetime.datetime.now().isoformat())

        return archived_container


    def stop(self):
        with timer_print("Stopping the container"):
            if self.container.state == "STOPPED":
                return
            self.container.stop()
            self.container.wait("STOPPED", 60)

    def destroy(self):
        with timer_print("Destroying the container"):
            self.container.destroy()

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

    rootfs_path = container.get_config_item("lxc.rootfs")
    setup_sh_path = os.path.join(
        container.get_config_item("lxc.rootfs"),
        "lxci_setup.sh"
    )

    with open(setup_sh_path, "w") as f:
        f.write("""
#!/bin/sh
set -eu
adduser --system --shell /bin/bash --group lxci
echo -n 'lxci:lxci' | chpasswd
usermod -a -G sudo lxci
echo "%lxci ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
mkdir /home/lxci/.ssh
    """)

    make_executable(setup_sh_path)

    res = None
    with timer_print("Preparing the container"):
        res = container.start(False, False, False, ("/lxci_setup.sh",))
    if not res:
        raise Exception("Failed to prepare the container")

    shutil.copyfile(
        config.SSH_PUB_KEY_PATH,
        os.path.join(rootfs_path, "home/lxci/.ssh/authorized_keys")
    )

    return RuntimeContainer(container)

