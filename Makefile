prefix ?= /usr/local
exec_prefix = $(prefix)
bindir = $(exec_prefix)/bin

# Huh, even python uses different paths under /usr/local
ifeq ($(prefix),/usr/local)
	PYTHON_PATH_DIR = $(prefix)/lib/python3.4/dist-packages
else
	PYTHON_PATH_DIR = $(prefix)/lib/python3/dist-packages
endif

all:

installdirs:
	mkdir -p $(DESTDIR)$(PYTHON_PATH_DIR)
	mkdir -p $(DESTDIR)$(bindir)
	mkdir -p $(DESTDIR)/etc/lxci

install: installdirs
	cp -a lxci $(DESTDIR)$(PYTHON_PATH_DIR)
	cp -a lxci.py $(DESTDIR)$(bindir)/lxci
	cp -a config.default $(DESTDIR)/etc/lxci/config


test:
	# too slow to run on packet build

test_:
	sudo test/run.sh

clean:
	find . -name '*.pyc' -delete
	rm -rf lxci/__pycache__

deb:
	rm -rf debian
	cp -a debian.default debian
	dpkg-buildpackage -us -uc

install-build-dep:
	mk-build-deps --install debian.default/control \
		--tool "apt-get --yes" --remove

