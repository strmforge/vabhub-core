#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文数字转换模块
支持中文数字到阿拉伯数字的转换，集成cn2an库
增强版：支持复杂中文数字转换和错误处理
"""

import re
import logging

logger = logging.getLogger(__name__)


def chinese_to_arabic(chinese_str):
    """
    将中文数字转换为阿拉伯数字
    
    Args:
        chinese_str: 包含中文数字的字符串
        
    Returns:
        str: 转换后的字符串
    """
    if not chinese_str:
        return chinese_str
    
    # 尝试使用cn2an库进行精确转换
    try:
        import cn2an
        # 使用cn2an进行智能转换
        return str(cn2an.cn2an(chinese_str, "smart"))
    except ImportError:
        # cn2an不可用，使用基础转换
        logger.warning("cn2an库未安装，使用基础中文数字转换")
    except Exception as e:
        # cn2an转换失败，使用基础转换
        logger.warning(f"cn2an转换失败: {str(e)}，使用基础转换")
    
    # 增强版中文数字映射
    chinese_numerals = {
        '零': '0', '一': '1', '二': '2', '三': '3', '四': '4',
        '五': '5', '六': '6', '七': '7', '八': '8', '九': '9',
        '十': '10', '百': '100', '千': '1000', '万': '10000', '亿': '100000000',
        '壹': '1', '贰': '2', '叁': '3', '肆': '4', '伍': '5',
        '陆': '6', '柒': '7', '捌': '8', '玖': '9', '拾': '10',
        '佰': '100', '仟': '1000', '萬': '10000', '億': '100000000'
    }
    
    # 复杂中文数字转换逻辑
    def convert_complex_chinese(text):
        """转换复杂中文数字"""
        # 处理简单数字
        for chinese, arabic in chinese_numerals.items():
            text = text.replace(chinese, arabic)
        
        # 处理复杂数字组合
        # 例如：一百二十三 -> 123
        patterns = [
            (r'(\d+)百(\d+)十(\d+)', lambda m: str(int(m.group(1)) * 100 + int(m.group(2)) * 10 + int(m.group(3)))),
            (r'(\d+)百(\d+)', lambda m: str(int(m.group(1)) * 100 + int(m.group(2)))),
            (r'(\d+)十(\d+)', lambda m: str(int(m.group(1)) * 10 + int(m.group(2)))),
            (r'十(\d+)', lambda m: str(10 + int(m.group(1)))),
            (r'(\d+)千(\d+)百(\d+)十(\d+)', lambda m: str(int(m.group(1)) * 1000 + int(m.group(2)) * 100 + int(m.group(3)) * 10 + int(m.group(4)))),
        ]
        
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text)
        
        return text
    
    return convert_complex_chinese(chinese_str)


class ChineseNumber:
    """中文数字转换器类"""
    
    def __init__(self, use_cn2an: bool = True):
        self.use_cn2an = use_cn2an
        
        # 基础中文数字映射
        self.basic_numerals = {
            '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
            '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
            '十': 10, '百': 100, '千': 1000, '万': 10000, '亿': 100000000,
            '壹': 1, '贰': 2, '叁': 3, '肆': 4, '伍': 5,
            '陆': 6, '柒': 7, '捌': 8, '玖': 9, '拾': 10,
            '佰': 100, '仟': 1000, '萬': 10000, '億': 100000000
        }
        
        # 中文数字单位
        self.units = ['十', '百', '千', '万', '亿', '拾', '佰', '仟', '萬', '億']
        
        # 中文数字正则模式
        self.chinese_number_pattern = re.compile(
            r'[零一二三四五六七八九十百千万亿壹贰叁肆伍陆柒捌玖拾佰仟萬億]+'
        )
    
    def convert(self, text: str) -> str:
        """
        转换文本中的中文数字
        
        Args:
            text: 输入文本
            
        Returns:
            str: 转换后的文本
        """
        if not text:
            return text
        
        # 使用cn2an库进行精确转换
        if self.use_cn2an:
            try:
                import cn2an
                return cn2an.transform(text, "cn2an")
            except (ImportError, Exception) as e:
                logger.warning(f"cn2an转换失败: {str(e)}，使用基础转换")
        
        # 基础转换逻辑
        def replace_chinese_number(match):
            chinese_num = match.group()
            try:
                return self._convert_chinese_number(chinese_num)
            except Exception as e:
                logger.warning(f"中文数字转换失败: {chinese_num}, 错误: {str(e)}")
                return chinese_num
        
        # 替换所有中文数字
        return self.chinese_number_pattern.sub(replace_chinese_number, text)
    
    def _convert_chinese_number(self, chinese_num: str) -> str:
        """转换单个中文数字"""
        if not chinese_num:
            return ""
        
        # 简单数字直接转换
        if len(chinese_num) == 1:
            return str(self.basic_numerals.get(chinese_num, chinese_num))
        
        # 复杂数字转换逻辑
        result = 0
        temp = 0
        last_unit = 1
        
        for char in chinese_num:
            if char in self.basic_numerals:
                value = self.basic_numerals[char]
                if value < 10:  # 基本数字
                    temp = value
                else:  # 单位
                    if temp == 0:
                        temp = 1
                    result += temp * value
                    temp = 0
                    last_unit = value
            else:
                # 非数字字符，保留原样
                return chinese_num
        
        # 处理剩余的数字
        result += temp
        
        return str(result)
    
    def extract_chinese_numbers(self, text: str) -> list:
        """
        提取文本中的所有中文数字
        
        Args:
            text: 输入文本
            
        Returns:
            list: 中文数字列表
        """
        return self.chinese_number_pattern.findall(text)
    
    def has_chinese_numbers(self, text: str) -> bool:
        """
        检查文本是否包含中文数字
        
        Args:
            text: 输入文本
            
        Returns:
            bool: 是否包含中文数字
        """
        return bool(self.chinese_number_pattern.search(text))
    
    def convert_filename(self, filename: str) -> str:
        """
        转换文件名中的中文数字
        特别处理季集信息
        
        Args:
            filename: 文件名
            
        Returns:
            str: 转换后的文件名
        """
        if not filename:
            return filename
        
        # 特别处理季集信息
        season_patterns = [
            (r'第([零一二三四五六七八九十百]+)季', self._convert_season),
            (r'第([零一二三四五六七八九十百]+)部', self._convert_season),
            (r'S([零一二三四五六七八九十百]+)', self._convert_season),
        ]
        
        result = filename
        for pattern, converter in season_patterns:
            result = re.sub(pattern, converter, result)
        
        # 转换其他中文数字
        result = self.convert(result)
        
        return result
    
    def _convert_season(self, match) -> str:
        """转换季信息"""
        chinese_season = match.group(1)
        try:
            arabic_season = self._convert_chinese_number(chinese_season)
            return match.group().replace(chinese_season, arabic_season)
        except Exception:
            return match.group()


# 全局实例
_chinese_number = None


def get_chinese_number(use_cn2an: bool = True) -> ChineseNumber:
    """获取中文数字转换器实例（单例模式）"""
    global _chinese_number
    if _chinese_number is None:
        _chinese_number = ChineseNumber(use_cn2an=use_cn2an)
    return _chinese_number


def convert_chinese_number(text: str, use_cn2an: bool = True) -> str:
    """
    快捷方法：转换文本中的中文数字
    
    Args:
        text: 输入文本
        use_cn2an: 是否使用cn2an库
        
    Returns:
        str: 转换后的文本
    """
    converter = get_chinese_number(use_cn2an)
    return converter.convert(text)


def convert_filename_chinese_numbers(filename: str) -> str:
    """
    快捷方法：转换文件名中的中文数字
    
    Args:
        filename: 文件名
        
    Returns:
        str: 转换后的文件名
    """
    converter = get_chinese_number()
    return converter.convert_filename(filename)