#!/bin/sh


set -u


print_help(){
    echo "
    Usage: $(basename $0) [TEST_PATH]

    Run test file. If TEST_PATH is not set all tests will bee run
    "
}

[ "${1:-}" = "--help" -o "${1:-}" = "-h" ] && print_help && exit 0


export LXCI_CONFIG=test/lxci_test_config
export LXCI="./lxci.py"
export BASE=trusty-amd64

run_test(){
    local test_file=$1
    rm /tmp/lxci_test_* -rf
    echo -n "Running $test_file "
    chmod +x "$test_file"
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
