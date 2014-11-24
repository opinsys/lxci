
# lxCI

Run commands in full<sup>1</sup> temporary containers

    lxci trusty-amd64

This will do following

1. Creates a new temporary container based on the existing `trusty-amd64`
   container<sup>2</sup>
2. Adds user `lxci` to it
3. Boots and waits for the network and ssh server to wake up in it
4. Logins as the `lxci` user over ssh and starts `bash`
5. After the bash command exists the container is destroyed

add `-v` to see details

<small>

<sup>1</sup> Unlike Docker the container is started using the normal
`/sbin/init` meaning all the installed daemons (ssh, cron, upstart etc.) in the
base container will be started in as you would expect them to start in normal
virtual machine.

<sup>2</sup> Create it with `sudo lxc-create -t download -n trusty-amd64 --
--dist ubuntu --release trusty --arch amd64` and install `openssh-server`
package into it.

</small>

To execute custom command instead of bash use `--command COMMAND`

    $ lxci trusty-amd64 --command hostname
    trusty-amd64-runtime-2014-11-22_11-32-03

To copy files into the container workspace use `--sync PATH`

    $ lxci trusty-amd64 --sync . --command "ls -l *.py"
    -rwxrwxr-x 1 lxci lxci 8666 Nov 22 11:27 lxci.py

To archive the container on failures add `--archive-on-fail`

    $ lxci trusty-amd64 --command "exit 42" --archive-on-fail
    Command failed in the container with exit status 42
    You may inspect what went wrong with: [sudo] lxci --inspect trusty-amd64-runtime-2014-11-22_11-35-13

As noted the container can be inspected with `--inspect`. It will start bash in
the archived container

    $ lxci --inspect trusty-amd64-runtime-2014-11-22_11-35-13
    lxci@trusty-amd64-runtime-2014-11-22_11-35-13:~/workspace$

To list all other options use `--help`.


### Artifacts

Place any files to `/home/lxci/results` in the container and they will be
copied to `/var/lib/lxci/results/NAME` on the host. Where `NAME` is the name of
the temporary container. Set it with `--name`.

### Workflow with Continuous Integration Systems

lxCI works really well with Continuous Integration Systems such as Jenkins. We
use it like this

```shell
lxci --name "$JOB_NAME-$BUILD_NUMBER" \
    --tag $JOB_NAME \
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

    none /var/lib/lxci/runtime tmpfs size=5g 0 0

or

    none /var/lib/lxci/runtime ramfs defaults 0 0


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

You should always assume that code running as root in the container can get
root for the host too. Meaning if you do following

    sudo lxci base --sudo --command "sudo gem install funnygem"

You can assume that now the author of the `funnygem` has root access to your
host machine.

You should read this

http://www.slideshare.net/jpetazzo/is-it-safe-to-run-applications-in-linux-containers

### Unprivileged containers

However lxCI supports unprivileged containers. When using unprivileged
containers the root user of the container is mapped to a non-root user in the
host which might be a bit safer. Maybe.

Read here how to configure them

https://help.ubuntu.com/lts/serverguide/lxc.html

Here's some security background

https://www.stgraber.org/2014/01/01/lxc-1-0-security-features/

## Options

```
positional arguments:
  BASE_CONTAINER        base container to use. Use [sudo] lxc-ls to list
                        available containers.

optional arguments:
  -h, --help            show this help message and exit
  -c COMMAND, --command COMMAND
                        shell command to be executed in the container. If set
                        to - the command will be read from the stdin. DEFAULT:
                        bash
  -n NAME, --name NAME  custom name for the temporary runtime container
  -t TAG, --tag TAG     tag container with TAG
  -s DIR, --sync DIR    synchronize DIR to the container. The trailing slash
                        works like in rsync. If it is present the contents of
                        the DIR is synchronized to the current working
                        directory command. If not the directory itself is
                        synchronized.
  -A, --archive         archive the container after running the command. The
                        archive is always created with a directory backing
                        store
  -a, --archive-on-fail
                        archive the container only if the command returns with
                        non zero exit status
  -l, --list-archive    list archived containers. Combine --verbose to see
                        tags and filter list with --tag TAG
  -m NAME, --info NAME  display meta data of an archived container
  -D, --destroy-archive
                        destroy all archived containers. Combine with --tag
                        TAG to destroy only the containers with the TAG
  -d, --destroy-archive-on-success
                        destroy archived containers on success. If --tag is
                        set only the containers with matching tags will bee
                        destroyed
  -i NAME, --inspect NAME
                        start bash in the archived container for inspection
  -E ENV, --copy-env ENV
                        copy comma separated environment variables to the
                        container
  -e [ENV [ENV ...]], --set-env [ENV [ENV ...]]
                        Set environment variable for the container. Example
                        FOO=bar
  --print-config        print config
  -S, --sudo            enable passwordless sudo in the container
  -p, --snapshot        clone base container as a snapshot. Makes the
                        temporary container creation really fast if your host
                        filesystem supports this
  -B BACKINGSTORE, --backingstore BACKINGSTORE
                        set custom backingstore for --snapshot. Works just
                        like lxc-clone --backingstore
  -V, --version         print lxci version
  --destroy-runtime     stop and destroy all runtime containers
  -v, --verbose         be verbose

Use environment variable LXCI_HOME to set custom path to configuration file
```
