#!/bin/sh

set -eu

sudo apt-get install devscripts make equivs -y
make deb
ls ../*deb
