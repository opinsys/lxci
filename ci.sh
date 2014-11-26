#!/bin/sh

set -eux

sudo apt-get install devscripts make equivs -y

make deb
ls -l ..

cp ../lxci_* $HOME/results
