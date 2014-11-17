import lxc
import os

BASE_CONFIG_PATH = lxc.default_config_path
RUNTIME_CONFIG_PATH = lxc.default_config_path
ARCHIVE_CONFIG_PATH = lxc.default_config_path

SSH_KEY_PATH = os.path.join(
    os.path.realpath(os.path.dirname(__file__)),
    "insecure_key"
)

SSH_PUB_KEY_PATH = os.path.join(
    os.path.realpath(os.path.dirname(__file__)),
    "insecure_key.pub"
)

VERBOSE = False

