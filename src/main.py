import argparse
import os

from lib.configuration import YamlConfiguration
from lib.ai import OpenAI
from lib.telegram import TelegramBot


def parse_configuration():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=str, default='config.yaml')
    parser.add_argument('--path', type=str, default='')
    parser = parser.parse_args()
    config = parser.config
    path = parser.path
    if path != '':
        config = os.path.join(path, config)
    file_path = os.path.join(path, config) if path != '' else os.path.dirname(os.path.abspath(__file__)) + "/config.yaml"
    if not os.path.exists(file_path):
        raise Exception(f'Configuration file {file_path} not found')
    ext = config.split('.')[-1]
    if ext == 'yaml':
        configuration = YamlConfiguration(file_path)
        config = configuration.load()
        return config
    raise Exception(f'Unknown configuration file extension: {ext}')


def main():
    config = parse_configuration()
    open_ai = OpenAI(configuration=config.ai_settings)
    telegram_app = TelegramBot(configuration=config.telegram_settings)
    telegram_app.set_ai_handler(open_ai)
    telegram_app.start_telegram_bot()

if __name__ == '__main__':
    main()