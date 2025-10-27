#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音乐相关API路由
提供音乐文件识别、刮削和管理功能
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import os
import asyncio
import logging
from pathlib import Path

from core.music_scraper import MusicScraper

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/music", tags=["music"])

# 请求/响应模型
class MusicScrapeRequest(BaseModel):
    """音乐刮削请求"""
    file_path: str = Field(..., description="音乐文件路径")
    use_fingerprint: bool = Field(True, description="是否使用音频指纹识别")
    use_metadata: bool = Field(True, description="是否使用元数据搜索")

class MusicBatchScrapeRequest(BaseModel):
    """批量音乐刮削请求"""
    file_paths: List[str] = Field(..., description="音乐文件路径列表")
    use_fingerprint: bool = Field(True, description="是否使用音频指纹识别")
    use_metadata: bool = Field(True, description="是否使用元数据搜索")

class MusicSearchRequest(BaseModel):
    """音乐搜索请求"""
    query: str = Field(..., description="搜索查询")
    search_type: str = Field("recording", description="搜索类型: recording/release/artist")
    limit: int = Field(5, description="结果数量限制")

class MusicMetadataResponse(BaseModel):
    """音乐元数据响应"""
    file_path: str
    file_name: str
    file_size: int
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    year: Optional[str] = None
    genre: Optional[str] = None
    duration: Optional[int] = None
    bitrate: Optional[int] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    mbid: Optional[str] = None
    sources: List[str]
    scraped_at: str

class MusicStatisticsResponse(BaseModel):
    """音乐统计响应"""
    total_files: int
    successful_scrapes: int
    success_rate: float
    source_distribution: Dict[str, int]

# 全局音乐刮削器实例
_music_scraper: Optional[MusicScraper] = None

def get_music_scraper() -> MusicScraper:
    """获取音乐刮削器实例"""
    global _music_scraper
    if _music_scraper is None:
        # 从环境变量获取AcoustID API密钥
        acoustid_api_key = os.getenv('ACOUSTID_API_KEY')
        _music_scraper = MusicScraper(acoustid_api_key=acoustid_api_key)
    return _music_scraper

@router.get("/health")
async def health_check():
    """音乐服务健康检查"""
    scraper = get_music_scraper()
    return {
        "status": "healthy",
        "service": "music-scraper",
        "acoustid_available": scraper.acoustid_api_key is not None
    }

@router.post("/scrape")
async def scrape_music_file(request: MusicScrapeRequest) -> MusicMetadataResponse:
    """刮削单个音乐文件"""
    try:
        scraper = get_music_scraper()
        
        # 验证文件存在
        if not os.path.exists(request.file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 执行刮削
        metadata = scraper.scrape_music_file(request.file_path)
        
        # 转换为响应模型
        return MusicMetadataResponse(**metadata)
        
    except Exception as e:
        logger.error(f"音乐文件刮削失败 {request.file_path}: {e}")
        raise HTTPException(status_code=500, detail=f"刮削失败: {str(e)}")

@router.post("/scrape/batch")
async def batch_scrape_music_files(request: MusicBatchScrapeRequest) -> Dict[str, MusicMetadataResponse]:
    """批量刮削音乐文件"""
    try:
        scraper = get_music_scraper()
        
        # 验证文件存在
        for file_path in request.file_paths:
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail=f"文件不存在: {file_path}")
        
        # 执行批量刮削
        results = scraper.batch_scrape_music_files(request.file_paths)
        
        # 转换为响应模型
        response = {}
        for file_path, metadata in results.items():
            if 'error' not in metadata:
                response[file_path] = MusicMetadataResponse(**metadata)
            else:
                response[file_path] = {"error": metadata['error']}
        
        return response
        
    except Exception as e:
        logger.error(f"批量音乐文件刮削失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量刮削失败: {str(e)}")

@router.post("/search")
async def search_music(request: MusicSearchRequest) -> List[Dict[str, Any]]:
    """搜索音乐信息"""
    try:
        scraper = get_music_scraper()
        
        # 执行搜索
        results = scraper.search_musicbrainz(request.query, request.search_type)
        
        # 限制结果数量
        limited_results = results[:request.limit]
        
        return limited_results
        
    except Exception as e:
        logger.error(f"音乐搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

@router.get("/statistics")
async def get_music_statistics() -> MusicStatisticsResponse:
    """获取音乐刮削统计信息"""
    try:
        scraper = get_music_scraper()
        
        # 获取统计信息
        stats = scraper.get_scraping_statistics()
        
        return MusicStatisticsResponse(**stats)
        
    except Exception as e:
        logger.error(f"获取音乐统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")

@router.post("/upload")
async def upload_music_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """上传音乐文件并自动刮削"""
    try:
        # 验证文件类型
        allowed_extensions = {'.mp3', '.flac', '.wav', '.ogg', '.m4a', '.aac'}
        file_extension = Path(file.filename).suffix.lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件类型: {file_extension}"
            )
        
        # 创建上传目录
        upload_dir = Path("uploads/music")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存文件
        file_path = upload_dir / file.filename
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 异步刮削
        scraper = get_music_scraper()
        
        def process_uploaded_file():
            """处理上传的文件"""
            try:
                metadata = scraper.scrape_music_file(str(file_path))
                logger.info(f"上传文件刮削完成: {file.filename}")
                return metadata
            except Exception as e:
                logger.error(f"上传文件刮削失败: {e}")
                return {"error": str(e)}
        
        # 在后台处理
        background_tasks.add_task(process_uploaded_file)
        
        return {
            "status": "success",
            "message": "文件上传成功，正在处理中",
            "file_path": str(file_path),
            "file_name": file.filename
        }
        
    except Exception as e:
        logger.error(f"音乐文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

@router.get("/supported-formats")
async def get_supported_formats():
    """获取支持的音频格式"""
    return {
        "supported_formats": [
            {"extension": ".mp3", "name": "MP3", "description": "MPEG Audio Layer III"},
            {"extension": ".flac", "name": "FLAC", "description": "Free Lossless Audio Codec"},
            {"extension": ".wav", "name": "WAV", "description": "Waveform Audio File Format"},
            {"extension": ".ogg", "name": "OGG", "description": "Ogg Vorbis"},
            {"extension": ".m4a", "name": "M4A", "description": "MPEG-4 Audio"},
            {"extension": ".aac", "name": "AAC", "description": "Advanced Audio Coding"}
        ],
        "total_formats": 6
    }

@router.get("/fingerprint/{file_path:path}")
async def get_audio_fingerprint(file_path: str):
    """获取音频指纹"""
    try:
        scraper = get_music_scraper()
        
        # 验证文件存在
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 生成指纹
        fingerprint = scraper.generate_audio_fingerprint(file_path)
        
        if fingerprint:
            return {
                "status": "success",
                "file_path": file_path,
                "fingerprint": fingerprint[:100] + "..." if len(fingerprint) > 100 else fingerprint,
                "fingerprint_length": len(fingerprint)
            }
        else:
            raise HTTPException(status_code=500, detail="指纹生成失败")
        
    except Exception as e:
        logger.error(f"音频指纹生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"指纹生成失败: {str(e)}")

# 测试端点
@router.get("/test")
async def test_music_scraper():
    """测试音乐刮削器"""
    try:
        scraper = get_music_scraper()
        
        # 创建测试文件路径（实际使用时需要真实文件）
        test_files = [
            "test_music_1.mp3",
            "test_music_2.flac"
        ]
        
        # 检查测试文件是否存在
        existing_files = []
        for file_path in test_files:
            if os.path.exists(file_path):
                existing_files.append(file_path)
        
        if not existing_files:
            return {
                "status": "success",
                "message": "音乐刮削器已初始化，但未找到测试文件",
                "acoustid_available": scraper.acoustid_api_key is not None,
                "suggestion": "请上传音乐文件进行测试"
            }
        
        # 测试刮削
        results = {}
        for file_path in existing_files:
            try:
                metadata = scraper.scrape_music_file(file_path)
                results[file_path] = {
                    "status": "success",
                    "metadata": metadata
                }
            except Exception as e:
                results[file_path] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return {
            "status": "success",
            "test_results": results,
            "acoustid_available": scraper.acoustid_api_key is not None
        }
        
    except Exception as e:
        logger.error(f"音乐刮削器测试失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")