import lxc
import os

_dir = os.path.realpath(os.path.dirname(__file__))

BASE_CONFIG_PATH = lxc.default_config_path
RUNTIME_CONFIG_PATH = lxc.default_config_path
ARCHIVE_CONFIG_PATH = lxc.default_config_path

SSH_KEY_PATH = os.path.join(_dir, "insecure_key")
SSH_PUB_KEY_PATH = os.path.join(_dir, "insecure_key.pub")

VERBOSE = False

with open(os.path.join(_dir, "VERSION"), "r") as f:
    VERSION = f.read().strip()
