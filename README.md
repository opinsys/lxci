
# lxCI

Run commands in temporary containers

    lxci trusty-amd64

This will do following

1. Creates a new temporary container based on the existing `trusty-amd64` container<sup>1</sup>
2. Adds user `lxci` to it
3. Boots and waits for the network and ssh server to wake up in it
4. Logins as the `lxci` user over ssh and starts `bash`
5. After the bash command exists the container is destroyed

add `-v` to see details

<sup>1</sup> Create it with `sudo lxc-create -t download -n trusty-amd64 -- --dist ubuntu --release trusty --arch amd64` and install openssh-server into it


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
copied to `/var/lib/lxci/results/NAME` on the host. Where `NAME` is the name of
the temporary container. Set it with `--name`.

### Workflow with Continuous Integration Systems

lxcCI works really well with Continuous Integration Systems such as Jenkins. We
use it like this with the Jenkins "Execute shell" build

```shell
lxci --name "$JOB_NAME-$BUILD_NUMBER" \
    --tag $JOB \
    --archive-on-fail \
    --destroy-archive-on-success \
    --sync . \
    --command "sh ci.sh"

aptirepo-upload "/var/lib/lxci/results/$JOB_NAME-$BUILD_NUMBER/"*.deb
rm -r "/var/lib/lxci/results/$JOB_NAME-$BUILD_NUMBER/"
```

The `$JOB_NAME` and `$BUILD_NUMBER` are build specific environment variables
set by Jenkins.

`--name "$JOB_NAME-$BUILD_NUMBER"` sets the temporary container name

`--tag $JOB` tags the container with the job name so multiple builds of the
same project can be grouped together

`--archive-on-fail` archives the temporary container with the given name if the
build fails for later investigation

`--destroy-archive-on-success` destroys the archived containers with matching
tags when build succeeds. Automatic clean up!

`--sync .` copies the Jenkins project workspace in into the container

`--command "sh ci.sh"` executes the actual build script which is versioned
within the project

[`aptirepo-upload`](https://github.com/opinsys/aptirepo) is used to upload the build artifacts to our apt repository

and finally the build artifacts are removed with plain old `rm`

## Installation

lxCI is tested only on Ubuntu 14.04.1 LTS (Trusty Tahr) but in theory there
is no reason why it wouldn't work on other distros with recent enough LXC.

Dependencies

    apt-get install lxc python3-lxc rsync

And then just install it using the Makefile

    sudo make install


### Ubuntu packages

We have those. Docs coming soon.

### Configuration

In `/etc/lxci/config`

Default values are following

```
RUNTIME_CONFIG_PATH = /var/lib/lxci/runtime
ARCHIVE_CONFIG_PATH = /var/lib/lxci/archive
RESULTS_PATH = /var/lib/lxci/results

SSH_KEY_PATH = /etc/lxci/key
SSH_PUB_KEY_PATH = /etc/lxci/key.pub
```

### Making it fast with RAM disks

Do you think SSDs are fast? Well, RAM kicks SSDs ass!

As you can see lxCI uses different paths for the base, runtime and archived
containers. This means we can use different file systems on each.

Fun trick is to mount `tmpfs` or `ramfs` on `/var/lib/lxci/runtime` which
causes the containers to be executed entirely in RAM. This means there will be
no disk I/O involved when doing builds in it. Depending on your project this
can be anything from small to epic speed up.

To use it add

    none                                           /var/lib/lxci/runtime    tmpfs   size=5g        0       0

or

    none                                           /var/lib/lxci/runtime    tmpfs   defaults        0       0


to `/etc/fstab` and reload it in with `mount -a`.

This will if course require some RAM from the host machine. For example booting
Ubuntu Trusty without any extra packages installed takes around 400M of RAM
from the mount in addition to RAM used by the processes it creates.

However the RAM usage can be reduced by using overlayfs based snapshot cloning
(copy on write)

    lxci trusty-amd64 --snapshot --backingstore overlayfs

This way RAM is used only when you write something to the disk in the
container. Read operations will still hit the disk but it can be a good middle
ground.

Nice side effect of this is that the container creations becomes almost instant
since nothing is copied.

#### `tmpfs` vs. `ramfs`

Read this http://www.jamescoyle.net/knowledge/951-the-difference-between-a-tmpfs-and-ramfs-ram-disk

tl;dr `tmpfs` is a lot safer but `ramfs` can be faster since it does not use swap
ever.


### Try it with Vagrant

If you have [Vagrant](https://www.vagrantup.com/) installed just clone this
repository and type

    vagrant up

It will create an Ubuntu 14.04.1 LTS (Trusty Tahr) virtual machine with Jenkins
(port 8080), LXC and lxCI ready to go.

## Security

Not.

http://www.slideshare.net/jpetazzo/is-it-safe-to-run-applications-in-linux-containers

