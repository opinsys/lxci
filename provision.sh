#!/bin/sh

set -eu

wget -q -O - http://pkg.jenkins-ci.org/debian/jenkins-ci.org.key | sudo apt-key add -

cat >/etc/apt/sources.list.d/jenkins.list<<EOF
deb http://pkg.jenkins-ci.org/debian binary/
EOF

# Allow passwordless sudo for lxci command in jenkins
cat >/etc/sudoers.d/jenkins_lxci<<EOF
jenkins ALL=NOPASSWD:/usr/local/bin/lxci, /usr/bin/lxci
EOF

apt-get update

apt-get install -y lxc python3-lxc jenkins

cd /vagrant
# Install lxci
sudo make install


