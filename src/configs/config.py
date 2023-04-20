import os
import yaml


def file_relative_path(file_path: str) -> str:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    rel_path = os.path.join(current_dir, file_path)
    return rel_path


def load_config(file_path: str) -> dict:
    config_file = file_relative_path(file_path)
    with open(config_file) as f:
        return yaml.safe_load(f)
