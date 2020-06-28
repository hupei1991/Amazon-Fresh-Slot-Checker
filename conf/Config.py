import configparser
import os
from pathlib import Path

config_path = "conf/config.ini"
default_local_config_path = os.path.join(str(Path.home()), "tracker_config.ini")

CONFIG = configparser.ConfigParser(allow_no_value=True)
CONFIG.read([config_path, default_local_config_path])
