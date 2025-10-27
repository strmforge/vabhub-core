#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAML配置加载器
支持StrataMedia风格的配置管理
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigLoader:
    """配置加载器"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.configs: Dict[str, Any] = {}
        
    def load_all_configs(self) -> Dict[str, Any]:
        """加载所有配置文件"""
        config_files = [
            ("config.yaml", "main"),
            ("classifiers.yaml", "classifiers"),
            ("rename_templates.yaml", "templates")
        ]
        
        for filename, config_name in config_files:
            config_path = self.config_dir / filename
            if config_path.exists():
                self.configs[config_name] = self._load_yaml(config_path)
            else:
                print(f"警告: 配置文件 {config_path} 不存在")
                self.configs[config_name] = {}
        
        return self.configs
    
    def _load_yaml(self, filepath: Path) -> Dict[str, Any]:
        """加载YAML文件"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"加载配置文件 {filepath} 失败: {e}")
            return {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        keys = key.split('.')
        value = self.configs
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_classifier_rules(self) -> list:
        """获取分类器规则"""
        return self.configs.get('classifiers', {}).get('rules', [])
    
    def get_special_rules(self) -> list:
        """获取特殊处理规则"""
        return self.configs.get('classifiers', {}).get('special_rules', [])
    
    def get_templates(self) -> Dict[str, str]:
        """获取重命名模板"""
        return self.configs.get('templates', {})
    
    def get_workflow_config(self) -> Dict[str, Any]:
        """获取工作流配置"""
        return self.configs.get('main', {}).get('workflow', {})
    
    def get_plugin_config(self, plugin_type: str) -> list:
        """获取插件配置"""
        return self.configs.get('main', {}).get('plugins', {}).get(plugin_type, [])


# 全局配置实例
_config_loader: Optional[ConfigLoader] = None


def get_config_loader() -> ConfigLoader:
    """获取全局配置加载器"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
        _config_loader.load_all_configs()
    return _config_loader


def reload_configs() -> None:
    """重新加载所有配置"""
    global _config_loader
    if _config_loader:
        _config_loader.load_all_configs()


if __name__ == "__main__":
    # 测试配置加载
    loader = ConfigLoader()
    configs = loader.load_all_configs()
    
    print("配置加载成功:")
    for name, config in configs.items():
        print(f"{name}: {len(config)} 个配置项")