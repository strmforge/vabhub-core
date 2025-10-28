"""
统一分类管理器
集成VabHub的二级分类系统与MoviePilot模式，支持电影、电视剧、音乐等多种媒体类型
"""

import os
import re
import yaml
import json
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime

from .music_classifier import MusicClassifier


class UnifiedClassifier:
    """统一分类管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.logger = logging.getLogger("unified_classifier")
        
        # 加载配置
        self.config_path = config_path or "config/unified_categories.yaml"
        self.config = self._load_config()
        
        # 初始化各类型分类器
        self.music_classifier = MusicClassifier()
        
        # 媒体类型映射
        self.media_types = {
            "movie": "电影",
            "tv": "电视剧", 
            "music": "音乐",
            "anime": "动漫",
            "documentary": "纪录片"
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """加载统一分类配置"""
        default_config = {
            "movie": {
                "name": "电影",
                "description": "电影作品",
                "patterns": ["*电影*", "*Movie*", "*Cinema*", "*Film*"],
                "file_patterns": ["*.mp4", "*.mkv", "*.avi"],
                "sub_categories": {
                    "动画电影": {"genre_ids": "16"},
                    "华语电影": {"original_language": "zh,cn,bo,za"},
                    "外语电影": {}
                }
            },
            "tv": {
                "name": "电视剧",
                "description": "电视剧集",
                "patterns": ["*剧集*", "*TV*", "*Season*", "*Episode*", "*S\\d{2}E\\d{2}*"],
                "file_patterns": ["*.mp4", "*.mkv", "*.avi"],
                "sub_categories": {
                    "国漫": {"genre_ids": "16", "origin_country": "CN,TW,HK"},
                    "日番": {"genre_ids": "16", "origin_country": "JP"},
                    "纪录片": {"genre_ids": "99"},
                    "儿童": {"genre_ids": "10762"},
                    "综艺": {"genre_ids": "10764,10767"},
                    "国产剧": {"origin_country": "CN,TW,HK"},
                    "欧美剧": {"origin_country": "US,FR,GB,DE,ES,IT,NL,PT,RU,UK"},
                    "日韩剧": {"origin_country": "JP,KP,KR,TH,IN,SG"},
                    "未分类": {}
                }
            },
            "music": {
                "name": "音乐",
                "description": "音乐作品",
                "patterns": ["*音乐*", "*Music*", "*Album*", "*Track*"],
                "file_patterns": ["*.mp3", "*.flac", "*.wav", "*.aac"],
                "sub_categories": {
                    "流行音乐": {"genre_ids": "14", "patterns": ["*pop*", "*流行*", "*POP*"]},
                    "摇滚音乐": {"genre_ids": "21", "patterns": ["*rock*", "*摇滚*", "*ROCK*"]},
                    "古典音乐": {"genre_ids": "32", "patterns": ["*classical*", "*古典*", "*Classical*"]},
                    "爵士音乐": {"genre_ids": "8", "patterns": ["*jazz*", "*爵士*", "*Jazz*"]},
                    "电子音乐": {"genre_ids": "7", "patterns": ["*electronic*", "*电子*", "*Electronic*"]},
                    "华语音乐": {"country_codes": ["CN", "TW", "HK"], "patterns": ["*中文*", "*华语*", "*Chinese*"]},
                    "欧美音乐": {"country_codes": ["US", "GB", "FR", "DE"], "patterns": ["*欧美*", "*Western*", "*English*"]},
                    "日本音乐": {"country_codes": ["JP"], "patterns": ["*日语*", "*日本*", "*Japanese*"]},
                    "韩国音乐": {"country_codes": ["KR"], "patterns": ["*韩语*", "*韩国*", "*Korean*"]},
                    "无损音乐": {"patterns": ["*FLAC*", "*APE*", "*WAV*"], "bitrate": ">=800"},
                    "高品质": {"patterns": ["*320k*", "*V0*"], "bitrate": "320"},
                    "未分类": {}
                }
            }
        }
        
        try:
            config_path = Path(self.config_path)
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or default_config
            else:
                # 创建默认配置文件
                config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(default_config, f, allow_unicode=True, indent=2)
                return default_config
        except Exception as e:
            self.logger.error(f"加载统一分类配置失败: {e}")
            return default_config
    
    def detect_media_type(self, file_path: str) -> Optional[str]:
        """检测媒体类型"""
        try:
            file_name = Path(file_path).name.lower()
            file_ext = Path(file_path).suffix.lower()
            
            # 检查文件扩展名
            for media_type, config in self.config.items():
                file_patterns = config.get("file_patterns", [])
                for pattern in file_patterns:
                    if pattern.startswith('*') and file_ext in pattern:
                        return media_type
            
            # 检查文件名模式
            for media_type, config in self.config.items():
                patterns = config.get("patterns", [])
                for pattern in patterns:
                    if self._pattern_match(file_name, pattern):
                        return media_type
            
            return None
            
        except Exception as e:
            self.logger.error(f"检测媒体类型失败: {e}")
            return None
    
    def classify_media(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """分类媒体文件"""
        try:
            # 检测媒体类型
            media_type = self.detect_media_type(file_path)
            if not media_type:
                return {
                    "media_type": "unknown",
                    "primary_category": "unknown",
                    "sub_categories": {},
                    "confidence": 0.0,
                    "matched_rules": []
                }
            
            # 根据媒体类型调用相应的分类器
            if media_type == "music":
                return self.music_classifier.classify_music(file_path, metadata)
            else:
                return self._classify_video(file_path, media_type, metadata)
            
        except Exception as e:
            self.logger.error(f"分类媒体文件失败: {e}")
            return {
                "media_type": "unknown",
                "primary_category": "unknown", 
                "sub_categories": {},
                "confidence": 0.0,
                "matched_rules": []
            }
    
    def _classify_video(self, file_path: str, media_type: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """分类视频文件（电影/电视剧）"""
        try:
            result = {
                "media_type": media_type,
                "primary_category": media_type,
                "sub_categories": {},
                "confidence": 0.0,
                "matched_rules": []
            }
            
            file_name = Path(file_path).name.lower()
            config = self.config.get(media_type, {})
            sub_categories = config.get("sub_categories", {})
            
            # 应用MoviePilot风格的分类规则
            for category_name, category_config in sub_categories.items():
                if self._match_video_category(file_name, metadata, category_config):
                    result["sub_categories"][category_name] = {
                        "name": category_name,
                        "type": "video",
                        "config": category_config
                    }
                    result["matched_rules"].append(category_name)
            
            # 计算置信度
            if result["sub_categories"]:
                result["confidence"] = min(1.0, len(result["matched_rules"]) * 0.3)
            
            return result
            
        except Exception as e:
            self.logger.error(f"分类视频文件失败: {e}")
            return {
                "media_type": media_type,
                "primary_category": media_type,
                "sub_categories": {},
                "confidence": 0.0,
                "matched_rules": []
            }
    
    def _match_video_category(self, file_name: str, metadata: Optional[Dict[str, Any]], 
                            category_config: Dict[str, Any]) -> bool:
        """匹配视频分类规则"""
        
        # 检查文件名模式匹配
        patterns = category_config.get("patterns", [])
        for pattern in patterns:
            if self._pattern_match(file_name, pattern):
                return True
        
        # 检查元数据匹配
        if metadata:
            # 流派匹配
            genre_ids = category_config.get("genre_ids", "")
            if genre_ids and metadata.get("genre_ids"):
                metadata_genres = str(metadata["genre_ids"]).split(',') if isinstance(metadata["genre_ids"], str) else metadata["genre_ids"]
                config_genres = genre_ids.split(',') if isinstance(genre_ids, str) else genre_ids
                
                for genre in metadata_genres:
                    if genre.strip() in config_genres:
                        return True
            
            # 语言匹配
            languages = category_config.get("original_language", "")
            if languages and metadata.get("original_language"):
                metadata_langs = str(metadata["original_language"]).split(',') if isinstance(metadata["original_language"], str) else metadata["original_language"]
                config_langs = languages.split(',') if isinstance(languages, str) else languages
                
                for lang in metadata_langs:
                    if lang.strip() in config_langs:
                        return True
            
            # 国家匹配
            countries = category_config.get("origin_country", "")
            if countries and metadata.get("origin_country"):
                metadata_countries = str(metadata["origin_country"]).split(',') if isinstance(metadata["origin_country"], str) else metadata["origin_country"]
                config_countries = countries.split(',') if isinstance(countries, str) else countries
                
                for country in metadata_countries:
                    if country.strip() in config_countries:
                        return True
            
            # 生产国家匹配（电影）
            production_countries = category_config.get("production_countries", "")
            if production_countries and metadata.get("production_countries"):
                metadata_countries = str(metadata["production_countries"]).split(',') if isinstance(metadata["production_countries"], str) else metadata["production_countries"]
                config_countries = production_countries.split(',') if isinstance(production_countries, str) else production_countries
                
                for country in metadata_countries:
                    if country.strip() in config_countries:
                        return True
        
        # 如果没有配置任何规则，则默认匹配
        if not any([patterns, category_config.get("genre_ids"), category_config.get("original_language"), 
                   category_config.get("origin_country"), category_config.get("production_countries")]):
            return True
        
        return False
    
    def _pattern_match(self, text: str, pattern: str) -> bool:
        """模式匹配（支持通配符）"""
        try:
            # 将通配符模式转换为正则表达式
            regex_pattern = pattern.replace('*', '.*').replace('?', '.')
            return bool(re.search(regex_pattern, text, re.IGNORECASE))
        except:
            return False
    
    def get_media_directory_structure(self, classification: Dict[str, Any]) -> str:
        """根据分类结果生成目录结构"""
        try:
            media_type = classification.get("media_type", "unknown")
            sub_categories = classification.get("sub_categories", {})
            
            # 根目录
            if media_type == "movie":
                path_parts = ["Movies"]
            elif media_type == "tv":
                path_parts = ["TV Shows"]
            elif media_type == "music":
                path_parts = ["Music"]
            elif media_type == "anime":
                path_parts = ["Anime"]
            elif media_type == "documentary":
                path_parts = ["Documentaries"]
            else:
                path_parts = ["Other"]
            
            # 添加子分类
            if sub_categories:
                # 对于视频类型，使用MoviePilot的分类名称
                if media_type in ["movie", "tv"]:
                    for category_name in sub_categories.keys():
                        path_parts.append(category_name)
                        break  # 只取第一个匹配的分类
                # 对于音乐类型，使用多级分类
                elif media_type == "music":
                    music_categories = sub_categories.get("music", {})
                    for category_type in ["genre", "region", "decade", "quality"]:
                        if category_type in music_categories:
                            category_info = music_categories[category_type]
                            path_parts.append(category_info["name"])
            
            # 如果没有匹配到任何子分类，使用默认分类
            if len(path_parts) == 1:
                path_parts.append("未分类")
            
            return "/".join(path_parts)
            
        except Exception as e:
            self.logger.error(f"生成目录结构失败: {e}")
            return "Other/未分类"
    
    def batch_classify(self, file_paths: List[str]) -> Dict[str, Dict[str, Any]]:
        """批量分类媒体文件"""
        results = {}
        
        for file_path in file_paths:
            try:
                classification = self.classify_media(file_path)
                results[file_path] = classification
            except Exception as e:
                self.logger.error(f"分类文件失败 {file_path}: {e}")
                results[file_path] = {
                    "media_type": "unknown",
                    "primary_category": "unknown",
                    "sub_categories": {},
                    "confidence": 0.0,
                    "matched_rules": []
                }
        
        return results
    
    def export_classification_config(self, output_path: str) -> bool:
        """导出分类配置"""
        try:
            output_data = {
                "timestamp": datetime.now().isoformat(),
                "config": self.config,
                "media_types": self.media_types
            }
            
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            self.logger.error(f"导出分类配置失败: {e}")
            return False
    
    def import_classification_config(self, config_path: str) -> bool:
        """导入分类配置"""
        try:
            config_path = Path(config_path)
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    imported_config = json.load(f)
                
                # 更新配置
                self.config.update(imported_config.get("config", {}))
                
                # 保存到配置文件
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(self.config, f, allow_unicode=True, indent=2)
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"导入分类配置失败: {e}")
            return False
    
    def get_classification_statistics(self, classifications: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """获取分类统计信息"""
        stats = {
            "total_files": len(classifications),
            "media_type_distribution": {},
            "categorized_files": 0,
            "uncategorized_files": 0,
            "confidence_distribution": {
                "high": 0,    # >= 0.8
                "medium": 0,  # 0.5-0.8
                "low": 0      # < 0.5
            }
        }
        
        for file_path, classification in classifications.items():
            media_type = classification.get("media_type", "unknown")
            confidence = classification.get("confidence", 0.0)
            
            # 媒体类型分布
            if media_type not in stats["media_type_distribution"]:
                stats["media_type_distribution"][media_type] = 0
            stats["media_type_distribution"][media_type] += 1
            
            # 分类统计
            if confidence > 0:
                stats["categorized_files"] += 1
            else:
                stats["uncategorized_files"] += 1
            
            # 置信度分布
            if confidence >= 0.8:
                stats["confidence_distribution"]["high"] += 1
            elif confidence >= 0.5:
                stats["confidence_distribution"]["medium"] += 1
            else:
                stats["confidence_distribution"]["low"] += 1
        
        return stats


# 全局实例
unified_classifier = UnifiedClassifier()