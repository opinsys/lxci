#!/bin/sh

set -eu

mkdir -p "$HOME/tmp/workspace"
echo hello > "$HOME/tmp/workspace/syncme"


$LXCI $BASE --name container --sync "$HOME/tmp/workspace/" --command "cat syncme" || {
    echo "The file did not sync or the permissions where bad"
    exit 1
}
