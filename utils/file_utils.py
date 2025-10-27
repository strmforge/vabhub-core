#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件操作工具模块
提供跨平台的文件操作功能
"""

import os
import time
import shutil
from pathlib import Path
from functools import wraps
from typing import List, Dict, Any

from core.config import settings


def retry_on_error(max_retries=3, delay=1):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (OSError, IOError) as e:
                    if attempt < max_retries - 1:
                        print(f"操作失败，{delay}秒后重试... ({attempt + 1}/{max_retries})")
                        time.sleep(delay)
                    else:
                        raise
            return None
        return wrapper
    return decorator


def sanitize_filename(filename):
    """清理文件名，确保跨文件系统兼容"""
    if not filename:
        return "unnamed"
    
    # 移除或替换非法字符
    illegal_chars = '<>:"/\\|?*'
    for char in illegal_chars:
        filename = filename.replace(char, '_')
    
    # 限制文件名长度
    name, ext = os.path.splitext(filename)
    max_name_len = 255 - len(ext.encode('utf-8')) - 10
    
    if len(name.encode('utf-8')) > max_name_len:
        name = name[:max_name_len]
    
    return name + ext


@retry_on_error(max_retries=settings.network_retry_count, delay=settings.network_retry_delay)
def safe_rename(old_path, new_path):
    """安全的文件重命名，支持重试和验证"""
    old_path = str(old_path)
    new_path = str(new_path)
    
    # 确保目标目录存在
    os.makedirs(os.path.dirname(new_path), exist_ok=True)
    
    # 如果目标文件已存在，根据策略处理
    if os.path.exists(new_path):
        if settings.conflict_strategy == "skip":
            print(f"跳过已存在文件: {new_path}")
            return old_path  # 不重命名
        elif settings.conflict_strategy == "replace":
            os.remove(new_path)
        elif settings.conflict_strategy == "keep_both":
            base, ext = os.path.splitext(new_path)
            counter = 1
            while os.path.exists(new_path):
                new_path = f"{base}_{counter}{ext}"
                counter += 1
        else:  # auto
            # 自动处理：比较文件大小，保留较大的文件
            current_size = os.path.getsize(old_path)
            existing_size = os.path.getsize(new_path)
            
            if current_size > existing_size:
                os.remove(new_path)
            else:
                print(f"跳过已存在文件（当前文件较小）: {new_path}")
                return old_path
    
    # 执行重命名
    shutil.move(old_path, new_path)
    
    # 验证重命名是否成功
    if not os.path.exists(new_path):
        raise OSError(f"重命名验证失败: {old_path} -> {new_path}")
    
    print(f"文件重命名成功: {old_path} -> {new_path}")
    return new_path


@retry_on_error(max_retries=settings.network_retry_count, delay=settings.network_retry_delay)
def safe_delete(file_path):
    """安全的文件删除"""
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"文件删除成功: {file_path}")
    else:
        print(f"文件不存在，无需删除: {file_path}")


def get_file_info(file_path):
    """获取文件详细信息"""
    stat = os.stat(file_path)
    
    return {
        "path": file_path,
        "name": os.path.basename(file_path),
        "size": stat.st_size,
        "modified_time": stat.st_mtime,
        "created_time": stat.st_ctime,
        "extension": os.path.splitext(file_path)[1].lower()
    }


def scan_directory(directory, recursive=True, file_types=None):
    """扫描目录中的文件"""
    if file_types is None:
        file_types = ['.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm']
    
    files = []
    
    try:
        if recursive:
            # 递归扫描
            for root, dirs, filenames in os.walk(directory):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    
                    # 跳过隐藏文件和系统文件
                    if filename.startswith('.') or filename.startswith('~'):
                        continue
                    
                    # 检查文件扩展名
                    ext = Path(filename).suffix.lower()
                    if ext in file_types:
                        files.append(get_file_info(file_path))
        else:
            # 非递归扫描
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                
                if os.path.isfile(file_path):
                    # 跳过隐藏文件和系统文件
                    if filename.startswith('.') or filename.startswith('~'):
                        continue
                    
                    # 检查文件扩展名
                    ext = Path(filename).suffix.lower()
                    if ext in file_types:
                        files.append(get_file_info(file_path))
    
    except Exception as e:
        print(f"扫描目录失败: {directory}, 错误: {e}")
    
    return files


def copy_file_with_progress(src, dst, callback=None):
    """带进度回调的文件复制"""
    total_size = os.path.getsize(src)
    copied = 0
    
    with open(src, 'rb') as fsrc:
        with open(dst, 'wb') as fdst:
            while True:
                buf = fsrc.read(8192)
                if not buf:
                    break
                fdst.write(buf)
                copied += len(buf)
                
                if callback:
                    progress = (copied / total_size) * 100
                    callback(progress, copied, total_size)
    
    return dst


def get_directory_size(directory):
    """获取目录总大小"""
    total_size = 0
    
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            
            if os.path.isfile(file_path):
                total_size += os.path.getsize(file_path)
    
    return total_size


def create_backup(file_path, backup_suffix=".backup"):
    """创建文件备份"""
    backup_path = file_path + backup_suffix
    
    if os.path.exists(file_path):
        shutil.copy2(file_path, backup_path)
        print(f"备份创建成功: {backup_path}")
        return backup_path
    
    return None


def restore_backup(backup_path, original_suffix=".backup"):
    """从备份恢复文件"""
    if backup_path.endswith(original_suffix):
        original_path = backup_path[:-len(original_suffix)]
        
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, original_path)
            print(f"文件恢复成功: {original_path}")
            return original_path
    
    return None