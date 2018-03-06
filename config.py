from ruamel.yaml import YAML
import os
import codecs

# opening config.yaml
def _read_config():
    yaml = YAML(typ='safe')
    config_path = os.path.join(os.path.dirname(__file__), 
                               "config.yaml")
    with codecs.open(config_path, "r", encoding="utf-8") as config_file:
        config = yaml.load(config_file)

    return config

config = _read_config()