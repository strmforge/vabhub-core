#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VabHub 库管理器
支持多库分离管理，模仿 MoviePilot 的库模式
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, asdict


class LibraryType(Enum):
    """库类型枚举"""
    MOVIE = "movie"
    TV = "tv"
    MUSIC = "music"
    ANIME = "anime"
    DOCUMENTARY = "documentary"
    OTHER = "other"


@dataclass
class LibraryConfig:
    """库配置类"""
    name: str
    type: LibraryType
    path: str
    enabled: bool = True
    auto_scan: bool = True
    scan_interval: int = 3600  # 扫描间隔（秒）
    rename_rules: Optional[Dict] = None
    metadata_sources: List[str] = None
    file_extensions: List[str] = None
    
    def __post_init__(self):
        if self.rename_rules is None:
            self.rename_rules = {}
        if self.metadata_sources is None:
            self.metadata_sources = ["tmdb", "douban"]
        if self.file_extensions is None:
            self.file_extensions = self._get_default_extensions()
    
    def _get_default_extensions(self) -> List[str]:
        """获取默认文件扩展名"""
        if self.type == LibraryType.MOVIE:
            return [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"]
        elif self.type == LibraryType.TV:
            return [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"]
        elif self.type == LibraryType.MUSIC:
            return [".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a"]
        elif self.type == LibraryType.ANIME:
            return [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"]
        else:
            return [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"]


class LibraryManager:
    """库管理器"""
    
    def __init__(self, config_file: str = "config/libraries.yaml"):
        self.config_file = config_file
        self.libraries: Dict[str, LibraryConfig] = {}
        self._load_config()
    
    def _load_config(self):
        """加载库配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f) or {}
                
                self.libraries = {}
                for lib_id, lib_data in config_data.get("libraries", {}).items():
                    try:
                        lib_config = LibraryConfig(
                            name=lib_data["name"],
                            type=LibraryType(lib_data["type"]),
                            path=lib_data["path"],
                            enabled=lib_data.get("enabled", True),
                            auto_scan=lib_data.get("auto_scan", True),
                            scan_interval=lib_data.get("scan_interval", 3600),
                            rename_rules=lib_data.get("rename_rules"),
                            metadata_sources=lib_data.get("metadata_sources"),
                            file_extensions=lib_data.get("file_extensions")
                        )
                        self.libraries[lib_id] = lib_config
                    except Exception as e:
                        print(f"⚠️ 加载库配置失败 {lib_id}: {e}")
                        
            except Exception as e:
                print(f"❌ 加载库配置文件失败: {e}")
                self._create_default_config()
        else:
            self._create_default_config()
    
    def _create_default_config(self):
        """创建默认配置"""
        print("📝 创建默认库配置...")
        
        # 创建默认库配置
        default_libraries = {
            "movie": LibraryConfig(
                name="电影库",
                type=LibraryType.MOVIE,
                path="/data/movies",
                rename_rules={
                    "template": "{title} ({year})",
                    "naming_convention": "Plex"
                }
            ),
            "tv": LibraryConfig(
                name="电视剧库",
                type=LibraryType.TV,
                path="/data/tv",
                rename_rules={
                    "template": "{title}/Season {season:02d}/{title} - S{season:02d}E{episode:02d}",
                    "naming_convention": "Plex"
                }
            ),
            "music": LibraryConfig(
                name="音乐库",
                type=LibraryType.MUSIC,
                path="/data/music",
                rename_rules={
                    "template": "{artist}/{album}/{track:02d} - {title}",
                    "naming_convention": "MusicBrainz"
                }
            )
        }
        
        self.libraries = default_libraries
        self.save_config()
    
    def save_config(self):
        """保存配置到文件"""
        try:
            # 确保配置目录存在
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            config_data = {
                "libraries": {
                    lib_id: asdict(lib_config) 
                    for lib_id, lib_config in self.libraries.items()
                }
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True, indent=2)
            
            print(f"✅ 库配置已保存: {self.config_file}")
            
        except Exception as e:
            print(f"❌ 保存库配置失败: {e}")
    
    def get_library(self, library_id: str) -> Optional[LibraryConfig]:
        """获取指定库配置"""
        return self.libraries.get(library_id)
    
    def get_enabled_libraries(self) -> Dict[str, LibraryConfig]:
        """获取所有启用的库"""
        return {lib_id: lib for lib_id, lib in self.libraries.items() if lib.enabled}
    
    def get_libraries_by_type(self, library_type: LibraryType) -> Dict[str, LibraryConfig]:
        """按类型获取库"""
        return {lib_id: lib for lib_id, lib in self.libraries.items() if lib.type == library_type}
    
    def add_library(self, library_id: str, library_config: LibraryConfig) -> bool:
        """添加新库"""
        if library_id in self.libraries:
            print(f"⚠️ 库ID已存在: {library_id}")
            return False
        
        self.libraries[library_id] = library_config
        self.save_config()
        print(f"✅ 添加库成功: {library_id}")
        return True
    
    def update_library(self, library_id: str, **kwargs) -> bool:
        """更新库配置"""
        if library_id not in self.libraries:
            print(f"⚠️ 库不存在: {library_id}")
            return False
        
        library = self.libraries[library_id]
        for key, value in kwargs.items():
            if hasattr(library, key):
                setattr(library, key, value)
        
        self.save_config()
        print(f"✅ 更新库成功: {library_id}")
        return True
    
    def remove_library(self, library_id: str) -> bool:
        """删除库"""
        if library_id not in self.libraries:
            print(f"⚠️ 库不存在: {library_id}")
            return False
        
        del self.libraries[library_id]
        self.save_config()
        print(f"✅ 删除库成功: {library_id}")
        return True
    
    def enable_library(self, library_id: str) -> bool:
        """启用库"""
        return self.update_library(library_id, enabled=True)
    
    def disable_library(self, library_id: str) -> bool:
        """禁用库"""
        return self.update_library(library_id, enabled=False)
    
    def validate_library_paths(self) -> Dict[str, bool]:
        """验证库路径"""
        results = {}
        for lib_id, lib_config in self.libraries.items():
            if lib_config.enabled:
                path_exists = os.path.exists(lib_config.path)
                results[lib_id] = path_exists
                status = "✅" if path_exists else "❌"
                print(f"{status} {lib_config.name}: {lib_config.path}")
        return results
    
    def get_library_stats(self) -> Dict[str, Any]:
        """获取库统计信息"""
        stats = {
            "total_libraries": len(self.libraries),
            "enabled_libraries": len(self.get_enabled_libraries()),
            "by_type": {},
            "path_validation": self.validate_library_paths()
        }
        
        # 按类型统计
        for lib_type in LibraryType:
            type_libs = self.get_libraries_by_type(lib_type)
            stats["by_type"][lib_type.value] = {
                "count": len(type_libs),
                "enabled": len([lib for lib in type_libs.values() if lib.enabled])
            }
        
        return stats
    
    def scan_library(self, library_id: str) -> Dict[str, Any]:
        """扫描指定库"""
        library = self.get_library(library_id)
        if not library:
            return {"error": f"库不存在: {library_id}"}
        
        if not library.enabled:
            return {"error": f"库已禁用: {library_id}"}
        
        if not os.path.exists(library.path):
            return {"error": f"库路径不存在: {library.path}"}
        
        print(f"🔍 扫描库: {library.name} ({library.path})")
        
        try:
            # 扫描文件
            media_files = []
            total_size = 0
            
            for root, dirs, files in os.walk(library.path):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in library.file_extensions):
                        file_path = os.path.join(root, file)
                        file_size = os.path.getsize(file_path)
                        
                        media_files.append({
                            "path": file_path,
                            "size": file_size,
                            "relative_path": os.path.relpath(file_path, library.path)
                        })
                        total_size += file_size
            
            result = {
                "library_id": library_id,
                "library_name": library.name,
                "file_count": len(media_files),
                "total_size": total_size,
                "media_files": media_files[:100],  # 限制返回数量
                "status": "success"
            }
            
            print(f"✅ 扫描完成: 找到 {len(media_files)} 个媒体文件")
            return result
            
        except Exception as e:
            error_msg = f"扫描失败: {e}"
            print(f"❌ {error_msg}")
            return {"error": error_msg}
    
    def scan_all_libraries(self) -> Dict[str, Any]:
        """扫描所有启用的库"""
        enabled_libs = self.get_enabled_libraries()
        results = {}
        
        print(f"🔍 开始扫描 {len(enabled_libs)} 个启用的库...")
        
        for lib_id, library in enabled_libs.items():
            results[lib_id] = self.scan_library(lib_id)
        
        # 统计信息
        total_files = sum(
            result.get("file_count", 0) 
            for result in results.values() 
            if "error" not in result
        )
        
        total_size = sum(
            result.get("total_size", 0) 
            for result in results.values() 
            if "error" not in result
        )
        
        return {
            "total_libraries_scanned": len(enabled_libs),
            "total_files_found": total_files,
            "total_size": total_size,
            "results": results,
            "status": "completed"
        }


def create_library_manager() -> LibraryManager:
    """创建库管理器实例"""
    return LibraryManager()


# 测试代码
if __name__ == "__main__":
    # 创建库管理器
    manager = create_library_manager()
    
    # 显示库信息
    print("📚 库管理器测试")
    print("=" * 50)
    
    # 显示所有库
    for lib_id, lib_config in manager.libraries.items():
        status = "✅" if lib_config.enabled else "❌"
        print(f"{status} {lib_config.name} ({lib_id}): {lib_config.path}")
    
    # 显示统计信息
    stats = manager.get_library_stats()
    print(f"\n📊 统计信息:")
    print(f"  总库数: {stats['total_libraries']}")
    print(f"  启用库数: {stats['enabled_libraries']}")
    
    # 验证路径
    print(f"\n🔍 路径验证:")
    manager.validate_library_paths()
    
    # 扫描测试（可选）
    if input("\n是否进行扫描测试? (y/n): ").lower() == "y":
        scan_results = manager.scan_all_libraries()
        print(f"\n📋 扫描结果:")
        print(f"  扫描库数: {scan_results['total_libraries_scanned']}")
        print(f"  找到文件: {scan_results['total_files_found']}")
        print(f"  总大小: {scan_results['total_size'] / (1024**3):.2f} GB")