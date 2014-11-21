
#!/bin/sh

set -eu

$LXCI $BASE --name container --sudo --command "sudo cat /etc/shadow" || {
    echo "failed to use sudo with --sudo"
    exit 1
}
