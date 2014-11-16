import argparse
import sys
import datetime
import atexit
import lxc
import os

import config
import lxci

SCRIPT_NAME = os.path.basename(sys.argv[0])

parser = argparse.ArgumentParser(description="Run command in a temporary LXC container")
parser.add_argument("base_container", metavar="BASE_CONTAINER", nargs="?", help="Base container to use. Use lxc-ls to list available containers")
parser.add_argument("command", metavar="COMMAND", default="bash", nargs="?", help="Command to run in the container. Defaults to bash")
parser.add_argument("-n", "--name",  metavar="NAME", dest="name", help="Name for the temporary runtime container")
parser.add_argument("-t", "--tag",  metavar="TAG", dest="tag", help="Add tag for the runtime container")
parser.add_argument("-s", "--sync-workspace",  metavar="DIR", dest="workspace_source_dir", help="Synchronize DIR to the container")
parser.add_argument("-A", "--archive", dest="archive", action="store_true", help="Archive container after running the command")
parser.add_argument("-a", "--archive-on-fail", dest="archive_on_fail", action="store_true", help="Archive container after running the command only if the command retuns with non zero exit status")
parser.add_argument("-l", "--list-archive", dest="list_archive", action="store_true", help="List archived containers")
parser.add_argument("-c", "--clear-archive", dest="clear_archive", action="store_true", help="Clear all archived containers")
parser.add_argument("-i", "--inspect",  metavar="NAME", dest="inspect", help="Start bash in the archived container inspection")
parser.add_argument("-E", "--copy-env",  metavar="ENV", dest="copy_env", help="Copy comma separated environment variables to the container")
parser.add_argument("-e", "--set-env", metavar="ENV", nargs="*", dest="set_env", help="Set environment variable for the container. Can be set multiple times. Example FOO=bar")
parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", help="Be verbose")

def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)

def inspect(args):
    if not args.inspect in lxci.list_base_containers():
        die("Unknown base container {}. See --list-archive".format(args.base_container))
    container = lxci.RuntimeContainer(lxc.Container(args.inspect, config_path=config.ARCHIVE_CONFIG_PATH))
    container.start()
    cmd = container.run_command("bash")
    container.stop()
    sys.exit(cmd.returncode)



def main():
    args = parser.parse_args()
    print(args)
    config.VERBOSE = args.verbose


    if args.list_archive:
        print(" ".join(lxci.list_archived_containers()))
        sys.exit(0)

    if args.inspect:
        return inspect(args)

    if args.clear_archive:
        lxci.clear_archive()
        sys.exit(0)

    if not args.base_container:
        die("BASE_CONTAINER not defined. See --help")

    if not args.name:
        args.name = args.base_container + "-runtime-" + datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    if not args.base_container in lxci.list_base_containers():
        die("Unknown base container {}".format(args.base_container))

    if args.name in lxci.list_runtime_containers():
        die("Container name {} already exists".format(args.name))

    runtime_container = lxci.create_runtime_container(
        args.base_container, args.name
    )

    cmd = None

    def on_exit():
        did_fail = cmd and cmd.returncode != 0
        archive = args.archive or (did_fail and args.archive_on_fail)

        if archive:
            runtime_container.archive()
        else:
            runtime_container.destroy()
        if did_fail:
            print("Command failed with exit status {status}".format(status=cmd.returncode))
            if archive:
                print(
                    "You may inspect what went wrong with {SCRIPT_NAME} --inspect {name}".format(
                    SCRIPT_NAME=SCRIPT_NAME, name=runtime_container.get_name())
                )

    atexit.register(on_exit)

    if args.copy_env:
        env_keys = args.env.split(",")
        env = {k:v for k,v in os.environ.items() if k in env_keys}
        runtime_container.write_env(env)

    if args.set_env:
        env = {}
        for pair in args.set_env:
            if not "=" in pair:
                die("Invalid set env value in {}".format(pair))
            k, v = pair.split("=")
            env[k] = v
        runtime_container.write_env(env)

    if args.workspace_source_dir:
        runtime_container.sync_workspace(args.workspace_source_dir)

    runtime_container.start()
    runtime_container.write_metadata({
        "tags": (args.tag or "default").split(","),
        "command": args.command
    })
    cmd = runtime_container.run_command(args.command)
    runtime_container.stop()
    sys.exit(cmd.returncode)


if __name__ == "__main__":
    main()


