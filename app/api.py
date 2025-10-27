#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VabHub 统一API接口
参照MoviePilot的API设计理念
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import json
from pathlib import Path
import time

from core.config import get_config, config_manager
from core.services import get_service_manager
from core.base import BatchTask, ProcessingResult
from core.database import db_manager
from core.media_dao import MediaDAO
from core.error_handler import (
    VabHubError, DatabaseError, PluginError, MediaNotFoundError, PluginNotFoundError,
    ValidationError, AuthenticationError, PermissionError, RateLimitError,
    setup_exception_handlers, log_api_request, get_success_response, get_error_response
)

# 获取服务管理器实例
service_manager = get_service_manager()


class APIResponse(BaseModel):
    """统一API响应格式"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
    
    @classmethod
    def success(cls, message: str = "", data: Dict[str, Any] = None):
        return cls(success=True, message=message, data=data)
    
    @classmethod
    def error(cls, message: str = "", error_code: int = 500, details: Dict[str, Any] = None):
        return cls(success=False, message=message, error_code=error_code, details=details)


class FileOrganizeRequest(BaseModel):
    """文件整理请求"""
    source_dir: str
    target_dir: str
    move_files: bool = False


class DuplicateScanRequest(BaseModel):
    """重复扫描请求"""
    directory: str
    method: str = "hash"


class RenameRequest(BaseModel):
    """重命名请求"""
    file_path: str
    strategy: Optional[str] = None


class BatchRenameRequest(BaseModel):
    """批量重命名请求"""
    files: List[str]
    strategy: Optional[str] = None


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    status: str
    progress: float
    message: str
    results: Optional[List[Dict[str, Any]]] = None


class MediaScanRequest(BaseModel):
    """媒体扫描请求"""
    paths: List[str]
    scan_type: str = "full"  # full, quick, metadata
    force_rescan: bool = False

class MediaItem(BaseModel):
    """媒体项目"""
    id: str
    title: str
    type: str  # movie, tv, music
    year: Optional[str] = None
    rating: Optional[float] = None
    poster: Optional[str] = None
    path: str
    size: int
    created_time: str
    metadata: Optional[Dict[str, Any]] = None

class PluginInfo(BaseModel):
    """插件信息"""
    id: str
    name: str
    version: str
    author: str
    description: str
    status: str  # installed, available, disabled
    enabled: bool

class VabHubAPI:
    """VabHub API主类"""
    
    def __init__(self):
        self.app = FastAPI(
            title="VabHub API",
            version="5.0.0",
            description="VabHub 统一API接口"
        )
        self.config = get_config()
        self.tasks = {}  # 任务管理器
        self.websocket_connections = []
        
        self._setup_middleware()
        self._setup_routes()
    
    def _setup_middleware(self):
        """设置中间件"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.api.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 设置异常处理器
        setup_exception_handlers(self.app)
        
        # 添加请求日志中间件
        @self.app.middleware("http")
        async def log_requests(request: Request, call_next):
            start_time = time.time()
            response = await call_next(request)
            duration = time.time() - start_time
            
            # 记录API请求日志
            log_api_request(request, response, duration)
            
            return response
    
    def _setup_routes(self):
        """设置路由"""
        
        @self.app.get("/", response_model=APIResponse)
        async def root():
            """根路径"""
            return APIResponse.success("VabHub API 服务运行正常")
        
        @self.app.get("/health", response_model=APIResponse)
        async def health_check():
            """健康检查"""
            service_status = service_manager.get_service_status()
            return APIResponse.success("服务健康", {
                "services": service_status,
                "version": self.config.version
            })
        
        @self.app.get("/config", response_model=APIResponse)
        async def get_configuration():
            """获取配置"""
            return APIResponse.success("配置获取成功", {
                "config": self.config.dict()
            })
        
        @self.app.post("/config/update", response_model=APIResponse)
        async def update_configuration(updates: Dict[str, Any]):
            """更新配置"""
            try:
                config_manager.update_config(**updates)
                return APIResponse.success("配置更新成功")
            except Exception as e:
                return APIResponse.error(f"配置更新失败: {str(e)}")
        
        @self.app.post("/files/organize", response_model=APIResponse)
        async def organize_files(request: FileOrganizeRequest, background_tasks: BackgroundTasks):
            """文件整理"""
            if not config_manager.get_feature_status("file_organizer"):
                return APIResponse.error("文件整理功能未启用")
            
            task_id = self._create_task("file_organize", {
                "source_dir": request.source_dir,
                "target_dir": request.target_dir,
                "move_files": request.move_files
            })
            
            background_tasks.add_task(self._execute_file_organize, task_id)
            
            return APIResponse.success("文件整理任务已启动", {"task_id": task_id})
        
        @self.app.post("/files/duplicate-scan", response_model=APIResponse)
        async def duplicate_scan(request: DuplicateScanRequest, background_tasks: BackgroundTasks):
            """重复文件扫描"""
            if not config_manager.get_feature_status("duplicate_finder"):
                return APIResponse.error("重复文件检测功能未启用")
            
            task_id = self._create_task("duplicate_scan", {
                "directory": request.directory,
                "method": request.method
            })
            
            background_tasks.add_task(self._execute_duplicate_scan, task_id)
            
            return APIResponse.success("重复文件扫描任务已启动", {"task_id": task_id})
        
        @self.app.post("/files/rename", response_model=APIResponse)
        async def rename_file(request: RenameRequest):
            """重命名文件"""
            if not config_manager.get_feature_status("smart_rename"):
                return APIResponse.error("智能重命名功能未启用")
            
            try:
                result = await service_manager.smart_renamer.rename_file(
                    request.file_path, request.strategy
                )
                
                if result.success:
                    return APIResponse.success(result.message, result.data)
                else:
                    return APIResponse.error(result.message)
                    
            except Exception as e:
                return APIResponse.error(f"重命名失败: {str(e)}")
        
        @self.app.post("/files/batch-rename", response_model=APIResponse)
        async def batch_rename(request: BatchRenameRequest, background_tasks: BackgroundTasks):
            """批量重命名"""
            if not config_manager.get_feature_status("smart_rename"):
                return APIResponse.error("智能重命名功能未启用")
            
            task_id = self._create_task("batch_rename", {
                "files": request.files,
                "strategy": request.strategy
            })
            
            background_tasks.add_task(self._execute_batch_rename, task_id)
            
            return APIResponse.success("批量重命名任务已启动", {"task_id": task_id})
        
        @self.app.get("/tasks/{task_id}", response_model=APIResponse)
        async def get_task_status(task_id: str):
            """获取任务状态"""
            if task_id not in self.tasks:
                return APIResponse.error("任务不存在")
            
            task = self.tasks[task_id]
            return APIResponse.success("任务状态获取成功", {
                "task": task.to_dict()
            })
        
        # 媒体管理相关接口
        @self.app.post("/media/scan", response_model=APIResponse)
        async def scan_media(request: MediaScanRequest, background_tasks: BackgroundTasks):
            """扫描媒体文件"""
            task_id = self._create_task("media_scan", {
                "paths": request.paths,
                "scan_type": request.scan_type,
                "force_rescan": request.force_rescan
            })
            
            background_tasks.add_task(self._execute_media_scan, task_id)
            
            return APIResponse.success("媒体扫描任务已启动", {"task_id": task_id})
        
        @self.app.get("/media", response_model=APIResponse)
        async def get_media_list(
            type: Optional[str] = None,
            search: Optional[str] = None,
            page: int = 1,
            page_size: int = 20
        ):
            """获取媒体列表"""
            try:
                # 初始化数据库连接
                await db_manager.initialize()
                
                # 使用数据库获取媒体列表
                async with db_manager.get_async_session() as session:
                    media_dao = MediaDAO(session)
                    media_items = await media_dao.get_media_items(
                        media_type=type,
                        search=search,
                        page=page,
                        page_size=page_size
                    )
                    total_count = await media_dao.get_media_count(
                        media_type=type,
                        search=search
                    )
                    
                    # 转换为API响应格式
                    media_list = [item.to_dict() for item in media_items]
                    
                    return APIResponse.success("媒体列表获取成功", {
                        "media": media_list,
                        "pagination": {
                            "page": page,
                            "page_size": page_size,
                            "total": total_count,
                            "total_pages": (total_count + page_size - 1) // page_size
                        }
                    })
            except Exception as e:
                return APIResponse.error(f"获取媒体列表失败: {str(e)}")
        
        @self.app.get("/media/{media_id}", response_model=APIResponse)
        async def get_media_detail(media_id: str):
            """获取媒体详情"""
            try:
                # 初始化数据库连接
                await db_manager.initialize()
                
                # 使用数据库获取媒体详情
                async with db_manager.get_async_session() as session:
                    media_dao = MediaDAO(session)
                    media_item = await media_dao.get_media_item(int(media_id))
                    
                    if not media_item:
                        raise MediaNotFoundError(media_id)
                
                return APIResponse.success("媒体详情获取成功", {"media": media_item.to_dict()})
            except VabHubError:
                raise
            except Exception as e:
                raise DatabaseError(f"获取媒体详情失败: {str(e)}")
        
        @self.app.put("/media/{media_id}", response_model=APIResponse)
        async def update_media(media_id: str, updates: Dict[str, Any]):
            """更新媒体信息"""
            try:
                # 初始化数据库连接
                await db_manager.initialize()
                
                # 使用数据库更新媒体信息
                async with db_manager.get_async_session() as session:
                    media_dao = MediaDAO(session)
                    result = await media_dao.update_media_item(int(media_id), updates)
                    
                    if result:
                        return APIResponse.success("媒体信息更新成功")
                    else:
                        return APIResponse.error("媒体信息更新失败")
            except Exception as e:
                return APIResponse.error(f"更新媒体信息失败: {str(e)}")
        
        @self.app.delete("/media/{media_id}", response_model=APIResponse)
        async def delete_media(media_id: str):
            """删除媒体"""
            try:
                # 初始化数据库连接
                await db_manager.initialize()
                
                # 使用数据库删除媒体
                async with db_manager.get_async_session() as session:
                    media_dao = MediaDAO(session)
                    result = await media_dao.delete_media_item(int(media_id))
                    
                    if result:
                        return APIResponse.success("媒体删除成功")
                    else:
                        return APIResponse.error("媒体删除失败")
            except Exception as e:
                return APIResponse.error(f"删除媒体失败: {str(e)}")
        
        # 插件管理相关接口
        @self.app.get("/plugins", response_model=APIResponse)
        async def get_plugins(status: Optional[str] = None):
            """获取插件列表"""
            try:
                # 初始化数据库连接
                await db_manager.initialize()
                
                # 使用数据库获取插件列表
                async with db_manager.get_async_session() as session:
                    media_dao = MediaDAO(session)
                    
                    # 根据状态过滤插件
                    installed_only = status == "installed"
                    plugins = await media_dao.get_all_plugins(installed_only=installed_only)
                    
                    # 转换为API响应格式
                    plugin_list = [plugin.to_dict() for plugin in plugins]
                    
                    return APIResponse.success("插件列表获取成功", {"plugins": plugin_list})
            except Exception as e:
                return APIResponse.error(f"获取插件列表失败: {str(e)}")
        
        @self.app.post("/plugins/{plugin_id}/install", response_model=APIResponse)
        async def install_plugin(plugin_id: str):
            """安装插件"""
            try:
                # 初始化数据库连接
                await db_manager.initialize()
                
                # 使用数据库安装插件
                async with db_manager.get_async_session() as session:
                    media_dao = MediaDAO(session)
                    
                    # 创建或更新插件信息
                    plugin_data = {
                        "id": plugin_id,
                        "name": plugin_id.replace("-", " ").title(),
                        "version": "1.0.0",
                        "author": "VabHub Team",
                        "description": f"{plugin_id} 插件",
                        "installed": True,
                        "enabled": True
                    }
                    
                    plugin = await media_dao.create_or_update_plugin(plugin_data)
                    
                    if plugin:
                        return APIResponse.success("插件安装成功")
                    else:
                        return APIResponse.error("插件安装失败")
            except Exception as e:
                return APIResponse.error(f"安装插件失败: {str(e)}")
        
        @self.app.post("/plugins/{plugin_id}/uninstall", response_model=APIResponse)
        async def uninstall_plugin(plugin_id: str):
            """卸载插件"""
            try:
                # 初始化数据库连接
                await db_manager.initialize()
                
                # 使用数据库卸载插件
                async with db_manager.get_async_session() as session:
                    media_dao = MediaDAO(session)
                    
                    # 更新插件状态为未安装
                    plugin_data = {
                        "id": plugin_id,
                        "installed": False,
                        "enabled": False
                    }
                    
                    plugin = await media_dao.create_or_update_plugin(plugin_data)
                    
                    if plugin:
                        return APIResponse.success("插件卸载成功")
                    else:
                        return APIResponse.error("插件卸载失败")
            except Exception as e:
                return APIResponse.error(f"卸载插件失败: {str(e)}")
        
        @self.app.post("/plugins/{plugin_id}/enable", response_model=APIResponse)
        async def enable_plugin(plugin_id: str):
            """启用插件"""
            try:
                # 初始化数据库连接
                await db_manager.initialize()
                
                # 使用数据库启用插件
                async with db_manager.get_async_session() as session:
                    media_dao = MediaDAO(session)
                    
                    # 检查插件是否存在
                    plugin = await media_dao.get_plugin(plugin_id)
                    if not plugin:
                        return APIResponse.error("插件不存在")
                    
                    # 启用插件
                    result = await media_dao.update_plugin_status(plugin_id, enabled=True)
                    
                    if result:
                        return APIResponse.success("插件启用成功")
                    else:
                        return APIResponse.error("插件启用失败")
            except Exception as e:
                return APIResponse.error(f"启用插件失败: {str(e)}")
        
        @self.app.post("/plugins/{plugin_id}/disable", response_model=APIResponse)
        async def disable_plugin(plugin_id: str):
            """禁用插件"""
            try:
                # 初始化数据库连接
                await db_manager.initialize()
                
                # 使用数据库禁用插件
                async with db_manager.get_async_session() as session:
                    media_dao = MediaDAO(session)
                    
                    # 检查插件是否存在
                    plugin = await media_dao.get_plugin(plugin_id)
                    if not plugin:
                        return APIResponse.error("插件不存在")
                    
                    # 禁用插件
                    result = await media_dao.update_plugin_status(plugin_id, enabled=False)
                    
                    if result:
                        return APIResponse.success("插件禁用成功")
                    else:
                        return APIResponse.error("插件禁用失败")
            except Exception as e:
                return APIResponse.error(f"禁用插件失败: {str(e)}")
        
        # 设置管理相关接口
        @self.app.get("/settings", response_model=APIResponse)
        async def get_settings():
            """获取系统设置"""
            try:
                # 初始化数据库连接
                await db_manager.initialize()
                
                # 使用数据库获取系统设置
                async with db_manager.get_async_session() as session:
                    media_dao = MediaDAO(session)
                    settings_list = await media_dao.get_all_settings()
                    
                    # 转换为字典格式
                    settings_dict = {}
                    for setting in settings_list:
                        settings_dict[setting.key] = setting.value
                    
                    # 如果没有设置，使用默认值
                    default_settings = {
                        "systemName": "VabHub",
                        "language": "zh-CN",
                        "theme": "auto",
                        "autoScan": True,
                        "scanInterval": 6,
                        "apiPort": 8090,
                        "databaseType": "sqlite",
                        "cacheType": "memory"
                    }
                    
                    # 合并默认设置和数据库设置
                    for key, value in default_settings.items():
                        if key not in settings_dict:
                            settings_dict[key] = value
                            # 保存默认设置到数据库
                            await media_dao.set_setting(key, value, f"默认系统设置: {key}")
                    
                    return APIResponse.success("设置获取成功", {"settings": settings_dict})
            except Exception as e:
                return APIResponse.error(f"获取设置失败: {str(e)}")
        
        @self.app.post("/settings", response_model=APIResponse)
        async def update_settings(updates: Dict[str, Any]):
            """更新系统设置"""
            try:
                # 初始化数据库连接
                await db_manager.initialize()
                
                # 使用数据库更新系统设置
                async with db_manager.get_async_session() as session:
                    media_dao = MediaDAO(session)
                    
                    # 更新每个设置项
                    for key, value in updates.items():
                        await media_dao.set_setting(key, value, f"用户设置: {key}")
                    
                    return APIResponse.success("设置更新成功")
            except Exception as e:
                return APIResponse.error(f"更新设置失败: {str(e)}")
        
        @self.app.post("/system/restart", response_model=APIResponse)
        async def restart_system():
            """重启系统"""
            try:
                # TODO: 实现系统重启逻辑
                return APIResponse.success("系统重启命令已发送")
            except Exception as e:
                return APIResponse.error(f"系统重启失败: {str(e)}")
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket端点"""
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            try:
                while True:
                    data = await websocket.receive_text()
                    # 处理客户端消息
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "message": "连接正常"
                    }))
            except Exception:
                self.websocket_connections.remove(websocket)
    
    def _create_task(self, task_type: str, params: Dict[str, Any]) -> str:
        """创建任务"""
        import hashlib
        import time
        
        task_id = hashlib.md5(f"{task_type}{time.time()}".encode()).hexdigest()[:8]
        task = BatchTask(task_id, task_type)
        
        for file_path in params.get('files', []):
            task.add_file(file_path)
        
        self.tasks[task_id] = task
        return task_id
    
    async def _execute_file_organize(self, task_id: str):
        """执行文件整理任务"""
        task = self.tasks[task_id]
        task.status = 'running'
        
        try:
            result = await service_manager.file_organizer.organize_files(
                task.params['source_dir'],
                task.params['target_dir'],
                task.params.get('move_files', False)
            )
            
            task.add_result(result)
            task.status = 'completed'
            task.update_progress(100.0)
            
        except Exception as e:
            task.status = 'failed'
            task.add_result(ProcessingResult(False, str(e)))
    
    async def _execute_duplicate_scan(self, task_id: str):
        """执行重复扫描任务"""
        task = self.tasks[task_id]
        task.status = 'running'
        
        try:
            result = await service_manager.duplicate_finder.find_duplicates(
                task.params['directory'],
                task.params.get('method', 'hash')
            )
            
            task.add_result(result)
            task.status = 'completed'
            task.update_progress(100.0)
            
        except Exception as e:
            task.status = 'failed'
            task.add_result(ProcessingResult(False, str(e)))
    
    async def _execute_batch_rename(self, task_id: str):
        """执行批量重命名任务"""
        task = self.tasks[task_id]
        task.status = 'running'
        
        try:
            total_files = len(task.params['files'])
            processed_files = 0
            
            for file_path in task.params['files']:
                result = await service_manager.smart_renamer.rename_file(
                    file_path, task.params.get('strategy')
                )
                task.add_result(result)
                
                processed_files += 1
                progress = (processed_files / total_files) * 100
                task.update_progress(progress)
            
            task.status = 'completed'
            
        except Exception as e:
            task.status = 'failed'
            task.add_result(ProcessingResult(False, str(e)))
    
    async def _broadcast_message(self, message: Dict[str, Any]):
        """广播消息到所有WebSocket连接"""
        for connection in self.websocket_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                self.websocket_connections.remove(connection)
    
    # 媒体管理辅助方法
    def _get_media_from_database(self, media_type: Optional[str] = None, 
                                search: Optional[str] = None, 
                                page: int = 1, page_size: int = 20) -> List[MediaItem]:
        """从数据库获取媒体列表"""
        # TODO: 实现数据库查询逻辑
        # 这里返回模拟数据
        return [
            MediaItem(
                id="1",
                title="示例电影",
                type="movie",
                year="2023",
                rating=8.5,
                poster="/images/poster.jpg",
                path="/media/movies/example.mkv",
                size=1024000,
                created_time="2023-01-01T00:00:00",
                metadata={"genre": "动作", "director": "张三"}
            )
        ]
    
    def _get_media_count(self, media_type: Optional[str] = None, 
                        search: Optional[str] = None) -> int:
        """获取媒体数量"""
        # TODO: 实现数据库查询逻辑
        return 1
    
    def _get_media_by_id(self, media_id: str) -> Optional[MediaItem]:
        """根据ID获取媒体详情"""
        # TODO: 实现数据库查询逻辑
        if media_id == "1":
            return MediaItem(
                id="1",
                title="示例电影",
                type="movie",
                year="2023",
                rating=8.5,
                poster="/images/poster.jpg",
                path="/media/movies/example.mkv",
                size=1024000,
                created_time="2023-01-01T00:00:00",
                metadata={"genre": "动作", "director": "张三"}
            )
        return None
    
    def _update_media(self, media_id: str, updates: Dict[str, Any]) -> bool:
        """更新媒体信息"""
        # TODO: 实现数据库更新逻辑
        return True
    
    def _delete_media(self, media_id: str) -> bool:
        """删除媒体"""
        # TODO: 实现数据库删除逻辑
        return True
    
    # 插件管理辅助方法
    def _get_plugins(self, status: Optional[str] = None) -> List[PluginInfo]:
        """获取插件列表"""
        # TODO: 实现插件管理器查询逻辑
        return [
            PluginInfo(
                id="example-plugin",
                name="示例插件",
                version="1.0.0",
                author="VabHub Team",
                description="这是一个示例插件",
                status="installed",
                enabled=True
            )
        ]
    
    def _install_plugin(self, plugin_id: str) -> bool:
        """安装插件"""
        # TODO: 实现插件安装逻辑
        return True
    
    def _uninstall_plugin(self, plugin_id: str) -> bool:
        """卸载插件"""
        # TODO: 实现插件卸载逻辑
        return True
    
    def _enable_plugin(self, plugin_id: str) -> bool:
        """启用插件"""
        # TODO: 实现插件启用逻辑
        return True
    
    def _disable_plugin(self, plugin_id: str) -> bool:
        """禁用插件"""
        # TODO: 实现插件禁用逻辑
        return True
    
    # 设置管理辅助方法
    def _get_system_settings(self) -> Dict[str, Any]:
        """获取系统设置"""
        return {
            "systemName": "VabHub",
            "language": "zh-CN",
            "theme": "auto",
            "autoScan": True,
            "scanInterval": 6,
            "apiPort": 8090,
            "databaseType": "sqlite",
            "cacheType": "memory"
        }
    
    def _update_system_settings(self, updates: Dict[str, Any]) -> bool:
        """更新系统设置"""
        # TODO: 实现设置更新逻辑
        return True
    
    # 媒体扫描任务
    async def _execute_media_scan(self, task_id: str):
        """执行媒体扫描任务"""
        task = self.tasks[task_id]
        try:
            task.status = 'running'
            
            # 模拟扫描过程
            paths = task.data.get('paths', [])
            scan_type = task.data.get('scan_type', 'full')
            
            for i, path in enumerate(paths):
                progress = (i / len(paths)) * 100
                task.update_progress(progress)
                task.message = f"正在扫描路径: {path}"
                
                # 模拟扫描延迟
                await asyncio.sleep(1)
            
            task.status = 'completed'
            task.message = "媒体扫描完成"
            
        except Exception as e:
            task.status = 'failed'
            task.message = f"媒体扫描失败: {str(e)}"


# 创建API实例
api = VabHubAPI()
app = api.app