#!/bin/sh

set -eu

$LXCI $BASE --name container --command "touch /home/lxci/results/foobar"

ls "$RESULTS_PATH/container/foobar" || {
    echo "The artifact should have been copied"
    exit 1
}
