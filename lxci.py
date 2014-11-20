#!/usr/bin/env python3
import argparse
import sys
import datetime
import atexit
import lxc
import os
import json

import lxci
from lxci import config, error_message, verbose_message

SCRIPT_NAME = os.path.basename(sys.argv[0])

parser = argparse.ArgumentParser(
    description="lxCI - Run commands in temporary containers",
    epilog="Use environment variable LXCI_CONFIG to set custom path to configuration file"
)
parser.add_argument("base_container", metavar="BASE_CONTAINER", nargs="?", help="base container to use. Use [sudo] lxc-ls to list available containers.")
parser.add_argument("-c", "--command", metavar="COMMAND", default="bash", dest="command", help="shell command to be executed in the container. If set to - the command will be read from the stdin. DEFAULT: bash")
parser.add_argument("-n", "--name",  metavar="NAME", dest="name", help="custom name for the temporary runtime container")
parser.add_argument("-t", "--tag",  metavar="TAG", dest="tag", help="tag container with TAG")
parser.add_argument("-s", "--sync",  metavar="DIR", dest="workspace_source_dir", help="synchronize DIR to the container. The trailing slash works like in rsync. If it is present the contents of the DIR is synchronized to the current working directory command. If not the directory itself is synchronized.")
parser.add_argument("-A", "--archive", dest="archive", action="store_true", help="archive the container after running the command")
parser.add_argument("-a", "--archive-on-fail", dest="archive_on_fail", action="store_true", help="archive the container only if the command returns with non zero exit status")
parser.add_argument("-l", "--list-archive", dest="list_archive", action="store_true", help="list archived containers. Combine --verbose to see tags and filter list with --tag TAG")
parser.add_argument("-m", "--info", metavar="NAME", dest="info", help="display meta data of an archived container")
parser.add_argument("-D", "--destroy-archive", dest="destroy_archive", action="store_true", help="destroy all archived containers. Combine with --tag TAG to destroy only the containers with the TAG")
parser.add_argument("-d", "--destroy-archive-on-success", dest="destroy_on_ok", action="store_true", help="destroy archived containers on success. If --tag is set only the containers with matching tags will bee destroyed")
parser.add_argument("-i", "--inspect",  metavar="NAME", dest="inspect", help="start bash in the archived container for inspection")
parser.add_argument("-E", "--copy-env",  metavar="ENV", dest="copy_env", help="copy comma separated environment variables to the container")
parser.add_argument("-e", "--set-env", metavar="ENV", nargs="*", dest="set_env", help="Set environment variable for the container. Example FOO=bar")
parser.add_argument("--print-config", dest="print_config", action="store_true", help="print config")
parser.add_argument("-V", "--version", dest="version", action="store_true", help="print lxci version")
parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", help="be verbose")


def die(*a):
    error_message(*a)
    sys.exit(2)


def inspect(args):
    if not args.inspect in lxci.list_archived_containers():
        die("Unknown container {}. See --list-archive".format(args.inspect))
    container = lxci.RuntimeContainer(lxc.Container(args.inspect, config_path=config.ARCHIVE_CONFIG_PATH))
    container.start()
    cmd = container.run_command("bash")
    container.stop()
    sys.exit(cmd.returncode)

def info(args):
    if not args.info in lxci.list_archived_containers():
        die("{} is not an archived container. See --list-archive".format(args.base_container))
    c = lxci.RuntimeContainer(lxc.Container(args.info))
    print(json.dumps(c.read_meta(), sort_keys=True, indent=4))

def destroy_archive(args):
    containers = lxci.list_archived_containers(return_object=True, tag=args.tag)

    if len(containers) == 0:
        verbose_message("No containers matched with tag {}. Check -lv".format(args.tag))
        return

    for c in containers:
        c.destroy()

def list_archive(args):
    containers = lxci.list_archived_containers(return_object=True, tag=args.tag)

    if (len(containers) == 0):
        verbose_message("Archive is empty")
        return

    for c in containers:
        if config.VERBOSE:
            print(c)
        else:
            print(c.get_name())

def main():
    args = parser.parse_args()
    config.VERBOSE = args.verbose
    env = {}

    if args.print_config:
        for key in dir(config):
            if key.isupper():
                print("{k} = {v}".format(k=key, v=getattr(config, key)))
        return

    if args.version:
        print(config.VERSION)
        sys.exit(0)

    if args.command == "-":
        args.command = sys.stdin.read()

    if args.list_archive:
        return list_archive(args)

    if args.inspect:
        return inspect(args)

    if args.info:
        return info(args)

    if args.copy_env:
        env_keys = args.env.split(",")
        env = env.merge({k:v for k,v in os.environ.items() if k in env_keys})

    if args.set_env:
        for pair in args.set_env:
            if not "=" in pair:
                die("Invalid --set-env value: {}".format(pair))
            k, v = pair.split("=")
            env[k] = v

    if args.destroy_archive:
        return destroy_archive(args)

    if not args.base_container:
        die("BASE_CONTAINER not defined. See [sudo] lxc-ls")

    if not args.name:
        args.name = args.base_container + "-runtime-" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    if not args.base_container in lxci.list_base_containers():
        die("Unknown base container {}".format(args.base_container))

    if args.name in lxci.list_runtime_containers():
        die("Container name {} already exists".format(args.name))

    runtime_container = lxci.create_runtime_container(
        args.base_container, args.name
    )
    runtime_container.add_meta({
        "command": args.command,
        "tags": (args.tag or "default").split(","),
    })

    did_fail = False

    def on_exit():
        archive = args.archive or (did_fail and args.archive_on_fail)

        if archive:
            runtime_container.archive()
        else:
            runtime_container.destroy()
        if did_fail:
            print("Command failed in the container with exit status {status}".format(status=cmd.returncode))
            if archive:
                print(
                    "You may inspect what went wrong with: [sudo] {SCRIPT_NAME} --inspect {name}".format(
                    SCRIPT_NAME=SCRIPT_NAME, name=runtime_container.get_name())
                )

    atexit.register(on_exit)


    if len(env) > 0:
        runtime_container.write_env(env)


    if args.workspace_source_dir:
        runtime_container.sync_workspace(args.workspace_source_dir)

    runtime_container.start()
    runtime_container.add_meta({ "started": datetime.datetime.now().isoformat() })
    cmd = runtime_container.run_command(args.command)
    did_fail = cmd.returncode != 0
    runtime_container.stop()
    runtime_container.add_meta({
        "stopped": datetime.datetime.now().isoformat(),
        "exit_code": cmd.returncode,
    })
    if not did_fail and args.destroy_on_ok:
        destroy_archive(args)

    sys.exit(cmd.returncode)


if __name__ == "__main__":
    main()


