"""
增强分类器模块 - 基于MoviePilot分类策略
支持电影、电视剧的智能二级分类
"""

import yaml
import logging
from typing import Dict, List, Any, Optional
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class MediaType(Enum):
    """媒体类型"""
    MOVIE = "movie"
    TV = "tv"


class CategoryClassifier:
    """分类器类 - 基于MoviePilot分类策略"""
    
    def __init__(self, config_file: str = "config/categories.yaml"):
        """
        初始化分类器
        
        Args:
            config_file: 分类配置文件路径
        """
        self.config_file = Path(config_file)
        self.categories_config = self._load_categories_config()
        
        # 语种字典
        self.language_dict = {
            'af': '南非语', 'ar': '阿拉伯语', 'az': '阿塞拜疆语', 'be': '比利时语',
            'bg': '保加利亚语', 'ca': '加泰隆语', 'cs': '捷克语', 'cy': '威尔士语',
            'da': '丹麦语', 'de': '德语', 'dv': '第维埃语', 'el': '希腊语',
            'en': '英语', 'eo': '世界语', 'es': '西班牙语', 'et': '爱沙尼亚语',
            'eu': '巴士克语', 'fa': '法斯语', 'fi': '芬兰语', 'fo': '法罗语',
            'fr': '法语', 'gl': '加里西亚语', 'gu': '古吉拉特语', 'he': '希伯来语',
            'hi': '印地语', 'hr': '克罗地亚语', 'hu': '匈牙利语', 'hy': '亚美尼亚语',
            'id': '印度尼西亚语', 'is': '冰岛语', 'it': '意大利语', 'ja': '日语',
            'ka': '格鲁吉亚语', 'kk': '哈萨克语', 'kn': '卡纳拉语', 'ko': '朝鲜语',
            'kok': '孔卡尼语', 'ky': '吉尔吉斯语', 'lt': '立陶宛语', 'lv': '拉脱维亚语',
            'mi': '毛利语', 'mk': '马其顿语', 'mn': '蒙古语', 'mr': '马拉地语',
            'ms': '马来语', 'mt': '马耳他语', 'nb': '挪威语(伯克梅尔)', 'nl': '荷兰语',
            'ns': '北梭托语', 'pa': '旁遮普语', 'pl': '波兰语', 'pt': '葡萄牙语',
            'qu': '克丘亚语', 'ro': '罗马尼亚语', 'ru': '俄语', 'sa': '梵文',
            'se': '北萨摩斯语', 'sk': '斯洛伐克语', 'sl': '斯洛文尼亚语',
            'sq': '阿尔巴尼亚语', 'sv': '瑞典语', 'sw': '斯瓦希里语', 'syr': '叙利亚语',
            'ta': '泰米尔语', 'te': '泰卢固语', 'th': '泰语', 'tl': '塔加路语',
            'tn': '茨瓦纳语', 'tr': '土耳其语', 'ts': '宗加语', 'tt': '鞑靼语',
            'uk': '乌克兰语', 'ur': '乌都语', 'uz': '乌兹别克语', 'vi': '越南语',
            'xh': '班图语', 'zh': '中文', 'cn': '中文', 'zu': '祖鲁语'
        }
        
        # 国家地区字典
        self.country_dict = {
            'AR': '阿根廷', 'AU': '澳大利亚', 'BE': '比利时', 'BR': '巴西',
            'CA': '加拿大', 'CH': '瑞士', 'CL': '智利', 'CO': '哥伦比亚',
            'CZ': '捷克', 'DE': '德国', 'DK': '丹麦', 'EG': '埃及',
            'ES': '西班牙', 'FR': '法国', 'GR': '希腊', 'HK': '香港',
            'IL': '以色列', 'IN': '印度', 'IQ': '伊拉克', 'IR': '伊朗',
            'IT': '意大利', 'JP': '日本', 'MM': '缅甸', 'MO': '澳门',
            'MX': '墨西哥', 'MY': '马来西亚', 'NL': '荷兰', 'NO': '挪威',
            'PH': '菲律宾', 'PK': '巴基斯坦', 'PL': '波兰', 'RU': '俄罗斯',
            'SE': '瑞典', 'SG': '新加坡', 'TH': '泰国', 'TR': '土耳其',
            'US': '美国', 'VN': '越南', 'CN': '中国内地', 'GB': '英国',
            'TW': '中国台湾', 'NZ': '新西兰', 'SA': '沙特阿拉伯',
            'LA': '老挝', 'KP': '朝鲜', 'KR': '韩国', 'PT': '葡萄牙',
            'MN': '蒙古'
        }
        
        # 内容类型字典
        self.genre_dict = {
            '28': '动作', '12': '冒险', '16': '动画', '35': '喜剧',
            '80': '犯罪', '99': '纪录', '18': '剧情', '10751': '家庭',
            '14': '奇幻', '36': '历史', '27': '恐怖', '10402': '音乐',
            '9648': '悬疑', '10749': '爱情', '878': '科幻', '10770': '电视电影',
            '53': '惊悚', '10752': '战争', '37': '西部'
        }
    
    def _load_categories_config(self) -> Dict[str, Any]:
        """加载分类配置文件"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            else:
                logger.warning(f"分类配置文件不存在: {self.config_file}")
                return self._get_default_categories()
        except Exception as e:
            logger.error(f"加载分类配置文件失败: {e}")
            return self._get_default_categories()
    
    def _get_default_categories(self) -> Dict[str, Any]:
        """获取默认分类配置"""
        return {
            "movie": {
                "动画电影": {"genre_ids": "16"},
                "华语电影": {"original_language": "zh,cn,bo,za"},
                "外语电影": {}
            },
            "tv": {
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
        }
    
    def _check_condition(self, condition_value: str, media_value: Any, field_name: str) -> bool:
        """
        检查单个条件是否匹配
        
        Args:
            condition_value: 条件值
            media_value: 媒体值
            field_name: 字段名
        """
        if not condition_value:
            return True
            
        # 处理排除条件
        if condition_value.startswith('!'):
            exclude_values = condition_value[1:].split(',')
            if media_value in exclude_values:
                return False
            return True
        
        # 处理范围条件（年份）
        if field_name == 'release_year' and '-' in condition_value:
            try:
                start_year, end_year = condition_value.split('-')
                if start_year and end_year:
                    return int(start_year) <= int(media_value) <= int(end_year)
            except (ValueError, TypeError):
                pass
        
        # 处理多值条件
        condition_values = condition_value.split(',')
        if isinstance(media_value, list):
            # 媒体值是列表（如origin_country）
            return any(val in media_value for val in condition_values)
        else:
            # 媒体值是单个值
            return str(media_value) in condition_values
    
    def classify_media(self, media_type: MediaType, media_info: Dict[str, Any]) -> str:
        """
        对媒体进行分类
        
        Args:
            media_type: 媒体类型
            media_info: 媒体信息字典
            
        Returns:
            分类名称
        """
        categories = self.categories_config.get(media_type.value, {})
        
        for category_name, conditions in categories.items():
            if self._match_conditions(conditions, media_info):
                return category_name
        
        # 如果没有匹配到任何分类，返回默认分类
        if media_type == MediaType.MOVIE:
            return "外语电影"
        else:
            return "未分类"
    
    def _match_conditions(self, conditions: Dict[str, str], media_info: Dict[str, Any]) -> bool:
        """
        检查媒体信息是否匹配所有条件
        
        Args:
            conditions: 条件字典
            media_info: 媒体信息
        """
        if not conditions:
            return True
            
        for field, condition_value in conditions.items():
            media_value = media_info.get(field)
            
            # 如果条件值不为空但媒体值为空，则不匹配
            if condition_value and media_value is None:
                return False
                
            # 检查条件
            if not self._check_condition(condition_value, media_value, field):
                return False
        
        return True
    
    def get_category_path(self, media_type: MediaType, category_name: str, 
                         title: str, year: Optional[str] = None) -> str:
        """
        获取分类路径
        
        Args:
            media_type: 媒体类型
            category_name: 分类名称
            title: 标题
            year: 年份
            
        Returns:
            完整的分类路径
        """
        if media_type == MediaType.MOVIE:
            if year:
                return f"{category_name}/{title} ({year})"
            else:
                return f"{category_name}/{title}"
        else:
            return f"{category_name}/{title}"
    
    def get_available_categories(self, media_type: MediaType) -> List[str]:
        """
        获取可用的分类列表
        
        Args:
            media_type: 媒体类型
            
        Returns:
            分类名称列表
        """
        return list(self.categories_config.get(media_type.value, {}).keys())
    
    def reload_config(self):
        """重新加载分类配置"""
        self.categories_config = self._load_categories_config()
        logger.info("分类配置已重新加载")


# 全局分类器实例
classifier = CategoryClassifier()