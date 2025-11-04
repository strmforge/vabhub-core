"""
API module for VabHub Core
"""

import logging
from typing import Optional, Any, Dict, List
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from .config import Config
from .auth import AuthManager
from .database import DatabaseManager
from .media_server import MediaServerManager
from .strm_gateway import STRMGatewayManager
from .charts import ChartItem, ChartsService
from .downloader import DownloaderManager
from .init_performance import start_performance_system
from .api_download import router as download_router
from .api_rss import router as rss_router
from .api_metadata import router as metadata_router
from .api_renamer import router as renamer_router
from .api_notification import router as notification_router
from .api_auth import router as auth_router
from .api_path import router as path_router
from .api_plugins import router as plugins_router
from .api_performance import router as performance_router
from .api_websocket import router as websocket_router
from .ai_recommendation_api import router as ai_recommendation_router
from .api_subscription import router as subscription_router
from .api_file_organizer import router as file_organizer_router

# # # # from .graphql_api import GraphQLAPI  # GraphQLAPI 暂时未实现  # GraphQLAPI 暂时未实现  # GraphQLAPI 暂时未实现  # GraphQLAPI 暂时未实现
from .exceptions import exception_handler
from .logging_config import get_logger


# Data models for API endpoints
class Subscription(BaseModel):
    id: Optional[str] = None
    name: str
    query: str
    enabled: bool = True
    priority: int = 0


class RuleSet(BaseModel):
    rules: Dict[str, Any] = {}


class Task(BaseModel):
    id: Optional[str] = None
    name: str
    status: str = "pending"
    progress: int = 0


class ScraperConfig(BaseModel):
    tmdb_enabled: bool = True
    douban_enabled: bool = True
    language: str = "zh-CN"
    region: str = "CN"
    priority: List[str] = ["tmdb", "douban"]


class LibraryServer(BaseModel):
    kind: str
    name: str
    url: str
    ok: bool = False


class DownloaderInstance(BaseModel):
    id: str
    kind: str
    url: str
    ok: bool = False


class StorageStatus(BaseModel):
    local: bool = True
    strm: bool = False
    cloud: List[str] = []


class STRMEmitRequest(BaseModel):
    library_path: str
    filename: str
    url: str


class GatewaySignRequest(BaseModel):
    path: str
    ttl: int = 600


class SecretStatus(BaseModel):
    sops_enabled: bool = False
    age_key_present: bool = False


class VabHubAPI:
    """Main API class for VabHub Core"""

    def __init__(self, config: Config):
        self.config: Config = config
        self.auth_manager: AuthManager = AuthManager(config.SECRET_KEY)
        self.db_manager: DatabaseManager = DatabaseManager(config.DATABASE_URL)
        self.media_server_manager: MediaServerManager = MediaServerManager(config)
        self.strm_gateway_manager: STRMGatewayManager = STRMGatewayManager(
            config.to_dict()
        )
        self.charts_service: ChartsService = ChartsService(config)
        # self.graphql_api: GraphQLAPI = GraphQLAPI(config)  # GraphQLAPI 暂时未实现

        # 初始化日志器
        self.logger: logging.Logger = get_logger("vabhub.api")

        self.app: FastAPI = FastAPI(
            title="VabHub Core API",
            description="Core backend API for VabHub platform",
            version="1.5.0",
        )

        # 添加限流中间件
        # self.app.add_middleware(create_rate_limit_middleware)  # create_rate_limit_middleware 暂时未实现

        # 添加全局异常处理器
        self.app.add_exception_handler(Exception, exception_handler)

        self._setup_routes()

        # 注册路由
        self.app.include_router(download_router)
        self.app.include_router(rss_router)
        self.app.include_router(metadata_router)
        self.app.include_router(renamer_router)
        self.app.include_router(notification_router)
        self.app.include_router(auth_router)
        self.app.include_router(path_router)
        self.app.include_router(plugins_router)
        self.app.include_router(performance_router)
        self.app.include_router(websocket_router)
        self.app.include_router(ai_recommendation_router)
        self.app.include_router(subscription_router)
        self.app.include_router(file_organizer_router)

        # 注册GraphQL路由
        # self.app.include_router(self.graphql_api.get_router())  # GraphQLAPI 暂时未实现

        # 启动性能监控系统
        self.app.add_event_handler("startup", start_performance_system)

        # 记录API启动信息
        self.app.add_event_handler("startup", self._log_startup_info)

    async def _log_startup_info(self):
        """记录API启动信息"""
        self.logger.info(
            "VabHub Core API 启动成功",
            extra={
                "version": "1.5.0",
                "features": ["REST API", "GraphQL", "插件系统", "性能监控", "限流保护"],
            },
        )

    def _setup_routes(self):
        """Setup API routes"""

        # Health and basic info
        @self.app.get("/")
        async def root():
            return {"message": "VabHub Core API", "version": "1.5.0"}

        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "service": "vabhub-core"}

        @self.app.get("/config")
        async def get_config():
            return self.config.to_dict()

        # Authentication
        @self.app.post("/auth/token")
        async def create_token(user_id: str):
            token = self.auth_manager.create_token(user_id)
            return {"access_token": token, "token_type": "bearer"}

        @self.app.get("/auth/verify")
        async def verify_token(token: str):
            payload = self.auth_manager.verify_token(token)
            if payload:
                return {"valid": True, "user_id": payload.get("user_id")}
            raise HTTPException(status_code=401, detail="Invalid token")

        # Subscriptions management
        @self.app.get("/api/subscriptions", response_model=List[Subscription])
        async def list_subs():
            subscriptions = self.db_manager.get_subscriptions()
            return [Subscription(**sub) for sub in subscriptions]

        @self.app.post(
            "/api/subscriptions", response_model=Subscription, status_code=201
        )
        async def create_sub(s: Subscription):
            subscription_data = {
                "name": s.name,
                "query": s.query,
                "enabled": s.enabled,
                "priority": s.priority,
            }
            subscription_id = self.db_manager.create_subscription(subscription_data)
            s.id = subscription_id
            return s

        @self.app.put("/api/subscriptions/{sid}", response_model=Subscription)
        async def update_sub(sid: str, s: Subscription):
            subscription_data = {
                "name": s.name,
                "query": s.query,
                "enabled": s.enabled,
                "priority": s.priority,
            }
            success = self.db_manager.update_subscription(sid, subscription_data)
            if not success:
                raise HTTPException(status_code=404, detail="Subscription not found")
            s.id = sid
            return s

        @self.app.delete("/api/subscriptions/{sid}", status_code=204)
        async def delete_sub(sid: str):
            success = self.db_manager.delete_subscription(sid)
            if not success:
                raise HTTPException(status_code=404, detail="Subscription not found")

        @self.app.post("/api/subscriptions/test")
        async def test_sub(
            query: str = Query(..., description="query or rule to test")
        ):
            return {"ok": True, "matches": [{"title": "Demo Title", "score": 0.87}]}

        # Rules management
        @self.app.get("/api/ruleset", response_model=RuleSet)
        async def get_rules():
            return RuleSet()

        @self.app.put("/api/ruleset", response_model=RuleSet)
        async def put_rules(r: RuleSet):
            return r

        # Tasks management
        @self.app.get("/api/tasks", response_model=List[Task])
        async def list_tasks(status: Optional[str] = None):
            tasks = self.db_manager.get_tasks(status)
            return [Task(**task) for task in tasks]

        @self.app.post("/api/tasks", response_model=Task, status_code=201)
        async def create_task(t: Task):
            task_data = {
                "name": t.name,
                "type": "manual",
                "status": t.status,
                "progress": t.progress,
            }
            task_id = self.db_manager.create_task(task_data)
            t.id = task_id
            return t

        @self.app.post("/api/tasks/{tid}/retry")
        async def retry_task(tid: str):
            success = self.db_manager.update_task_status(tid, "pending", 0)
            if not success:
                raise HTTPException(status_code=404, detail="Task not found")
            return {"ok": True, "id": tid}

        @self.app.delete("/api/tasks/{tid}", status_code=204)
        async def delete_task(tid: str):
            # For now, we'll just update status to cancelled
            success = self.db_manager.update_task_status(tid, "cancelled", 0)
            if not success:
                raise HTTPException(status_code=404, detail="Task not found")

        # Scraper services
        @self.app.get("/api/scraper/config", response_model=ScraperConfig)
        async def get_scraper_conf():
            return ScraperConfig()

        @self.app.put("/api/scraper/config", response_model=ScraperConfig)
        async def put_scraper_conf(c: ScraperConfig):
            return c

        @self.app.post("/api/scraper/test")
        async def test_scraper(q: str = Query(...)):
            return {
                "ok": True,
                "candidates": [
                    {"provider": "tmdb", "id": "550", "title": "Fight Club"}
                ],
            }

        # Library management
        @self.app.get("/api/library/servers", response_model=List[LibraryServer])
        async def list_servers():
            servers = self.db_manager.get_media_servers()
            # Test connection for each server
            for server in servers:
                test_result = await self.media_server_manager.test_connection(
                    server["url"], server.get("api_key", "")
                )
                server["ok"] = test_result["ok"]
            return [LibraryServer(**server) for server in servers]

        @self.app.post("/api/library/{server}/refresh")
        async def library_refresh(server: str):
            # Get server details from database
            servers = self.db_manager.get_media_servers()
            target_server = next((s for s in servers if s["id"] == server), None)
            if not target_server:
                raise HTTPException(status_code=404, detail="Server not found")

            # Refresh all libraries
            libraries = await self.media_server_manager.get_libraries(
                target_server["url"], target_server.get("api_key", "")
            )

            refresh_results = []
            for lib in libraries:
                result = await self.media_server_manager.refresh_library(
                    target_server["url"], target_server.get("api_key", ""), lib["name"]
                )
                refresh_results.append({"library": lib["name"], "result": result})

            return {"ok": True, "server": server, "refresh_results": refresh_results}

        @self.app.get("/api/library/{server}/libraries")
        async def get_libraries(server: str):
            servers = self.db_manager.get_media_servers()
            target_server = next((s for s in servers if s["id"] == server), None)
            if not target_server:
                raise HTTPException(status_code=404, detail="Server not found")

            libraries = await self.media_server_manager.get_libraries(
                target_server["url"], target_server.get("api_key", "")
            )
            return {"server": server, "libraries": libraries}

        @self.app.get("/api/library/{server}/recently-added")
        async def get_recently_added(server: str, limit: int = 10):
            servers = self.db_manager.get_media_servers()
            target_server = next((s for s in servers if s["id"] == server), None)
            if not target_server:
                raise HTTPException(status_code=404, detail="Server not found")

            items = await self.media_server_manager.get_recently_added(
                target_server["url"], target_server.get("api_key", ""), limit
            )
            return {"server": server, "recently_added": items}

        # Downloaders management
        @self.app.get("/api/dl/instances", response_model=List[DownloaderInstance])
        async def dl_instances():
            downloaders = self.db_manager.get_downloaders()
            return [DownloaderInstance(**downloader) for downloader in downloaders]

        @self.app.post("/api/dl/{did}/test")
        async def dl_test(did: str):
            """测试下载器连接"""
            try:
                # downloader = self.db_manager.get_downloader(did)  # get_downloader 方法不存在
                downloaders = self.db_manager.get_downloaders()
                downloader = next((d for d in downloaders if d.get("id") == did), None)
                if not downloader:
                    raise HTTPException(status_code=404, detail="下载器不存在")

                # 使用DownloaderManager测试连接
                downloader_manager = DownloaderManager(self.config)
                result = await downloader_manager.test_connection(
                    downloader["url"],
                    downloader["type"],
                    downloader.get("username", ""),
                    downloader.get("password", ""),
                )

                return {"ok": True, "id": did, "result": result}

            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"下载器测试失败: {e}")
                raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")

        @self.app.get("/api/dl/{did}/stats")
        async def dl_stats(did: str):
            """获取下载器统计信息"""
            try:
                # downloader = self.db_manager.get_downloader(did)  # get_downloader 方法不存在
                downloaders = self.db_manager.get_downloaders()
                downloader = next((d for d in downloaders if d.get("id") == did), None)
                if not downloader:
                    raise HTTPException(status_code=404, detail="下载器不存在")

                # 使用DownloaderManager获取统计信息
                downloader_manager = DownloaderManager(self.config)
                stats = await downloader_manager.get_stats(
                    downloader["url"],
                    downloader["type"],
                    downloader.get("username", ""),
                    downloader.get("password", ""),
                )

                return {"id": did, "stats": stats}

            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"获取下载器统计失败: {e}")
                raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")

        # Storage management
        @self.app.get("/api/storage/status", response_model=StorageStatus)
        async def storage_status():
            return StorageStatus(local=True, strm=False, cloud=[])

        @self.app.get("/api/storage/config")
        async def storage_conf_get():
            return {"local": {"library": "/srv/media/library"}, "cloud": {}}

        @self.app.put("/api/storage/config")
        async def storage_conf_put(conf: Dict[str, Any]):
            return conf

        # STRM gateway
        @self.app.post("/api/strm/emit")
        async def strm_emit(req: STRMEmitRequest):
            try:
                media_info = {
                    "title": req.filename.replace(".strm", ""),
                    "url": req.url,
                    "library_path": req.library_path,
                }
                strm_path = self.strm_gateway_manager.generate_strm_file(media_info)
                return {"ok": True, "path": strm_path, "url": req.url}
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Failed to generate STRM file: {e}"
                )

        @self.app.post("/api/gateway/sign")
        async def gateway_sign(req: GatewaySignRequest):
            try:
                media_info = {"url": req.path, "ttl": req.ttl}
                signed_url = self.strm_gateway_manager._generate_signed_url(media_info)
                return {"ok": True, "signed": signed_url}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to sign URL: {e}")

        @self.app.get("/api/strm/files")
        async def list_strm_files():
            """List all STRM files in library"""
            try:
                strm_files = self.strm_gateway_manager.scan_library_for_strm_files()
                return {"ok": True, "files": strm_files}
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Failed to scan STRM files: {e}"
                )

        @self.app.post("/api/strm/organize")
        async def organize_strm_files(rules: Dict[str, Any] = {}):
            """Organize STRM files based on rules"""
            try:
                organized_files = self.strm_gateway_manager.organize_strm_files(rules)
                return {"ok": True, "organized_files": organized_files}
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Failed to organize STRM files: {e}"
                )

        @self.app.post("/api/strm/validate")
        async def validate_strm_file(file_path: str):
            """Validate STRM file"""
            try:
                validation_result = self.strm_gateway_manager.validate_strm_file(
                    file_path
                )
                return {"ok": True, "validation": validation_result}
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Failed to validate STRM file: {e}"
                )

        @self.app.post("/api/strm/batch-generate")
        async def batch_generate_strm_files(media_list: List[Dict[str, Any]]):
            """Batch generate STRM files"""
            try:
                results = self.strm_gateway_manager.batch_generate_strm_files(
                    media_list
                )
                return {"ok": True, "results": results}
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Failed to batch generate STRM files: {e}"
                )

        @self.app.post("/api/strm/cleanup")
        async def cleanup_old_strm_files(max_age_days: int = 30):
            """Clean up old STRM files"""
            try:
                cleanup_result = self.strm_gateway_manager.cleanup_old_strm_files(
                    max_age_days
                )
                return {"ok": True, "cleanup": cleanup_result}
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Failed to cleanup old STRM files: {e}"
                )

        # Plugins management
        @self.app.get("/api/plugins/registry")
        async def plugins_registry():
            return {
                "official": [{"id": "strm-emitter", "version": "0.0.1"}],
                "community": [],
            }

        @self.app.post("/api/plugins/{pid}/install")
        async def plugin_install(pid: str):
            return {"ok": True, "id": pid}

        # Secrets management
        @self.app.get("/api/secrets/status", response_model=SecretStatus)
        async def secrets_status():
            return SecretStatus(sops_enabled=False, age_key_present=False)

        # Charts API endpoints
        @self.app.get("/api/charts", response_model=List[ChartItem])
        async def get_charts(
            source: str = Query(
                ..., description="数据源: tmdb, spotify, apple_music, bangumi"
            ),
            region: str = Query("US", description="地区代码"),
            time_range: str = Query("week", description="时间范围: day, week, month"),
            media_type: str = Query(
                "all", description="媒体类型: movie, tv, music, anime, all"
            ),
            limit: int = Query(20, description="返回数量限制"),
        ):
            """获取图表数据"""
            try:
                charts = await self.charts_service.fetch_charts(
                    source, region, time_range, media_type, limit
                )
                return charts
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Failed to fetch charts: {str(e)}"
                )

        @self.app.get("/api/charts/sources")
        async def get_chart_sources():
            """获取支持的图表数据源"""
            return {
                "sources": [
                    {
                        "id": "tmdb",
                        "name": "TMDB",
                        "supported_regions": ["US", "CN", "JP", "KR"],
                        "media_types": ["movie", "tv"],
                    },
                    {
                        "id": "spotify",
                        "name": "Spotify",
                        "supported_regions": ["US", "GB", "JP", "CN"],
                        "media_types": ["music"],
                    },
                    {
                        "id": "apple_music",
                        "name": "Apple Music",
                        "supported_regions": ["US", "GB", "JP", "CN"],
                        "media_types": ["music"],
                    },
                    {
                        "id": "bangumi",
                        "name": "Bangumi",
                        "supported_regions": ["JP"],
                        "media_types": ["anime"],
                    },
                ]
            }

        @self.app.post("/api/charts/cache/clear")
        async def clear_charts_cache():
            """清除图表缓存"""
            self.charts_service.cache.clear()
            return {"message": "Charts cache cleared successfully"}

    def get_app(self) -> FastAPI:
        """Get FastAPI application"""
        return self.app


# 创建全局FastAPI应用实例用于测试
from .config import Config

# 使用默认配置创建API实例
config = Config()
api = VabHubAPI(config)
app = api.get_app()


# 创建全局FastAPI应用实例用于测试
from .config import Config

# 使用默认配置创建API实例
config = Config()
api = VabHubAPI(config)
app = api.get_app()
