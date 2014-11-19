
# lxCI

Run commands in temporary containers

    lxci trusty-amd64

This will do following

1. Creates a new temporary container based on the existing `trusty-amd64` container
  - Create it with `sudo lxc-create -t download -n trusty-amd64 -- --dist ubuntu --release trusty --arch amd64` and install openssh-server in it
2. Adds user `lxci` to it
3. Boots and waits for the network and ssh server to wake up in it
4. Logins as the `lxci` user over ssh and starts `bash`
5. After the bash command exists the container is destroyed

> Add `-v` to see details

To execute custom command instead of bash use `--command COMMAND`

    lxci trusty-amd64 --command hostname

To copy files into the container workspace use `--sync-workspace PATH`

    lxci trusty-amd64 --command "ls -l" --sync-workspace .

To archive the container on failures add `--archive-on-fail`

    lxci trusty-amd64 --command "exit 2" --archive-on-fail

The archived containers can be listed with `--list-archive`

    lxci --list-archive

To inspect an archived container use `--inspect NAME`

    lxci --inspect NAME

> This will start an interactive shell session in it

To list all other options use `--help`

    lxci --help

## Installation

todo

## Workflow with Continuous Integration Systems

todo

### Artifacts

todo

## Making it ridiculously fast with tmpfs

Do you think SSDs are fast?

## Security

Not.

http://www.slideshare.net/jpetazzo/is-it-safe-to-run-applications-in-linux-containers

## todo

- --sudo
- SUDO\_USER check
- artifacts

