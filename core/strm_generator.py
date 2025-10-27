"""
STRM文件生成器
用于生成指向云存储文件的STRM文件，实现302跳转功能
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
from enum import Enum


class STRMType(Enum):
    """STRM文件类型"""
    DIRECT = "direct"  # 直接跳转
    PROXY = "proxy"    # 代理跳转
    CUSTOM = "custom"  # 自定义跳转


class STRMGenerator:
    """STRM文件生成器"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.logger = logging.getLogger(__name__)
    
    def generate_strm_content(self, 
                            file_url: str, 
                            strm_type: STRMType = STRMType.DIRECT,
                            metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        生成STRM文件内容
        
        Args:
            file_url: 实际文件URL
            strm_type: STRM类型
            metadata: 文件元数据
            
        Returns:
            STRM文件内容
        """
        if strm_type == STRMType.DIRECT:
            # 直接跳转格式
            return f"#STRM Direct Redirect\n{file_url}"
        
        elif strm_type == STRMType.PROXY:
            # 代理跳转格式（通过本地服务代理）
            proxy_url = f"{self.base_url}/api/strm/proxy?url={file_url}"
            return f"#STRM Proxy Redirect\n{proxy_url}"
        
        elif strm_type == STRMType.CUSTOM:
            # 自定义格式，包含元数据
            content = f"#STRM Custom Redirect\n{file_url}\n"
            if metadata:
                content += f"#METADATA\n{json.dumps(metadata, ensure_ascii=False, indent=2)}"
            return content
        
        else:
            raise ValueError(f"不支持的STRM类型: {strm_type}")
    
    def create_strm_file(self, 
                        output_path: str, 
                        file_url: str, 
                        strm_type: STRMType = STRMType.DIRECT,
                        metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        创建STRM文件
        
        Args:
            output_path: 输出文件路径
            file_url: 实际文件URL
            strm_type: STRM类型
            metadata: 文件元数据
            
        Returns:
            是否成功创建
        """
        try:
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            # 生成STRM内容
            content = self.generate_strm_content(file_url, strm_type, metadata)
            
            # 写入文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.info(f"STRM文件创建成功: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"创建STRM文件失败: {e}")
            return False
    
    def generate_cloud_strm(self,
                           storage_type: str,
                           file_id: str,
                           file_name: str,
                           output_dir: str,
                           metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        为云存储文件生成STRM文件
        
        Args:
            storage_type: 存储类型 (u115, alipan, etc.)
            file_id: 文件ID
            file_name: 文件名
            output_dir: 输出目录
            metadata: 文件元数据
            
        Returns:
            生成的STRM文件路径
        """
        try:
            # 生成文件URL（通过本地服务代理）
            file_url = f"{self.base_url}/api/strm/stream/{storage_type}/{file_id}"
            
            # 生成STRM文件名（保持原文件扩展名）
            file_ext = Path(file_name).suffix
            strm_filename = Path(file_name).stem + ".strm"
            output_path = os.path.join(output_dir, strm_filename)
            
            # 创建STRM文件
            if self.create_strm_file(output_path, file_url, STRMType.PROXY, metadata):
                return output_path
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"生成云存储STRM文件失败: {e}")
            return None
    
    def batch_generate_strm(self,
                           file_list: List[Dict[str, Any]],
                           output_base_dir: str,
                           organize_by_type: bool = True) -> Dict[str, Any]:
        """
        批量生成STRM文件
        
        Args:
            file_list: 文件列表，每个文件包含 storage_type, file_id, file_name, metadata
            output_base_dir: 输出基础目录
            organize_by_type: 是否按类型组织目录
            
        Returns:
            生成结果统计
        """
        results = {
            "total": len(file_list),
            "success": 0,
            "failed": 0,
            "generated_files": []
        }
        
        for file_info in file_list:
            try:
                storage_type = file_info.get('storage_type')
                file_id = file_info.get('file_id')
                file_name = file_info.get('file_name')
                metadata = file_info.get('metadata', {})
                
                # 确定输出目录
                if organize_by_type:
                    # 按媒体类型组织目录
                    media_type = metadata.get('media_type', 'other')
                    if media_type == 'movie':
                        output_dir = os.path.join(output_base_dir, '电影')
                    elif media_type == 'tv':
                        output_dir = os.path.join(output_base_dir, '电视剧')
                    elif media_type == 'anime':
                        output_dir = os.path.join(output_base_dir, '动漫')
                    else:
                        output_dir = os.path.join(output_base_dir, '其他')
                else:
                    output_dir = output_base_dir
                
                # 生成STRM文件
                strm_path = self.generate_cloud_strm(
                    storage_type, file_id, file_name, output_dir, metadata
                )
                
                if strm_path:
                    results['success'] += 1
                    results['generated_files'].append({
                        'original_file': file_name,
                        'strm_path': strm_path,
                        'storage_type': storage_type
                    })
                else:
                    results['failed'] += 1
                    
            except Exception as e:
                self.logger.error(f"批量生成STRM文件失败: {e}")
                results['failed'] += 1
        
        return results
    
    def validate_strm_file(self, strm_path: str) -> Dict[str, Any]:
        """
        验证STRM文件有效性
        
        Args:
            strm_path: STRM文件路径
            
        Returns:
            验证结果
        """
        result = {
            'valid': False,
            'file_exists': False,
            'content_valid': False,
            'url_valid': False,
            'error': None
        }
        
        try:
            # 检查文件是否存在
            if not os.path.exists(strm_path):
                result['error'] = '文件不存在'
                return result
            
            result['file_exists'] = True
            
            # 读取文件内容
            with open(strm_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # 检查内容格式
            lines = content.split('\n')
            if len(lines) < 2:
                result['error'] = '文件格式不正确'
                return result
            
            # 提取URL（最后一行）
            file_url = lines[-1].strip()
            if not file_url:
                result['error'] = 'URL为空'
                return result
            
            result['content_valid'] = True
            result['url'] = file_url
            result['valid'] = True
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def repair_strm_file(self, strm_path: str, new_url: str = None) -> bool:
        """
        修复STRM文件
        
        Args:
            strm_path: STRM文件路径
            new_url: 新的URL（可选）
            
        Returns:
            是否修复成功
        """
        try:
            validation = self.validate_strm_file(strm_path)
            
            if not validation['file_exists']:
                self.logger.error(f"STRM文件不存在: {strm_path}")
                return False
            
            # 如果提供了新URL，直接使用
            if new_url:
                file_url = new_url
            else:
                # 尝试从原文件中提取URL
                with open(strm_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                lines = content.split('\n')
                if len(lines) >= 2:
                    file_url = lines[-1].strip()
                else:
                    self.logger.error(f"无法从STRM文件中提取URL: {strm_path}")
                    return False
            
            # 重新生成STRM文件
            return self.create_strm_file(strm_path, file_url, STRMType.PROXY)
            
        except Exception as e:
            self.logger.error(f"修复STRM文件失败: {e}")
            return False