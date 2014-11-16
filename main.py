import argparse
import sys
import datetime
import atexit

import lxci

parser = argparse.ArgumentParser(description="Run command in a temporary LXC container")
parser.add_argument("base_container", metavar="BASE_CONTAINER", help="Base container to use. Use lxc-ls to list")
parser.add_argument("command", metavar="COMMAND", help="Command to run in the container")
parser.add_argument("-n", "--name",  metavar="NAME", dest="name", help="Name for the temporary runtime container")
parser.add_argument("-t", "--tag",  metavar="TAG", dest="tag", help="Add tag for the runtime container")
parser.add_argument("-A", "--archive", dest="archive", action="store_true", help="Archive container after running the command")
parser.add_argument("-a", "--archive-on-fail", dest="archive_on_fail", action="store_true", help="Archive container after running the command only if the command retuns with non zero exit status")

def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)

def main():
    args = parser.parse_args()

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
        if args.archive:
            runtime_container.archive()
        elif cmd and cmd.returncode != 0 and args.archive_on_fail:
            runtime_container.archive()
        else:
            runtime_container.destroy()

    atexit.register(on_exit)

    runtime_container.start()
    runtime_container.write_metadata({
        "tags": (args.tag or "default").split(","),
        "command": args.command
    })
    cmd = runtime_container.run_command(args.command)
    print("Exit status {}".format(cmd.returncode))
    runtime_container.stop()
    sys.exit(cmd.returncode)


if __name__ == "__main__":
    main()


