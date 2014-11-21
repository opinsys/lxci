#!/bin/sh

set -eu

$LXCI $BASE --archive-on-fail --name foo --command "exit 0"

ls "$RUNTIME_CONFIG_PATH/foo" && {
    echo "Container was not destroyed"
    exit 1
} || true

ls "$ARCHIVE_CONFIG_PATH/foo" && {
    echo "Container should not have been archived"
    exit 1
} || true
