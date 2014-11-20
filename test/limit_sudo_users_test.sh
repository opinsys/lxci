
#!/bin/sh

set -eu

. test/lxci_test_config

mkdir -p /tmp/lxci_test_dir/foo/bar

export SUDO_UID=0

$LXCI $BASE --name container --command "echo i can read secrets" --sync /tmp/lxci_test_dir && {
    echo "Should not allow sudo users to sync files from random locations"
    exit 1
} || true

