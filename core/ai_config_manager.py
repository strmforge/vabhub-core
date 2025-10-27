#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI配置管理器
统一管理AI服务的配置、认证和集成
"""

import os
import json
from typing import Dict, List, Any, Optional
from pathlib import Path


class AIConfigManager:
    """AI配置管理器"""
    
    def __init__(self, config_file: str = "ai_config.json"):
        self.config_file = config_file
        self.config_data = self._load_config()
        self.available_services = self._initialize_services()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载AI配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # 默认配置
        return {
            "services": {
                "openai": {
                    "enabled": False,
                    "api_key": "",
                    "model": "gpt-4-vision-preview",
                    "max_tokens": 1000,
                    "temperature": 0.7
                },
                "baidu_ai": {
                    "enabled": False,
                    "api_key": "",
                    "secret_key": "",
                    "app_id": ""
                },
                "google_ai": {
                    "enabled": False,
                    "api_key": "",
                    "model": "gemini-pro-vision"
                },
                "local_ai": {
                    "enabled": True,
                    "model_path": "models/local_ai",
                    "device": "auto"
                },
                "simulation_ai": {
                    "enabled": True,
                    "confidence_threshold": 0.8
                }
            },
            "preferences": {
                "primary_service": "simulation_ai",
                "fallback_services": ["local_ai", "simulation_ai"],
                "auto_switch": True,
                "cost_optimization": True,
                "privacy_mode": False
            }
        }
    
    def _initialize_services(self) -> Dict[str, Dict[str, Any]]:
        """初始化AI服务"""
        return {
            "openai": {
                "name": "OpenAI",
                "description": "OpenAI GPT-4 Vision模型",
                "capabilities": ["video_analysis", "content_classification", "description_generation"],
                "cost_per_request": 0.01,
                "latency": "medium",
                "accuracy": "high"
            },
            "baidu_ai": {
                "name": "百度AI",
                "description": "百度智能云AI服务",
                "capabilities": ["video_analysis", "content_classification", "chinese_optimized"],
                "cost_per_request": 0.005,
                "latency": "low",
                "accuracy": "high"
            },
            "google_ai": {
                "name": "Google AI",
                "description": "Google Gemini Vision模型",
                "capabilities": ["video_analysis", "content_classification", "multimodal"],
                "cost_per_request": 0.008,
                "latency": "medium",
                "accuracy": "high"
            },
            "local_ai": {
                "name": "本地AI",
                "description": "本地部署的AI模型",
                "capabilities": ["video_analysis", "content_classification"],
                "cost_per_request": 0.0,
                "latency": "high",
                "accuracy": "medium",
                "privacy": "high"
            },
            "simulation_ai": {
                "name": "模拟AI",
                "description": "基于规则的模拟AI分析",
                "capabilities": ["basic_analysis", "filename_patterns"],
                "cost_per_request": 0.0,
                "latency": "low",
                "accuracy": "low",
                "availability": "always"
            }
        }
    
    def save_config(self):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def get_service_config(self, service_name: str) -> Dict[str, Any]:
        """获取服务配置"""
        return self.config_data.get("services", {}).get(service_name, {})
    
    def update_service_config(self, service_name: str, config: Dict[str, Any]):
        """更新服务配置"""
        if "services" not in self.config_data:
            self.config_data["services"] = {}
        
        self.config_data["services"][service_name] = config
        self.save_config()
    
    def enable_service(self, service_name: str):
        """启用服务"""
        config = self.get_service_config(service_name)
        config["enabled"] = True
        self.update_service_config(service_name, config)
    
    def disable_service(self, service_name: str):
        """禁用服务"""
        config = self.get_service_config(service_name)
        config["enabled"] = False
        self.update_service_config(service_name, config)
    
    def validate_service_config(self, service_name: str) -> Dict[str, Any]:
        """验证服务配置"""
        config = self.get_service_config(service_name)
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        if not config.get("enabled", False):
            validation_result["warnings"].append("服务未启用")
            return validation_result
        
        # 验证特定服务的配置
        if service_name == "openai":
            if not config.get("api_key"):
                validation_result["valid"] = False
                validation_result["errors"].append("缺少API密钥")
        
        elif service_name == "baidu_ai":
            if not config.get("api_key") or not config.get("secret_key"):
                validation_result["valid"] = False
                validation_result["errors"].append("缺少API密钥或密钥")
        
        elif service_name == "google_ai":
            if not config.get("api_key"):
                validation_result["valid"] = False
                validation_result["errors"].append("缺少API密钥")
        
        elif service_name == "local_ai":
            model_path = config.get("model_path", "")
            if model_path and not os.path.exists(model_path):
                validation_result["warnings"].append("模型路径不存在")
        
        return validation_result
    
    def get_available_services(self) -> List[Dict[str, Any]]:
        """获取可用服务列表"""
        available_services = []
        
        for service_id, service_info in self.available_services.items():
            config = self.get_service_config(service_id)
            validation = self.validate_service_config(service_id)
            
            service_data = {
                "id": service_id,
                "name": service_info["name"],
                "description": service_info["description"],
                "enabled": config.get("enabled", False),
                "capabilities": service_info["capabilities"],
                "cost": service_info["cost_per_request"],
                "latency": service_info["latency"],
                "accuracy": service_info["accuracy"],
                "validation": validation
            }
            
            available_services.append(service_data)
        
        return available_services
    
    def get_best_service_for_task(self, task_type: str, requirements: Dict[str, Any] = None) -> str:
        """根据任务类型获取最佳服务"""
        if requirements is None:
            requirements = {}
        
        # 默认偏好设置
        preferences = self.config_data.get("preferences", {})
        primary_service = preferences.get("primary_service", "simulation_ai")
        
        # 检查主服务是否可用
        if self._is_service_available(primary_service):
            return primary_service
        
        # 检查备用服务
        fallback_services = preferences.get("fallback_services", ["local_ai", "simulation_ai"])
        for service in fallback_services:
            if self._is_service_available(service):
                return service
        
        # 最后返回模拟AI
        return "simulation_ai"
    
    def _is_service_available(self, service_name: str) -> bool:
        """检查服务是否可用"""
        config = self.get_service_config(service_name)
        validation = self.validate_service_config(service_name)
        
        return config.get("enabled", False) and validation["valid"]
    
    def get_service_performance_metrics(self) -> Dict[str, Any]:
        """获取服务性能指标"""
        # 这里可以集成实际的性能监控数据
        return {
            "openai": {
                "success_rate": 0.95,
                "average_response_time": 2.5,
                "cost_per_month": 0.0,
                "last_used": "2024-01-01"
            },
            "baidu_ai": {
                "success_rate": 0.92,
                "average_response_time": 1.8,
                "cost_per_month": 0.0,
                "last_used": "2024-01-01"
            },
            "google_ai": {
                "success_rate": 0.94,
                "average_response_time": 2.2,
                "cost_per_month": 0.0,
                "last_used": "2024-01-01"
            },
            "local_ai": {
                "success_rate": 0.85,
                "average_response_time": 5.0,
                "cost_per_month": 0.0,
                "last_used": "2024-01-01"
            },
            "simulation_ai": {
                "success_rate": 0.80,
                "average_response_time": 0.1,
                "cost_per_month": 0.0,
                "last_used": "2024-01-01"
            }
        }
    
    def update_preferences(self, preferences: Dict[str, Any]):
        """更新偏好设置"""
        if "preferences" not in self.config_data:
            self.config_data["preferences"] = {}
        
        self.config_data["preferences"].update(preferences)
        self.save_config()
    
    def get_preferences(self) -> Dict[str, Any]:
        """获取偏好设置"""
        return self.config_data.get("preferences", {})
    
    def reset_to_defaults(self):
        """重置为默认配置"""
        self.config_data = self._load_config()
        self.save_config()


# 全局配置管理器实例
ai_config_manager = AIConfigManager()