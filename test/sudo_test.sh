
#!/bin/sh

set -eu

. test/lxci_test_config

$LXCI $BASE --name container --sudo --command "sudo cat /etc/shadow" || {
    echo "failed to use sudo with --sudo"
    exit 1
}
