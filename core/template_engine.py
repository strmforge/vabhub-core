#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模板引擎
支持灵活的文件命名模板
"""

import re
from typing import Dict, Any, Optional


class TemplateEngine:
    """简单的模板引擎（类似 Jinja2，但无需外部依赖）"""
    
    def __init__(self):
        # 预定义模板
        self.templates = {
            # 电影模板
            'movie_default': '{title} ({year})/{title} ({year}) [{resolution}-{source}].{ext}',
            'movie_simple': '{title} ({year})/{title} ({year}).{ext}',
            'movie_detailed': '{title} ({year})/{title} ({year}) [{resolution} {video_codec} {audio_codec} {source}].{ext}',
            'movie_quality': '{title} ({year})/{title} ({year}) [{quality}].{ext}',
            
            # 电视剧模板
            'tv_default': '{title}/Season {season:02d}/{title} - S{season:02d}E{episode:02d} [{resolution}-{source}].{ext}',
            'tv_simple': '{title}/S{season:02d}/{title} - S{season:02d}E{episode:02d}.{ext}',
            'tv_detailed': '{title}/Season {season:02d}/{title} - S{season:02d}E{episode:02d} [{resolution} {video_codec} {audio_codec} {source}].{ext}',
            'tv_quality': '{title}/Season {season:02d}/{title} - S{season:02d}E{episode:02d} [{quality}].{ext}',
            
            # NAS-Tools 风格
            'nas_movie': '{title} ({year})/{title} ({year}) [{resolution} {video_codec} {audio_codec}].{ext}',
            'nas_tv': '{title}/Season {season:02d}/{title} S{season:02d}E{episode:02d} [{resolution} {video_codec} {audio_codec}].{ext}',
            
            # MoviePilot 风格
            'mp_movie': '{title} ({year})/{title} ({year}) [{quality}].{ext}',
            'mp_tv': '{title}/Season {season:02d}/{title} S{season:02d}E{episode:02d} [{quality}].{ext}',
            
            # Plex 风格
            'plex_movie': '{title} ({year})/{title} ({year}).{ext}',
            'plex_tv': '{title}/Season {season:02d}/{title} - s{season:02d}e{episode:02d}.{ext}',
            
            # Jellyfin 风格
            'jellyfin_movie': '{title} ({year})/{title} ({year}) - {quality}.{ext}',
            'jellyfin_tv': '{title}/Season {season:02d}/{title} S{season:02d}E{episode:02d}.{ext}',
            
            # Emby 风格
            'emby_movie': '{title} ({year})/{title} ({year}).{ext}',
            'emby_tv': '{title}/Season {season:02d}/{title} - S{season:02d}E{episode:02d}.{ext}',
        }
        
        # 用户自定义模板
        self.custom_templates = {}
    
    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        渲染模板
        
        Args:
            template_name: 模板名称
            context: 上下文变量
            
        Returns:
            渲染后的字符串
        """
        # 获取模板
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"模板不存在: {template_name}")
        
        # 渲染模板
        try:
            result = template.format(**context)
            return result
        except KeyError as e:
            raise ValueError(f"模板变量缺失: {e}")
        except Exception as e:
            raise ValueError(f"模板渲染失败: {e}")
    
    def get_template(self, template_name: str) -> Optional[str]:
        """
        获取模板
        
        Args:
            template_name: 模板名称
            
        Returns:
            模板字符串
        """
        # 优先查找自定义模板
        if template_name in self.custom_templates:
            return self.custom_templates[template_name]
        
        # 查找预定义模板
        if template_name in self.templates:
            return self.templates[template_name]
        
        return None
    
    def add_template(self, template_name: str, template: str):
        """
        添加自定义模板
        
        Args:
            template_name: 模板名称
            template: 模板字符串
        """
        self.custom_templates[template_name] = template
        print(f"✓ 模板已添加: {template_name}")
    
    def remove_template(self, template_name: str):
        """
        移除模板
        
        Args:
            template_name: 模板名称
        """
        if template_name in self.custom_templates:
            del self.custom_templates[template_name]
            print(f"✓ 模板已移除: {template_name}")
        elif template_name in self.templates:
            print(f"⚠ 预定义模板无法移除: {template_name}")
        else:
            print(f"⚠ 模板不存在: {template_name}")
    
    def list_templates(self) -> Dict[str, str]:
        """
        列出所有模板
        
        Returns:
            模板字典
        """
        all_templates = {}
        all_templates.update(self.templates)
        all_templates.update(self.custom_templates)
        return all_templates
    
    def validate_template(self, template: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证模板
        
        Args:
            template: 模板字符串
            context: 上下文变量
            
        Returns:
            验证结果
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'rendered': None
        }
        
        try:
            # 检查变量是否完整
            required_vars = self._extract_variables(template)
            missing_vars = [var for var in required_vars if var not in context]
            
            if missing_vars:
                result['warnings'].append(f"缺失变量: {', '.join(missing_vars)}")
            
            # 尝试渲染
            result['rendered'] = template.format(**context)
            
        except KeyError as e:
            result['valid'] = False
            result['errors'].append(f"变量缺失: {e}")
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"渲染失败: {e}")
        
        return result
    
    def _extract_variables(self, template: str) -> set:
        """
        提取模板中的变量
        
        Args:
            template: 模板字符串
            
        Returns:
            变量集合
        """
        # 使用正则表达式提取 {variable} 格式的变量
        pattern = r'\{([^}]+)\}'
        matches = re.findall(pattern, template)
        
        # 移除格式说明符（如 {season:02d} -> season）
        variables = set()
        for match in matches:
            # 分割变量名和格式说明符
            var_name = match.split(':')[0]
            variables.add(var_name)
        
        return variables
    
    def preview(self, template_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        预览模板渲染结果
        
        Args:
            template_name: 模板名称
            context: 上下文变量
            
        Returns:
            预览结果
        """
        result = {
            'template_name': template_name,
            'template': None,
            'rendered': None,
            'variables': {},
            'validation': {}
        }
        
        # 获取模板
        template = self.get_template(template_name)
        if not template:
            result['validation']['errors'] = [f"模板不存在: {template_name}"]
            return result
        
        result['template'] = template
        
        # 提取变量
        result['variables'] = self._extract_variables(template)
        
        # 验证模板
        result['validation'] = self.validate_template(template, context)
        
        if result['validation']['valid']:
            result['rendered'] = result['validation']['rendered']
        
        return result


# 全局实例
_template_engine = None


def get_template_engine() -> TemplateEngine:
    """获取模板引擎实例（单例模式）"""
    global _template_engine
    if _template_engine is None:
        _template_engine = TemplateEngine()
    return _template_engine


def render_template(template_name: str, context: Dict[str, Any]) -> str:
    """
    快捷方法：渲染模板
    
    Args:
        template_name: 模板名称
        context: 上下文变量
        
    Returns:
        渲染后的字符串
    """
    engine = get_template_engine()
    return engine.render(template_name, context)


if __name__ == '__main__':
    # 测试模板引擎
    print("测试模板引擎")
    print("="*60)
    
    engine = TemplateEngine()
    
    # 测试电影模板
    movie_context = {
        'title': '流浪地球',
        'year': '2023',
        'resolution': '1080p',
        'source': 'BluRay',
        'video_codec': 'H264',
        'audio_codec': 'DTS-HD',
        'quality': 'High',
        'ext': 'mkv'
    }
    
    print("\n电影模板测试:")
    print("-" * 60)
    
    for template_name in ['movie_default', 'movie_detailed', 'plex_movie']:
        try:
            result = engine.render(template_name, movie_context)
            print(f"{template_name}: {result}")
        except Exception as e:
            print(f"{template_name}: 错误 - {e}")
    
    # 测试电视剧模板
    tv_context = {
        'title': '权力的游戏',
        'season': 1,
        'episode': 5,
        'resolution': '1080p',
        'source': 'WEB-DL',
        'video_codec': 'H265',
        'audio_codec': 'AAC',
        'quality': 'Good',
        'ext': 'mp4'
    }
    
    print("\n电视剧模板测试:")
    print("-" * 60)
    
    for template_name in ['tv_default', 'tv_detailed', 'jellyfin_tv']:
        try:
            result = engine.render(template_name, tv_context)
            print(f"{template_name}: {result}")
        except Exception as e:
            print(f"{template_name}: 错误 - {e}")
    
    # 测试模板预览
    print("\n模板预览测试:")
    print("-" * 60)
    
    preview_result = engine.preview('movie_default', movie_context)
    print(f"模板名称: {preview_result['template_name']}")
    print(f"模板内容: {preview_result['template']}")
    print(f"渲染结果: {preview_result['rendered']}")
    print(f"所需变量: {preview_result['variables']}")
    print(f"验证结果: {preview_result['validation']}")
    
    # 测试自定义模板
    print("\n自定义模板测试:")
    print("-" * 60)
    
    custom_template = "{title} - {year} [{quality}]/{title} - {year}.{ext}"
    engine.add_template('custom_movie', custom_template)
    
    result = engine.render('custom_movie', movie_context)
    print(f"自定义模板结果: {result}")
    
    # 列出所有模板
    print("\n所有可用模板:")
    print("-" * 60)
    
    templates = engine.list_templates()
    for name in sorted(templates.keys()):
        print(f"  {name}")