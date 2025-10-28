"""
音乐分类系统
集成VabHub的二级分类系统与MoviePilot模式，创建音乐详细分类策略
"""

import os
import re
import yaml
import json
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime


class MusicClassifier:
    """音乐分类器"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.logger = logging.getLogger("music_classifier")
        
        # 默认音乐分类配置
        self.default_categories = {
            "music": {
                "name": "音乐",
                "description": "音乐作品",
                "patterns": ["*音乐*", "*Music*", "*Album*", "*Track*"],
                "file_patterns": ["*.mp3", "*.flac", "*.wav", "*.aac"],
                
                # 二级分类策略（基于MoviePilot模式）
                "sub_categories": {
                    # 按流派分类
                    "genre": {
                        "pop": {"name": "流行音乐", "patterns": ["*pop*", "*流行*", "*POP*"], "genre_ids": ["14"]},
                        "rock": {"name": "摇滚音乐", "patterns": ["*rock*", "*摇滚*", "*ROCK*"], "genre_ids": ["21"]},
                        "classical": {"name": "古典音乐", "patterns": ["*classical*", "*古典*", "*Classical*"], "genre_ids": ["32"]},
                        "jazz": {"name": "爵士音乐", "patterns": ["*jazz*", "*爵士*", "*Jazz*"], "genre_ids": ["8"]},
                        "electronic": {"name": "电子音乐", "patterns": ["*electronic*", "*电子*", "*Electronic*"], "genre_ids": ["7"]},
                        "hiphop": {"name": "嘻哈音乐", "patterns": ["*hiphop*", "*嘻哈*", "*HipHop*"], "genre_ids": ["18"]},
                        "country": {"name": "乡村音乐", "patterns": ["*country*", "*乡村*", "*Country*"], "genre_ids": ["6"]},
                        "rnb": {"name": "R&B音乐", "patterns": ["*rnb*", "*R&B*", "*节奏布鲁斯*"], "genre_ids": ["15"]},
                        "folk": {"name": "民谣音乐", "patterns": ["*folk*", "*民谣*", "*Folk*"], "genre_ids": ["16"]},
                        "metal": {"name": "金属音乐", "patterns": ["*metal*", "*金属*", "*Metal*"], "genre_ids": ["9"]},
                        "blues": {"name": "蓝调音乐", "patterns": ["*blues*", "*蓝调*", "*Blues*"], "genre_ids": ["2"]},
                        "reggae": {"name": "雷鬼音乐", "patterns": ["*reggae*", "*雷鬼*", "*Reggae*"], "genre_ids": ["17"]},
                        "world": {"name": "世界音乐", "patterns": ["*world*", "*世界*", "*World*"], "genre_ids": ["19"]},
                        "newage": {"name": "新世纪音乐", "patterns": ["*newage*", "*新世纪*", "*NewAge*"], "genre_ids": ["10"]},
                        "soundtrack": {"name": "影视原声", "patterns": ["*soundtrack*", "*原声*", "*OST*"], "genre_ids": ["16"]}
                    },
                    
                    # 按地区分类
                    "region": {
                        "chinese": {"name": "华语音乐", "patterns": ["*中文*", "*华语*", "*Chinese*"], "country_codes": ["CN", "TW", "HK"]},
                        "western": {"name": "欧美音乐", "patterns": ["*欧美*", "*Western*", "*English*"], "country_codes": ["US", "GB", "FR", "DE"]},
                        "japanese": {"name": "日本音乐", "patterns": ["*日语*", "*日本*", "*Japanese*"], "country_codes": ["JP"]},
                        "korean": {"name": "韩国音乐", "patterns": ["*韩语*", "*韩国*", "*Korean*"], "country_codes": ["KR"]},
                        "southeast_asia": {"name": "东南亚音乐", "patterns": ["*东南亚*", "*泰国*", "*越南*"], "country_codes": ["TH", "VN", "ID"]},
                        "latin": {"name": "拉丁音乐", "patterns": ["*拉丁*", "*Spanish*", "*Portuguese*"], "country_codes": ["ES", "PT", "MX"]}
                    },
                    
                    # 按年代分类
                    "decade": {
                        "1950s": {"name": "50年代", "year_range": "1950-1959"},
                        "1960s": {"name": "60年代", "year_range": "1960-1969"},
                        "1970s": {"name": "70年代", "year_range": "1970-1979"},
                        "1980s": {"name": "80年代", "year_range": "1980-1989"},
                        "1990s": {"name": "90年代", "year_range": "1990-1999"},
                        "2000s": {"name": "00年代", "year_range": "2000-2009"},
                        "2010s": {"name": "10年代", "year_range": "2010-2019"},
                        "2020s": {"name": "20年代", "year_range": "2020-2029"}
                    },
                    
                    # 按质量分类
                    "quality": {
                        "lossless": {"name": "无损音乐", "patterns": ["*FLAC*", "*APE*", "*WAV*"], "bitrate": ">=800"},
                        "high": {"name": "高品质", "patterns": ["*320k*", "*V0*"], "bitrate": "320"},
                        "standard": {"name": "标准品质", "patterns": ["*192k*", "*V2*"], "bitrate": "192"},
                        "low": {"name": "低品质", "patterns": ["*128k*"], "bitrate": "128"}
                    },
                    
                    # 按专辑类型分类
                    "album_type": {
                        "studio": {"name": "录音室专辑", "patterns": ["*Studio*", "*录音室*"], "album_types": ["album"]},
                        "live": {"name": "现场专辑", "patterns": ["*Live*", "*现场*"], "album_types": ["live"]},
                        "compilation": {"name": "精选集", "patterns": ["*Compilation*", "*精选*"], "album_types": ["compilation"]},
                        "ep": {"name": "EP专辑", "patterns": ["*EP*", "*迷你专辑*"], "album_types": ["ep"]},
                        "single": {"name": "单曲", "patterns": ["*Single*", "*单曲*"], "album_types": ["single"]},
                        "soundtrack": {"name": "原声带", "patterns": ["*Soundtrack*", "*OST*"], "album_types": ["soundtrack"]}
                    }
                }
            }
        }
        
        # 加载配置
        self.config_path = config_path or "config/music_categories.yaml"
        self.categories = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载分类配置"""
        try:
            config_path = Path(self.config_path)
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or self.default_categories
            else:
                # 创建默认配置文件
                config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(self.default_categories, f, allow_unicode=True, indent=2)
                return self.default_categories
        except Exception as e:
            self.logger.error(f"加载分类配置失败: {e}")
            return self.default_categories
    
    def classify_music(self, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """分类音乐文件"""
        try:
            result = {
                "primary_category": "music",
                "sub_categories": {},
                "confidence": 0.0,
                "matched_rules": []
            }
            
            file_name = Path(file_path).name.lower()
            
            # 检查是否为音乐文件
            if not self._is_music_file(file_path):
                return result
            
            # 应用分类规则
            music_config = self.categories.get("music", {})
            sub_categories = music_config.get("sub_categories", {})
            
            for category_type, categories in sub_categories.items():
                for category_id, category_config in categories.items():
                    if self._match_category(file_name, metadata, category_config):
                        result["sub_categories"][category_type] = {
                            "id": category_id,
                            "name": category_config.get("name", category_id),
                            "type": category_type
                        }
                        result["matched_rules"].append(f"{category_type}.{category_id}")
            
            # 计算置信度
            if result["sub_categories"]:
                result["confidence"] = min(1.0, len(result["matched_rules"]) * 0.2)
            
            return result
            
        except Exception as e:
            self.logger.error(f"分类音乐文件失败: {e}")
            return {"primary_category": "music", "sub_categories": {}, "confidence": 0.0, "matched_rules": []}
    
    def _is_music_file(self, file_path: str) -> bool:
        """检查是否为音乐文件"""
        music_extensions = {'.mp3', '.flac', '.wav', '.aac', '.ogg', '.m4a', '.wma', '.ape'}
        return Path(file_path).suffix.lower() in music_extensions
    
    def _match_category(self, file_name: str, metadata: Optional[Dict[str, Any]], 
                       category_config: Dict[str, Any]) -> bool:
        """匹配分类规则"""
        
        # 检查文件名模式匹配
        patterns = category_config.get("patterns", [])
        for pattern in patterns:
            if self._pattern_match(file_name, pattern):
                return True
        
        # 检查元数据匹配
        if metadata:
            # 流派匹配
            genre_ids = category_config.get("genre_ids", [])
            if genre_ids and metadata.get("genre") in genre_ids:
                return True
            
            # 国家代码匹配
            country_codes = category_config.get("country_codes", [])
            if country_codes and metadata.get("country") in country_codes:
                return True
            
            # 年代匹配
            year_range = category_config.get("year_range", "")
            if year_range and metadata.get("year"):
                if self._year_in_range(metadata["year"], year_range):
                    return True
            
            # 比特率匹配
            bitrate_rule = category_config.get("bitrate", "")
            if bitrate_rule and metadata.get("bitrate"):
                if self._bitrate_match(metadata["bitrate"], bitrate_rule):
                    return True
            
            # 专辑类型匹配
            album_types = category_config.get("album_types", [])
            if album_types and metadata.get("album_type") in album_types:
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
    
    def _year_in_range(self, year: int, year_range: str) -> bool:
        """检查年份是否在范围内"""
        try:
            if '-' in year_range:
                start, end = map(int, year_range.split('-'))
                return start <= year <= end
            else:
                return year == int(year_range)
        except:
            return False
    
    def _bitrate_match(self, bitrate: int, rule: str) -> bool:
        """比特率匹配"""
        try:
            if rule.startswith('>='):
                return bitrate >= int(rule[2:])
            elif rule.startswith('>'):
                return bitrate > int(rule[1:])
            elif rule.startswith('<='):
                return bitrate <= int(rule[2:])
            elif rule.startswith('<'):
                return bitrate < int(rule[1:])
            else:
                return bitrate == int(rule)
        except:
            return False
    
    def get_category_path(self, classification: Dict[str, Any]) -> str:
        """根据分类结果生成目录路径"""
        try:
            path_parts = ["Music"]  # 根目录
            
            sub_categories = classification.get("sub_categories", {})
            
            # 按优先级添加子分类
            priority_order = ["genre", "region", "decade", "quality", "album_type"]
            
            for category_type in priority_order:
                if category_type in sub_categories:
                    category_info = sub_categories[category_type]
                    path_parts.append(category_info["name"])
            
            # 如果没有匹配到任何子分类，使用默认分类
            if len(path_parts) == 1:
                path_parts.append("未分类")
            
            return "/".join(path_parts)
            
        except Exception as e:
            self.logger.error(f"生成分类路径失败: {e}")
            return "Music/未分类"
    
    def batch_classify(self, file_paths: List[str]) -> Dict[str, Dict[str, Any]]:
        """批量分类音乐文件"""
        results = {}
        
        for file_path in file_paths:
            try:
                classification = self.classify_music(file_path)
                results[file_path] = classification
            except Exception as e:
                self.logger.error(f"分类文件失败 {file_path}: {e}")
                results[file_path] = {
                    "primary_category": "music",
                    "sub_categories": {},
                    "confidence": 0.0,
                    "matched_rules": []
                }
        
        return results
    
    def get_category_statistics(self, classifications: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """获取分类统计信息"""
        stats = {
            "total_files": len(classifications),
            "categorized_files": 0,
            "category_distribution": {},
            "confidence_distribution": {
                "high": 0,    # >= 0.8
                "medium": 0,  # 0.5-0.8
                "low": 0      # < 0.5
            }
        }
        
        for file_path, classification in classifications.items():
            confidence = classification.get("confidence", 0.0)
            
            if confidence > 0:
                stats["categorized_files"] += 1
            
            # 置信度分布
            if confidence >= 0.8:
                stats["confidence_distribution"]["high"] += 1
            elif confidence >= 0.5:
                stats["confidence_distribution"]["medium"] += 1
            else:
                stats["confidence_distribution"]["low"] += 1
            
            # 分类分布
            sub_categories = classification.get("sub_categories", {})
            for category_type, category_info in sub_categories.items():
                category_name = category_info["name"]
                if category_name not in stats["category_distribution"]:
                    stats["category_distribution"][category_name] = 0
                stats["category_distribution"][category_name] += 1
        
        return stats
    
    def export_classification_results(self, classifications: Dict[str, Dict[str, Any]], 
                                    output_path: str) -> bool:
        """导出分类结果"""
        try:
            output_data = {
                "timestamp": datetime.now().isoformat(),
                "classifications": classifications,
                "statistics": self.get_category_statistics(classifications)
            }
            
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            self.logger.error(f"导出分类结果失败: {e}")
            return False


# 全局实例
music_classifier = MusicClassifier()