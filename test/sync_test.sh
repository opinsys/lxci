#!/bin/sh

set -eu

. test/lxci_test_config

mkdir -p "$HOME/tmp/workspace"
touch "$HOME/tmp/workspace/syncme"

$LXCI $BASE --name container --sync "$HOME/tmp/workspace/" --command "ls -l syncme" || {
    echo "The file did not sync"
    exit 1
}
