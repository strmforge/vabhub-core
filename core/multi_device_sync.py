#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多设备同步管理器
支持跨设备数据同步和统一用户画像
"""

import json
import asyncio
import hashlib
import time
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
from pathlib import Path
import aiofiles

from core.config import settings


class MultiDeviceSyncManager:
    """多设备同步管理器"""
    
    def __init__(self):
        self.sync_config_file = "multi_device_sync.json"
        self.user_profiles_file = "user_profiles.json"
        self.sync_history_file = "sync_history.json"
        self.device_registry_file = "device_registry.json"
        
        self.sync_config = self._load_sync_config()
        self.user_profiles = self._load_user_profiles()
        self.sync_history = self._load_sync_history()
        self.device_registry = self._load_device_registry()
        
        self.sync_queue = asyncio.Queue()
        self.sync_in_progress = False
        self.last_sync_time = None
    
    def _load_sync_config(self) -> Dict[str, Any]:
        """加载同步配置"""
        try:
            import aiofiles
            async def load_file():
                async with aiofiles.open(self.sync_config_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    return json.loads(content)
            
            # 在同步环境中运行异步函数
            import asyncio
            return asyncio.run(load_file())
        except:
            # 默认配置
            return {
                "sync_enabled": True,
                "sync_interval": 300,  # 5分钟
                "max_sync_retries": 3,
                "sync_data_types": ["user_preferences", "watch_history", "favorites", "playlists"],
                "encryption_enabled": True,
                "compression_enabled": True,
                "conflict_resolution": "newer_wins"  # newer_wins, manual, custom
            }
    
    def _load_user_profiles(self) -> Dict[str, Any]:
        """加载用户画像数据"""
        try:
            import aiofiles
            async def load_file():
                async with aiofiles.open(self.user_profiles_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    return json.loads(content)
            
            import asyncio
            return asyncio.run(load_file())
        except:
            return {}
    
    def _load_sync_history(self) -> Dict[str, Any]:
        """加载同步历史记录"""
        try:
            import aiofiles
            async def load_file():
                async with aiofiles.open(self.sync_history_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    return json.loads(content)
            
            import asyncio
            return asyncio.run(load_file())
        except:
            return {}
    
    def _load_device_registry(self) -> Dict[str, Any]:
        """加载设备注册表"""
        try:
            import aiofiles
            async def load_file():
                async with aiofiles.open(self.device_registry_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    return json.loads(content)
            
            import asyncio
            return asyncio.run(load_file())
        except:
            return {}
    
    async def _save_sync_config(self):
        """保存同步配置"""
        try:
            async with aiofiles.open(self.sync_config_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(self.sync_config, indent=2, ensure_ascii=False))
        except:
            pass
    
    async def _save_user_profiles(self):
        """保存用户画像数据"""
        try:
            async with aiofiles.open(self.user_profiles_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(self.user_profiles, indent=2, ensure_ascii=False))
        except:
            pass
    
    async def _save_sync_history(self):
        """保存同步历史记录"""
        try:
            async with aiofiles.open(self.sync_history_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(self.sync_history, indent=2, ensure_ascii=False))
        except:
            pass
    
    async def _save_device_registry(self):
        """保存设备注册表"""
        try:
            async with aiofiles.open(self.device_registry_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(self.device_registry, indent=2, ensure_ascii=False))
        except:
            pass
    
    async def register_device(self, device_info: Dict[str, Any]) -> Dict[str, Any]:
        """注册新设备"""
        try:
            device_id = self._generate_device_id(device_info)
            
            # 检查设备是否已注册
            if device_id in self.device_registry:
                return {
                    "success": False,
                    "message": "设备已注册",
                    "device_id": device_id
                }
            
            # 注册新设备
            self.device_registry[device_id] = {
                "device_info": device_info,
                "registration_time": datetime.now().isoformat(),
                "last_sync_time": None,
                "sync_status": "active",
                "sync_count": 0
            }
            
            await self._save_device_registry()
            
            return {
                "success": True,
                "message": "设备注册成功",
                "device_id": device_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"设备注册失败: {str(e)}"
            }
    
    def _generate_device_id(self, device_info: Dict[str, Any]) -> str:
        """生成设备唯一ID"""
        device_string = f"{device_info.get('device_name', '')}-{device_info.get('device_type', '')}-{device_info.get('os_version', '')}"
        return hashlib.md5(device_string.encode()).hexdigest()
    
    async def sync_data(self, device_id: str, sync_data: Dict[str, Any]) -> Dict[str, Any]:
        """同步设备数据"""
        try:
            # 验证设备
            if device_id not in self.device_registry:
                return {
                    "success": False,
                    "message": "设备未注册"
                }
            
            # 处理同步数据
            sync_result = await self._process_sync_data(device_id, sync_data)
            
            # 更新设备同步状态
            self.device_registry[device_id]["last_sync_time"] = datetime.now().isoformat()
            self.device_registry[device_id]["sync_count"] += 1
            
            await self._save_device_registry()
            
            # 记录同步历史
            sync_id = f"{device_id}_{int(time.time())}"
            self.sync_history[sync_id] = {
                "device_id": device_id,
                "sync_time": datetime.now().isoformat(),
                "sync_result": sync_result,
                "data_types": list(sync_data.keys())
            }
            
            await self._save_sync_history()
            
            return {
                "success": True,
                "message": "数据同步成功",
                "sync_result": sync_result
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"数据同步失败: {str(e)}"
            }
    
    async def _process_sync_data(self, device_id: str, sync_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理同步数据"""
        result = {
            "processed_items": 0,
            "conflicts_resolved": 0,
            "errors": []
        }
        
        for data_type, data in sync_data.items():
            try:
                if data_type == "user_preferences":
                    await self._sync_user_preferences(device_id, data)
                elif data_type == "watch_history":
                    await self._sync_watch_history(device_id, data)
                elif data_type == "favorites":
                    await self._sync_favorites(device_id, data)
                elif data_type == "playlists":
                    await self._sync_playlists(device_id, data)
                
                result["processed_items"] += 1
                
            except Exception as e:
                result["errors"].append({
                    "data_type": data_type,
                    "error": str(e)
                })
        
        return result
    
    async def _sync_user_preferences(self, device_id: str, preferences: Dict[str, Any]):
        """同步用户偏好设置"""
        # 创建或更新用户画像
        if "user_id" not in self.user_profiles:
            self.user_profiles["user_id"] = {}
        
        user_profile = self.user_profiles["user_id"]
        
        # 合并偏好设置
        if "preferences" not in user_profile:
            user_profile["preferences"] = {}
        
        # 冲突解决策略
        if self.sync_config["conflict_resolution"] == "newer_wins":
            user_profile["preferences"].update(preferences)
        
        # 更新设备特定的偏好
        if "device_preferences" not in user_profile:
            user_profile["device_preferences"] = {}
        
        user_profile["device_preferences"][device_id] = {
            "last_updated": datetime.now().isoformat(),
            "preferences": preferences
        }
        
        await self._save_user_profiles()
    
    async def _sync_watch_history(self, device_id: str, watch_history: List[Dict[str, Any]]):
        """同步观看历史"""
        if "watch_history" not in self.user_profiles["user_id"]:
            self.user_profiles["user_id"]["watch_history"] = []
        
        existing_history = self.user_profiles["user_id"]["watch_history"]
        
        # 合并观看历史，避免重复
        for item in watch_history:
            # 检查是否已存在
            existing_item = next((
                existing for existing in existing_history
                if existing.get("media_id") == item.get("media_id") and
                   existing.get("device_id") == device_id
            ), None)
            
            if existing_item:
                # 更新现有记录
                if item.get("last_watched") > existing_item.get("last_watched"):
                    existing_item.update(item)
            else:
                # 添加新记录
                item["device_id"] = device_id
                item["sync_time"] = datetime.now().isoformat()
                existing_history.append(item)
        
        # 按时间排序
        existing_history.sort(key=lambda x: x.get("last_watched", ""), reverse=True)
        
        await self._save_user_profiles()
    
    async def _sync_favorites(self, device_id: str, favorites: List[Dict[str, Any]]):
        """同步收藏列表"""
        if "favorites" not in self.user_profiles["user_id"]:
            self.user_profiles["user_id"]["favorites"] = {}
        
        user_favorites = self.user_profiles["user_id"]["favorites"]
        
        for favorite in favorites:
            media_id = favorite.get("media_id")
            if media_id:
                if media_id not in user_favorites:
                    user_favorites[media_id] = favorite
                else:
                    # 合并标签和设备信息
                    existing = user_favorites[media_id]
                    
                    # 合并标签
                    if "tags" in favorite and "tags" in existing:
                        existing["tags"] = list(set(existing["tags"] + favorite["tags"]))
                    
                    # 添加设备信息
                    if "devices" not in existing:
                        existing["devices"] = []
                    
                    if device_id not in existing["devices"]:
                        existing["devices"].append(device_id)
        
        await self._save_user_profiles()
    
    async def _sync_playlists(self, device_id: str, playlists: List[Dict[str, Any]]):
        """同步播放列表"""
        if "playlists" not in self.user_profiles["user_id"]:
            self.user_profiles["user_id"]["playlists"] = {}
        
        user_playlists = self.user_profiles["user_id"]["playlists"]
        
        for playlist in playlists:
            playlist_id = playlist.get("playlist_id")
            if playlist_id:
                if playlist_id not in user_playlists:
                    user_playlists[playlist_id] = playlist
                else:
                    # 合并播放列表内容
                    existing = user_playlists[playlist_id]
                    
                    # 合并媒体项
                    if "items" in playlist and "items" in existing:
                        # 去重合并
                        existing_items = {item["media_id"]: item for item in existing["items"]}
                        new_items = {item["media_id"]: item for item in playlist["items"]}
                        
                        # 更新或添加新项
                        existing_items.update(new_items)
                        existing["items"] = list(existing_items.values())
                    
                    # 更新设备信息
                    if "shared_devices" not in existing:
                        existing["shared_devices"] = []
                    
                    if device_id not in existing["shared_devices"]:
                        existing["shared_devices"].append(device_id)
        
        await self._save_user_profiles()
    
    async def get_unified_user_profile(self, user_id: str = "user_id") -> Dict[str, Any]:
        """获取统一用户画像"""
        try:
            if user_id not in self.user_profiles:
                return {
                    "success": False,
                    "message": "用户画像不存在"
                }
            
            user_profile = self.user_profiles[user_id]
            
            # 计算用户画像统计信息
            profile_stats = self._calculate_profile_stats(user_profile)
            
            # 生成个性化推荐
            recommendations = await self._generate_recommendations(user_profile)
            
            unified_profile = {
                "user_id": user_id,
                "profile_data": user_profile,
                "statistics": profile_stats,
                "recommendations": recommendations,
                "last_updated": datetime.now().isoformat()
            }
            
            return {
                "success": True,
                "data": unified_profile,
                "message": "统一用户画像获取成功"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"获取用户画像失败: {str(e)}"
            }
    
    def _calculate_profile_stats(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """计算用户画像统计信息"""
        stats = {
            "total_watch_time": 0,
            "favorite_categories": {},
            "device_count": 0,
            "playlist_count": 0,
            "recent_activity": {}
        }
        
        # 计算总观看时间
        if "watch_history" in user_profile:
            for item in user_profile["watch_history"]:
                stats["total_watch_time"] += item.get("watch_duration", 0)
        
        # 统计最喜欢的分类
        if "favorites" in user_profile:
            for favorite in user_profile["favorites"].values():
                category = favorite.get("category", "unknown")
                stats["favorite_categories"][category] = stats["favorite_categories"].get(category, 0) + 1
        
        # 统计设备数量
        if "device_preferences" in user_profile:
            stats["device_count"] = len(user_profile["device_preferences"])
        
        # 统计播放列表数量
        if "playlists" in user_profile:
            stats["playlist_count"] = len(user_profile["playlists"])
        
        return stats
    
    async def _generate_recommendations(self, user_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成个性化推荐"""
        # 基于用户画像生成推荐
        recommendations = []
        
        # 基于观看历史推荐
        if "watch_history" in user_profile:
            recent_watches = user_profile["watch_history"][:10]  # 最近10个
            for watch in recent_watches:
                recommendations.append({
                    "type": "similar_to_watched",
                    "media_id": watch.get("media_id"),
                    "title": f"类似 {watch.get('title', '未知')}",
                    "confidence": 0.8
                })
        
        # 基于收藏推荐
        if "favorites" in user_profile:
            favorites = list(user_profile["favorites"].values())[:5]  # 前5个收藏
            for favorite in favorites:
                recommendations.append({
                    "type": "based_on_favorites", 
                    "media_id": favorite.get("media_id"),
                    "title": f"您可能也喜欢 {favorite.get('title', '未知')}",
                    "confidence": 0.9
                })
        
        # 基于设备使用模式推荐
        if "device_preferences" in user_profile:
            recommendations.append({
                "type": "device_optimized",
                "title": "为您设备优化的内容",
                "confidence": 0.7
            })
        
        return recommendations[:10]  # 返回前10个推荐
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        try:
            status = {
                "sync_enabled": self.sync_config["sync_enabled"],
                "registered_devices": len(self.device_registry),
                "total_syncs": len(self.sync_history),
                "last_sync_time": self.last_sync_time,
                "sync_in_progress": self.sync_in_progress,
                "device_status": {}
            }
            
            # 设备状态
            for device_id, device_info in self.device_registry.items():
                status["device_status"][device_id] = {
                    "device_name": device_info["device_info"].get("device_name", "未知"),
                    "last_sync": device_info.get("last_sync_time"),
                    "sync_count": device_info.get("sync_count", 0),
                    "status": device_info.get("sync_status", "unknown")
                }
            
            return {
                "success": True,
                "data": status,
                "message": "同步状态获取成功"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"获取同步状态失败: {str(e)}"
            }
    
    async def start_auto_sync(self):
        """启动自动同步"""
        if not self.sync_config["sync_enabled"]:
            return
        
        # 启动后台同步任务
        asyncio.create_task(self._auto_sync_worker())
    
    async def _auto_sync_worker(self):
        """自动同步工作器"""
        while True:
            try:
                await asyncio.sleep(self.sync_config["sync_interval"])
                
                if not self.sync_in_progress:
                    await self._perform_auto_sync()
                    
            except Exception as e:
                print(f"自动同步错误: {e}")
    
    async def _perform_auto_sync(self):
        """执行自动同步"""
        self.sync_in_progress = True
        
        try:
            # 这里可以实现与云服务的自动同步
            # 目前模拟自动同步
            sync_result = {
                "auto_sync_time": datetime.now().isoformat(),
                "devices_synced": 0,
                "data_synced": 0
            }
            
            self.last_sync_time = datetime.now().isoformat()
            
            print(f"自动同步完成: {sync_result}")
            
        finally:
            self.sync_in_progress = False


# 多设备同步管理器实例
multi_device_sync_manager = MultiDeviceSyncManager()