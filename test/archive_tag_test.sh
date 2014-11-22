#!/bin/sh

set -eu

$LXCI $BASE --archive-on-fail --name foo --tag bar --command "exit 1" || true

ls "$ARCHIVE_CONFIG_PATH/foo" || {
    echo "The container should be in the archive!"
    exit 1
}


$LXCI $BASE --archive-on-fail --name foo2 --tag bar --destroy-archive-on-success --command "exit 0"


ls "$ARCHIVE_CONFIG_PATH/foo" && {
    echo "The foo container should have been destroyed"
    exit 1
} || true


ls "$ARCHIVE_CONFIG_PATH/foo2" && {
    echo "The foo2 container should not be in archive"
    exit 1
} || true
