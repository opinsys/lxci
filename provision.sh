#!/bin/sh

set -eu


# Add sources for latest Jenkins
wget -q -O - http://pkg.jenkins-ci.org/debian/jenkins-ci.org.key | sudo apt-key add -
cat >/etc/apt/sources.list.d/jenkins.list<<EOF
deb http://pkg.jenkins-ci.org/debian binary/
EOF

# Allow passwordless sudo for lxci command for jenkins user used by the Jenkins
# server
cat >/etc/sudoers.d/jenkins_lxci<<EOF
jenkins ALL=NOPASSWD:/usr/local/bin/lxci, /usr/bin/lxci
EOF

# Install LXC, Jenkins and lxci deps
apt-get update
apt-get install -y lxc python3-lxc jenkins rsync


# Use create a basic base container
lxc-create --template download --name trusty-amd64 -- --dist ubuntu --release trusty --arch amd64

# Install openssh-server into the container
chroot /var/lib/lxc/trusty-amd64/rootfs apt-get install openssh-server --yes --no-install-recommends

# Install lxci
if [ -f lxci.py ]; then
    make install
else
    # Vagrant provision
    cd /vagrant
    make install
fi


