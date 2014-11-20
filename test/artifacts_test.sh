#!/bin/sh

set -eu

. test/lxci_test_config

$LXCI $BASE --name container --command "touch /home/lxci/results/foobar"

ls "$RESULTS_PATH/container/foobar" || {
    echo "The artifact should have been copied"
    exit 1
}
