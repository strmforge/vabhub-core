"""
元数据刮削API路由
集成NASTool的元数据获取精华功能
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

from core.metadata_scraper import MetadataScraper

router = APIRouter(prefix="/metadata", tags=["metadata"])

# 全局元数据刮削器实例
metadata_scraper = MetadataScraper()


class SearchRequest(BaseModel):
    """搜索请求模型"""
    query: str = Field(..., description="搜索关键词")
    media_type: str = Field("movie", description="媒体类型: movie, tv, anime")
    year: Optional[int] = Field(None, description="年份过滤")


class MediaDetailsRequest(BaseModel):
    """媒体详情请求模型"""
    source: str = Field(..., description="数据源: tmdb, douban, omdb")
    media_id: str = Field(..., description="媒体ID")
    media_type: str = Field("movie", description="媒体类型")


class APIKeyConfig(BaseModel):
    """API密钥配置模型"""
    source: str = Field(..., description="数据源名称")
    api_key: str = Field(..., description="API密钥")


class MetadataResponse(BaseModel):
    """元数据响应模型"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


@router.on_event("startup")
async def startup_event():
    """应用启动时初始化元数据刮削器"""
    await metadata_scraper.initialize()


@router.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    await metadata_scraper.close()


@router.get("/status", response_model=MetadataResponse)
async def get_metadata_status():
    """获取元数据刮削器状态"""
    try:
        status = metadata_scraper.get_status()
        return MetadataResponse(
            success=True,
            message="元数据刮削器状态获取成功",
            data=status
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.post("/search", response_model=MetadataResponse)
async def search_media(search_request: SearchRequest):
    """搜索媒体"""
    try:
        results = await metadata_scraper.search_media(
            query=search_request.query,
            media_type=search_request.media_type,
            year=search_request.year
        )
        
        return MetadataResponse(
            success=True,
            message=f"搜索到 {len(results)} 个结果",
            data={"results": results}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.post("/details", response_model=MetadataResponse)
async def get_media_details(details_request: MediaDetailsRequest):
    """获取媒体详细信息"""
    try:
        metadata = await metadata_scraper.get_media_details(
            source=details_request.source,
            media_id=details_request.media_id,
            media_type=details_request.media_type
        )
        
        if metadata:
            return MetadataResponse(
                success=True,
                message="媒体详情获取成功",
                data={"metadata": metadata.__dict__}
            )
        else:
            return MetadataResponse(
                success=False,
                message="未找到媒体详情",
                data=None
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取媒体详情失败: {str(e)}")


@router.post("/config/api_key", response_model=MetadataResponse)
async def set_api_key(config: APIKeyConfig):
    """设置API密钥"""
    try:
        metadata_scraper.set_api_key(config.source, config.api_key)
        return MetadataResponse(
            success=True,
            message=f"{config.source} API密钥设置成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置API密钥失败: {str(e)}")


@router.put("/config/source/{source}/enable", response_model=MetadataResponse)
async def enable_source(source: str, enabled: bool = True):
    """启用/禁用数据源"""
    try:
        metadata_scraper.enable_source(source, enabled)
        status = "启用" if enabled else "禁用"
        return MetadataResponse(
            success=True,
            message=f"{source} 数据源{status}成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"操作数据源失败: {str(e)}")


@router.get("/sources", response_model=MetadataResponse)
async def list_sources():
    """获取所有数据源信息"""
    try:
        sources_info = {}
        for source_name, source_config in metadata_scraper.sources.items():
            sources_info[source_name] = {
                "name": source_config["name"],
                "enabled": source_config["enabled"],
                "configured": source_config["api_key"] is not None,
                "base_url": source_config["base_url"]
            }
        
        return MetadataResponse(
            success=True,
            message="数据源列表获取成功",
            data={"sources": sources_info}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取数据源列表失败: {str(e)}")


@router.post("/batch/details", response_model=MetadataResponse)
async def get_batch_media_details(requests: List[MediaDetailsRequest]):
    """批量获取媒体详细信息"""
    try:
        import asyncio
        
        # 并行获取所有媒体详情
        tasks = []
        for request in requests:
            task = metadata_scraper.get_media_details(
                source=request.source,
                media_id=request.media_id,
                media_type=request.media_type
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        successful_results = []
        failed_requests = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_requests.append({
                    "index": i,
                    "request": requests[i].dict(),
                    "error": str(result)
                })
            elif result:
                successful_results.append({
                    "request": requests[i].dict(),
                    "metadata": result.__dict__
                })
        
        return MetadataResponse(
            success=True,
            message=f"批量获取完成: 成功 {len(successful_results)} 个, 失败 {len(failed_requests)} 个",
            data={
                "successful": successful_results,
                "failed": failed_requests
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量获取媒体详情失败: {str(e)}")


@router.get("/health", response_model=MetadataResponse)
async def health_check():
    """健康检查"""
    try:
        # 简单的健康检查，测试一个数据源是否可用
        status = metadata_scraper.get_status()
        
        # 检查是否有配置的数据源
        configured_sources = status.get("configured_sources", [])
        
        if configured_sources:
            return MetadataResponse(
                success=True,
                message="元数据刮削器运行正常",
                data={
                    "status": "healthy",
                    "configured_sources": configured_sources,
                    "enabled_sources": status.get("enabled_sources", [])
                }
            )
        else:
            return MetadataResponse(
                success=True,
                message="元数据刮削器运行正常（无配置的数据源）",
                data={
                    "status": "healthy_no_config",
                    "configured_sources": configured_sources,
                    "enabled_sources": status.get("enabled_sources", [])
                }
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")