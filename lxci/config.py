import lxc
import os
import configparser
import getpass
import subprocess
import sys
from os.path import join

_dir = os.path.realpath(os.path.dirname(__file__))

_home = "/etc/lxci" # Default home
if getpass.getuser() != "root":
    # non-root users get their own environment
    _home = join(os.environ["HOME"], ".config/lxci")

# LXCI_HOME overrides everything
_home = os.environ.get("LXCI_HOME", _home)
# ensure it exists
os.makedirs(_home, exist_ok=True)

# default paths
RUNTIME_CONFIG_PATH = "/var/lib/lxci/runtime"
ARCHIVE_CONFIG_PATH = "/var/lib/lxci/archive"
RESULTS_PATH = "/var/lib/lxci/results"

# non-root cannot write to the default paths
if getpass.getuser() != "root":
    RUNTIME_CONFIG_PATH = join(_home, "runtime")
    ARCHIVE_CONFIG_PATH = join(_home, "archive")
    RESULTS_PATH = join(_home, "results")


# use lxc default path for the base containers
BASE_CONFIG_PATH = lxc.default_config_path

SSH_KEY_PATH = join(_home, "key")
SSH_PUB_KEY_PATH = join(_home, "key.pub")
VERBOSE = False

# load customizations
try:
    with open(join(_home, "config"), "r") as _f:
        _parser = configparser.ConfigParser()
        _parser.read_string("[default]\n" + _f.read())
        for _key, _value in _parser["default"].items():
            globals()[_key.upper()] = _value
except FileNotFoundError:
    pass

VERBOSE = bool(VERBOSE)

with open(os.path.join(_dir, "VERSION"), "r") as _f:
    VERSION = _f.read().strip()

# ensure rest of the directories
os.makedirs(BASE_CONFIG_PATH, exist_ok=True)
os.makedirs(RUNTIME_CONFIG_PATH, exist_ok=True)
os.makedirs(ARCHIVE_CONFIG_PATH, exist_ok=True)
os.makedirs(RESULTS_PATH, exist_ok=True)

if not os.path.exists(SSH_KEY_PATH):
    print("ssh key missing. Generating", SSH_KEY_PATH, file=sys.stderr)
    subprocess.check_call(["ssh-keygen", "-q", "-N", "", "-f", SSH_KEY_PATH])
