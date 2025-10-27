#!/usr/bin/env python3
"""
基础功能测试
"""
import unittest
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import ConfigManager
from core.media_processor import MediaProcessor


class TestBasicFunctionality(unittest.TestCase):
    """基础功能测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.config_manager = ConfigManager()
        self.media_processor = MediaProcessor()
        
    def test_config_loading(self):
        """测试配置加载"""
        config = self.config_manager.get_config()
        self.assertIsNotNone(config)
        self.assertIn('api_keys', config)
        
    def test_media_processor_initialization(self):
        """测试媒体处理器初始化"""
        self.assertIsNotNone(self.media_processor)
        
    def test_file_scanning(self):
        """测试文件扫描功能"""
        # 创建一个测试文件
        test_file = Path("test_scan.txt")
        test_file.write_text("test content")
        
        try:
            # 测试扫描功能
            files = self.media_processor.scan_directory(".")
            self.assertIsInstance(files, list)
        finally:
            # 清理测试文件
            if test_file.exists():
                test_file.unlink()


if __name__ == '__main__':
    unittest.main()