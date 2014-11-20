#!/bin/sh

set -eu

. test/lxci_test_config

$LXCI $BASE --name foo --command "exit 1" || true

ls "$ARCHIVE_CONFIG_PATH/foo" || {
    echo "The container should be in the archive!"
    exit 1
}

