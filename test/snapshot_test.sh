#!/bin/sh

set -eu

$LXCI $BASE --name snapshottest --snapshot --command "exit 0"

ls "$RUNTIME_CONFIG_PATH/snapshottest" && {
    echo "Container should have been destroyed"
    exit 1
} || true

ls "$ARCHIVE_CONFIG_PATH/snapshottest" && {
    echo "Container should not have been archived"
    exit 1
} || true
