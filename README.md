
# lxCI

Run commands in temporary containers

    lxci trusty-amd64

This will do following

1. Creates a new temporary container based on the existing `trusty-amd64` container<sup>1</sup>
2. Adds user `lxci` to it
3. Boots and waits for the network and ssh server to wake up in it
4. Logins as the `lxci` user over ssh and starts `bash`
5. After the bash command exists the container is destroyed

> Add `-v` to see details


> <sup>1</sup> Create it with `sudo lxc-create -t download -n trusty-amd64 -- --dist ubuntu --release trusty --arch amd64` and install openssh-server into it


To execute custom command instead of bash use `--command COMMAND`

    lxci trusty-amd64 --command hostname

To copy files into the container workspace use `--sync PATH`

    lxci trusty-amd64 --command "ls -l" --sync .

To archive the container on failures add `--archive-on-fail`

    lxci trusty-amd64 --command "exit 2" --archive-on-fail

The archived containers can be listed with `--list-archive`

    lxci --list-archive

To inspect an archived container use `--inspect NAME`

    lxci --inspect NAME

> This will start an interactive shell session in it

To list all other options use `--help`

    lxci --help

### Artifacts

Place any files to `/home/lxci/results` in the container and they will be
copied to `/var/lib/lxci-results/NAME` on the host. Where `NAME` is the name of
the temporary container. Set it with `--name`.

## Installation

todo

### Making it ridiculously fast with tmpfs

Do you think SSDs are fast?

### Configuration

## Workflow with Continuous Integration Systems

todo

### Try it with Vagrant

If you have [Vagrant](https://www.vagrantup.com/) installed just clone this repository and type

    vagrant up

It will create an Ubuntu 14.04.1 LTS (Trusty Tahr) virtual machine with Jenkins
(port 8080), LXC and lxCI ready to go.

## Security

Not.

http://www.slideshare.net/jpetazzo/is-it-safe-to-run-applications-in-linux-containers

## todo

- generate keys
- disable pw

