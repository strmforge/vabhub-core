#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模板管理器
支持命名规则模板、分类模板、推荐算法模板
"""

import os
import json
import yaml
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime


class TemplateManager:
    """模板管理器"""
    
    def __init__(self):
        self.templates_dir = "templates"
        self.templates_config = "templates_config.json"
        self.templates = {
            "naming_rules": {},
            "classification": {},
            "recommendation": {},
            "ui_themes": {}
        }
        
        # 创建模板目录
        os.makedirs(self.templates_dir, exist_ok=True)
        
        # 加载所有模板
        self.load_all_templates()
    
    def load_all_templates(self) -> bool:
        """加载所有模板"""
        try:
            # 加载命名规则模板
            naming_dir = os.path.join(self.templates_dir, "naming_rules")
            os.makedirs(naming_dir, exist_ok=True)
            
            for template_file in Path(naming_dir).glob("*.json"):
                template_name = template_file.stem
                self.templates["naming_rules"][template_name] = self._load_template(template_file)
            
            # 加载分类模板
            classification_dir = os.path.join(self.templates_dir, "classification")
            os.makedirs(classification_dir, exist_ok=True)
            
            for template_file in Path(classification_dir).glob("*.json"):
                template_name = template_file.stem
                self.templates["classification"][template_name] = self._load_template(template_file)
            
            # 加载推荐算法模板
            recommendation_dir = os.path.join(self.templates_dir, "recommendation")
            os.makedirs(recommendation_dir, exist_ok=True)
            
            for template_file in Path(recommendation_dir).glob("*.json"):
                template_name = template_file.stem
                self.templates["recommendation"][template_name] = self._load_template(template_file)
            
            # 加载UI主题模板
            themes_dir = os.path.join(self.templates_dir, "ui_themes")
            os.makedirs(themes_dir, exist_ok=True)
            
            for template_file in Path(themes_dir).glob("*.json"):
                template_name = template_file.stem
                self.templates["ui_themes"][template_name] = self._load_template(template_file)
            
            return True
            
        except Exception as e:
            print(f"加载模板失败: {e}")
            return False
    
    def _load_template(self, template_file: Path) -> Dict[str, Any]:
        """加载单个模板文件"""
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                if template_file.suffix == '.json':
                    return json.load(f)
                elif template_file.suffix in ['.yaml', '.yml']:
                    return yaml.safe_load(f)
        except Exception as e:
            print(f"加载模板文件 {template_file} 失败: {e}")
        return {}
    
    def get_naming_rule(self, template_name: str, media_type: str) -> Optional[Dict[str, Any]]:
        """获取命名规则模板"""
        template = self.templates["naming_rules"].get(template_name, {})
        return template.get(media_type)
    
    def apply_naming_rule(self, template_name: str, media_type: str, metadata: Dict[str, Any]) -> str:
        """应用命名规则"""
        rule = self.get_naming_rule(template_name, media_type)
        if not rule:
            return metadata.get("title", "unknown")
        
        # 应用命名规则
        naming_pattern = rule.get("pattern", "{title} ({year})")
        
        # 替换变量
        filename = naming_pattern
        for key, value in metadata.items():
            placeholder = f"{{{key}}}"
            if placeholder in filename:
                filename = filename.replace(placeholder, str(value))
        
        # 清理无效字符
        filename = self._sanitize_filename(filename)
        
        return filename
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名中的无效字符"""
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename
    
    def get_classification_rules(self, template_name: str) -> Optional[Dict[str, Any]]:
        """获取分类规则模板"""
        return self.templates["classification"].get(template_name)
    
    def classify_media(self, template_name: str, metadata: Dict[str, Any]) -> List[str]:
        """使用分类模板分类媒体"""
        rules = self.get_classification_rules(template_name)
        if not rules:
            return ["general"]
        
        categories = []
        
        # 应用分类规则
        for category, rule in rules.items():
            if self._matches_rule(rule, metadata):
                categories.append(category)
        
        return categories if categories else ["general"]
    
    def _matches_rule(self, rule: Dict[str, Any], metadata: Dict[str, Any]) -> bool:
        """检查是否匹配规则"""
        for field, condition in rule.items():
            if field == "and":
                # 与条件
                if not all(self._matches_rule(sub_rule, metadata) for sub_rule in condition):
                    return False
            elif field == "or":
                # 或条件
                if not any(self._matches_rule(sub_rule, metadata) for sub_rule in condition):
                    return False
            else:
                # 字段条件
                value = metadata.get(field)
                if value is None:
                    return False
                
                if isinstance(condition, dict):
                    # 复杂条件
                    for op, expected in condition.items():
                        if op == "equals" and value != expected:
                            return False
                        elif op == "contains" and expected not in str(value):
                            return False
                        elif op == "in" and value not in expected:
                            return False
                        elif op == "gt" and value <= expected:
                            return False
                        elif op == "lt" and value >= expected:
                            return False
                else:
                    # 简单条件
                    if value != condition:
                        return False
        
        return True
    
    def get_recommendation_algorithm(self, template_name: str) -> Optional[Dict[str, Any]]:
        """获取推荐算法模板"""
        return self.templates["recommendation"].get(template_name)
    
    def generate_recommendations(self, template_name: str, user_profile: Dict[str, Any], 
                               media_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成推荐"""
        algorithm = self.get_recommendation_algorithm(template_name)
        if not algorithm:
            return media_items[:10]  # 默认返回前10个
        
        # 应用推荐算法
        algorithm_type = algorithm.get("type", "popularity")
        
        if algorithm_type == "popularity":
            # 基于流行度推荐
            return sorted(media_items, key=lambda x: x.get("rating", 0), reverse=True)[:10]
        
        elif algorithm_type == "content_based":
            # 基于内容推荐
            user_preferences = user_profile.get("preferences", {})
            recommendations = []
            
            for item in media_items:
                score = self._calculate_content_score(item, user_preferences)
                if score > 0.5:  # 阈值
                    recommendations.append({"item": item, "score": score})
            
            return sorted(recommendations, key=lambda x: x["score"], reverse=True)[:10]
        
        elif algorithm_type == "collaborative":
            # 协同过滤推荐
            # 这里可以集成更复杂的协同过滤算法
            return media_items[:10]
        
        return media_items[:10]
    
    def _calculate_content_score(self, item: Dict[str, Any], preferences: Dict[str, Any]) -> float:
        """计算内容匹配分数"""
        score = 0.0
        
        # 基于类型匹配
        item_type = item.get("type")
        if item_type in preferences.get("preferred_types", []):
            score += 0.3
        
        # 基于分类匹配
        item_categories = item.get("categories", [])
        preferred_categories = preferences.get("preferred_categories", [])
        
        for category in item_categories:
            if category in preferred_categories:
                score += 0.2
        
        # 基于评分匹配
        item_rating = item.get("rating", 0)
        if item_rating >= 8.0:
            score += 0.2
        elif item_rating >= 7.0:
            score += 0.1
        
        return min(score, 1.0)
    
    def get_ui_theme(self, theme_name: str) -> Optional[Dict[str, Any]]:
        """获取UI主题模板"""
        return self.templates["ui_themes"].get(theme_name)
    
    def apply_ui_theme(self, theme_name: str, base_css: str) -> str:
        """应用UI主题"""
        theme = self.get_ui_theme(theme_name)
        if not theme:
            return base_css
        
        # 应用主题变量
        css = base_css
        for var_name, value in theme.get("variables", {}).items():
            css = css.replace(f"var(--{var_name})", value)
        
        return css
    
    def create_template(self, template_type: str, template_name: str, 
                       template_data: Dict[str, Any]) -> bool:
        """创建新模板"""
        try:
            template_dir = os.path.join(self.templates_dir, template_type)
            os.makedirs(template_dir, exist_ok=True)
            
            template_file = os.path.join(template_dir, f"{template_name}.json")
            
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(template_data, f, indent=2, ensure_ascii=False)
            
            # 更新内存中的模板
            self.templates[template_type][template_name] = template_data
            
            return True
            
        except Exception as e:
            print(f"创建模板失败: {e}")
            return False
    
    def export_template(self, template_type: str, template_name: str, 
                       export_path: str) -> bool:
        """导出模板"""
        try:
            template = self.templates[template_type].get(template_name)
            if not template:
                return False
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(template, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"导出模板失败: {e}")
            return False
    
    def get_all_templates(self) -> Dict[str, Dict[str, Any]]:
        """获取所有模板"""
        return self.templates
    
    def get_template_stats(self) -> Dict[str, Any]:
        """获取模板统计信息"""
        stats = {}
        
        for template_type, templates in self.templates.items():
            stats[template_type] = {
                "count": len(templates),
                "names": list(templates.keys())
            }
        
        return stats


# 创建示例模板
def create_sample_templates():
    """创建示例模板"""
    manager = TemplateManager()
    
    # 创建电影命名规则模板
    movie_naming_rule = {
        "movie": {
            "pattern": "{title} ({year}) [{quality}]",
            "description": "标准电影命名规则",
            "author": "MediaRenamer Team",
            "version": "1.0.0"
        },
        "tv_series": {
            "pattern": "{title}/Season {season}/S{season}E{episode} - {episode_title}",
            "description": "电视剧命名规则",
            "author": "MediaRenamer Team", 
            "version": "1.0.0"
        }
    }
    
    manager.create_template("naming_rules", "standard", movie_naming_rule)
    
    # 创建分类模板
    classification_rule = {
        "action": {
            "genres": {"contains": "action"},
            "rating": {"gt": 6.0}
        },
        "comedy": {
            "genres": {"contains": "comedy"}
        },
        "high_quality": {
            "rating": {"gt": 8.0},
            "and": [
                {"quality": {"in": ["4K", "1080P"]}}
            ]
        }
    }
    
    manager.create_template("classification", "standard", classification_rule)
    
    # 创建推荐算法模板
    recommendation_algorithm = {
        "type": "content_based",
        "description": "基于内容的推荐算法",
        "parameters": {
            "similarity_threshold": 0.7,
            "max_recommendations": 10
        }
    }
    
    manager.create_template("recommendation", "content_based", recommendation_algorithm)
    
    # 创建UI主题模板
    dark_theme = {
        "name": "Dark Theme",
        "variables": {
            "primary-color": "#2196F3",
            "background-color": "#1E1E1E",
            "text-color": "#FFFFFF",
            "border-color": "#333333"
        }
    }
    
    manager.create_template("ui_themes", "dark", dark_theme)
    
    print("✅ 示例模板创建完成")