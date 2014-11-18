
```
usage: lxci [-h] [-c COMMAND] [-n NAME] [-t TAG] [-s DIR] [-A] [-a] [-l]
               [-m NAME] [-D] [-d] [-i NAME] [-E ENV] [-e [ENV [ENV ...]]]
               [--print-config] [-V] [-v]
               [BASE_CONTAINER]

Start temporary container based on an existing one

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
  -s DIR, --sync-workspace DIR
                        synchronize DIR to the container. The trailing slash
                        works like in rsync. If it is present the contents of
                        the DIR is synchronized to the current working
                        directory command. If not the directory itself is
                        synchronized.
  -A, --archive         archive the container after running the command
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
  -V, --version         print lxci version
  -v, --verbose         be verbose
```
