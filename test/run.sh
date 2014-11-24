#!/bin/sh


set -u


print_help(){
    echo "
    Usage: $(basename $0) [TEST_PATH]

    Run test file. If TEST_PATH is not set all tests will be run
    "
}

[ "${1:-}" = "--help" -o "${1:-}" = "-h" ] && print_help && exit 0

export LXCI_HOME="/tmp/lxc-test-$USER"

export LXCI="./lxci.py --snapshot"
export BASE=trusty-amd64

export RUNTIME_CONFIG_PATH="$LXCI_HOME/runtime"
export ARCHIVE_CONFIG_PATH="$LXCI_HOME/archive"
export RESULTS_PATH="$LXCI_HOME/results"


before(){
    ./lxci.py  --destroy-runtime
    ./lxci.py  --destroy-archive
    rm -rf "$LXCI_HOME"
    mkdir -p "$LXCI_HOME"
    cat >"$LXCI_HOME/config"<<EOF
RUNTIME_CONFIG_PATH=$RUNTIME_CONFIG_PATH
ARCHIVE_CONFIG_PATH=$ARCHIVE_CONFIG_PATH
RESULTS_PATH=$RESULTS_PATH
VERBOSE=1
EOF
}

run_test(){
    local test_file=$1
    before
    echo -n "Running $test_file "
    res="$($test_file 2>&1)"
    if [ "$?" = "0" ]; then
        echo "OK!"
    else
        echo "FAILED!"
        echo "$res"
        exit 1
    fi
}

if [ "${1:-}" = "" ]; then
    for test_file in test/*_test.sh
    do
        run_test "$test_file"
    done
else
    run_test "$1"
fi

echo "All OK"
