import yaml

from .utils import DictToObj

class BaseConfiguration:
    def __init__(self, config_file):
        self.config_file = config_file

    def load(self):
        raise NotImplementedError

class YamlConfiguration(BaseConfiguration):
    def load(self):
        with open(self.config_file, 'r') as stream:
            stream = yaml.safe_load(stream)
        return DictToObj(stream).dict_data_to_object()