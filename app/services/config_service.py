import os
import yaml
from common.dotdict import DotDict

class ConfigService:
    def __init__(self, config_path='config/config.yml'):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> DotDict:
        with open(os.path.join(self.config_path), 'r') as file:
            return DotDict(yaml.safe_load(file))

    def get_config(self) -> DotDict:
        return self.config