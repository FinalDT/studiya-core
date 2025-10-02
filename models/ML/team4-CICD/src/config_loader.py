# src/config_loader.py
import json
from typing import Dict, Any

def load_config(config_path: str) -> Dict[str, Any]:
    """
    JSON config 파일을 읽어서 Python dict로 반환합니다.

    Args:
        config_path (str): config 파일 경로

    Returns:
        Dict[str, Any]: config 내용
    """
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config
