import lxc
import os
import configparser

_dir = os.path.realpath(os.path.dirname(__file__))

BASE_CONFIG_PATH = lxc.default_config_path
RUNTIME_CONFIG_PATH = lxc.default_config_path
ARCHIVE_CONFIG_PATH = lxc.default_config_path

SSH_KEY_PATH = os.path.join(_dir, "insecure_key")
SSH_PUB_KEY_PATH = os.path.join(_dir, "insecure_key.pub")

VERBOSE = False

with open(os.path.join(_dir, "VERSION"), "r") as _f:
    VERSION = _f.read().strip()

for _configfile in (os.environ["HOME"] + "/.config/lxci/config", "/etc/lxci/config"):
    try:
        with open("config", "r") as _f:
            _parser = configparser.ConfigParser()
            _parser.read_string("[default]\n" + _f.read())
            for _key, _value in _parser["default"].items():
                globals()[_key.upper()] = _value
    except FileNotFoundError:
        pass
