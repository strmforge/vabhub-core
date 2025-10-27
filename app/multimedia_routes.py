#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多媒体API路由
支持音乐、图片、电子书等多媒体文件的管理
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import asyncio
import os
from pathlib import Path

from core.music_manager import MusicManager
from core.image_manager import ImageManager
# # # from core.ebook_manager import EbookManager  # 暂时注释掉，避免依赖问题  # 暂时注释掉，避免依赖问题  # 暂时注释掉，避免依赖问题

router = APIRouter(prefix="/api/multimedia", tags=["multimedia"])

# 初始化管理器
music_manager = MusicManager()
image_manager = ImageManager()
# # # # # # # # # ebook_manager = EbookManager()  # 暂时注释掉，避免依赖问题  # 暂时注释掉，避免依赖问题  # 暂时注释掉，避免依赖问题  # 暂时注释掉，避免依赖问题  # 暂时注释掉，避免依赖问题  # 暂时注释掉，避免依赖问题  # 暂时注释掉，避免依赖问题  # 暂时注释掉，避免依赖问题  # 暂时注释掉，避免依赖问题


@router.post("/music/analyze")
async def analyze_music_file(
    file_path: str = Form(..., description="音乐文件路径"),
    analyze_content: bool = Form(True, description="是否分析内容")
):
    """分析音乐文件"""
    try:
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        result = await music_manager.analyze_music_file(file_path)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return JSONResponse({
            "success": True,
            "data": result,
            "message": "音乐文件分析完成"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/music/upload")
async def upload_music_file(
    file: UploadFile = File(..., description="音乐文件"),
    destination: str = Form("./", description="保存目录")
):
    """上传音乐文件"""
    try:
        # 检查文件类型
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in music_manager.supported_formats:
            raise HTTPException(status_code=400, detail="不支持的音频格式")
        
        # 保存文件
        save_path = Path(destination) / file.filename
        content = await file.read()
        
        with open(save_path, "wb") as f:
            f.write(content)
        
        # 分析文件
        result = await music_manager.analyze_music_file(str(save_path))
        
        return JSONResponse({
            "success": True,
            "data": {
                "file_path": str(save_path),
                "analysis": result
            },
            "message": "音乐文件上传并分析完成"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.get("/music/search")
async def search_music(
    query: str = Query(..., description="搜索关键词"),
    search_type: str = Query("all", description="搜索类型: all, artists, albums, tracks")
):
    """搜索音乐"""
    try:
        results = await music_manager.search_music(query, search_type)
        
        return JSONResponse({
            "success": True,
            "data": results,
            "message": f"找到 {len(results.get('artists', []))} 个艺术家, "
                       f"{len(results.get('albums', []))} 个专辑"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.post("/music/playlist")
async def create_playlist(
    name: str = Form(..., description="播放列表名称"),
    tracks: List[str] = Form(..., description="曲目列表")
):
    """创建播放列表"""
    try:
        playlist = await music_manager.create_playlist(name, tracks)
        
        return JSONResponse({
            "success": True,
            "data": playlist,
            "message": "播放列表创建成功"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建播放列表失败: {str(e)}")


@router.get("/music/artist/{artist_name}")
async def get_artist_discography(artist_name: str):
    """获取艺术家作品集"""
    try:
        discography = await music_manager.get_artist_discography(artist_name)
        
        if "error" in discography:
            raise HTTPException(status_code=404, detail=discography["error"])
        
        return JSONResponse({
            "success": True,
            "data": discography,
            "message": f"获取到 {artist_name} 的作品集"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取作品集失败: {str(e)}")


@router.post("/image/analyze")
async def analyze_image_file(
    file_path: str = Form(..., description="图片文件路径"),
    detect_faces: bool = Form(True, description="是否检测人脸"),
    analyze_colors: bool = Form(True, description="是否分析颜色")
):
    """分析图片文件"""
    try:
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        result = await image_manager.analyze_image_file(file_path)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return JSONResponse({
            "success": True,
            "data": result,
            "message": "图片文件分析完成"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/image/upload")
async def upload_image_file(
    file: UploadFile = File(..., description="图片文件"),
    destination: str = Form("./", description="保存目录")
):
    """上传图片文件"""
    try:
        # 检查文件类型
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in image_manager.supported_formats:
            raise HTTPException(status_code=400, detail="不支持的图片格式")
        
        # 保存文件
        save_path = Path(destination) / file.filename
        content = await file.read()
        
        with open(save_path, "wb") as f:
            f.write(content)
        
        # 分析文件
        result = await image_manager.analyze_image_file(str(save_path))
        
        return JSONResponse({
            "success": True,
            "data": {
                "file_path": str(save_path),
                "analysis": result
            },
            "message": "图片文件上传并分析完成"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/image/album")
async def create_image_album(
    name: str = Form(..., description="相册名称"),
    images: List[str] = Form(..., description="图片列表")
):
    """创建相册"""
    try:
        album = await image_manager.create_album(name, images)
        
        return JSONResponse({
            "success": True,
            "data": album,
            "message": "相册创建成功"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建相册失败: {str(e)}")


@router.get("/image/search")
async def search_images(
    query: str = Query(..., description="搜索关键词"),
    search_type: str = Query("all", description="搜索类型: all, filename, tags, scene")
):
    """搜索图片"""
    try:
        results = await image_manager.search_images(query, search_type)
        
        return JSONResponse({
            "success": True,
            "data": results,
            "message": f"搜索完成"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.post("/ebook/analyze")
async def analyze_ebook_file(
    file_path: str = Form(..., description="电子书文件路径"),
    extract_content: bool = Form(True, description="是否提取内容")
):
    """分析电子书文件"""
    try:
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        result = await ebook_manager.analyze_ebook_file(file_path)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return JSONResponse({
            "success": True,
            "data": result,
            "message": "电子书文件分析完成"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/ebook/upload")
async def upload_ebook_file(
    file: UploadFile = File(..., description="电子书文件"),
    destination: str = Form("./", description="保存目录")
):
    """上传电子书文件"""
    try:
        # 检查文件类型
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ebook_manager.supported_formats:
            raise HTTPException(status_code=400, detail="不支持的电子书格式")
        
        # 保存文件
        save_path = Path(destination) / file.filename
        content = await file.read()
        
        with open(save_path, "wb") as f:
            f.write(content)
        
        # 分析文件
        result = await ebook_manager.analyze_ebook_file(str(save_path))
        
        return JSONResponse({
            "success": True,
            "data": {
                "file_path": str(save_path),
                "analysis": result
            },
            "message": "电子书文件上传并分析完成"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/ebook/library")
async def create_ebook_library(
    name: str = Form(..., description="电子书库名称"),
    books: List[str] = Form(..., description="书籍列表")
):
    """创建电子书库"""
    try:
        library = await ebook_manager.create_library(name, books)
        
        return JSONResponse({
            "success": True,
            "data": library,
            "message": "电子书库创建成功"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建书库失败: {str(e)}")


@router.get("/ebook/search")
async def search_ebooks(
    query: str = Query(..., description="搜索关键词"),
    search_type: str = Query("all", description="搜索类型: all, title, author, genre")
):
    """搜索电子书"""
    try:
        results = await ebook_manager.search_ebooks(query, search_type)
        
        return JSONResponse({
            "success": True,
            "data": results,
            "message": f"找到 {len(results.get('by_title', []))} 本书籍, "
                       f"{len(results.get('by_author', []))} 位作者"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.get("/stats")
async def get_multimedia_stats():
    """获取多媒体统计信息"""
    try:
        stats = {
            "music": {
                "artists_count": len(music_manager.artist_database),
                "albums_count": len(music_manager.album_database),
                "playlists_count": len(music_manager.playlist_database)
            },
            "images": {
                "albums_count": len(image_manager.album_database),
                "faces_count": len(image_manager.face_database),
                "tags_count": len(image_manager.tag_database)
            },
            "ebooks": {
                "authors_count": len(ebook_manager.author_database),
                "books_count": len(ebook_manager.book_database),
                "libraries_count": len(ebook_manager.library_database)
            }
        }
        
        return JSONResponse({
            "success": True,
            "data": stats,
            "message": "多媒体统计信息获取成功"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get("/supported-formats")
async def get_supported_formats():
    """获取支持的文件格式"""
    try:
        formats = {
            "music": music_manager.supported_formats,
            "images": image_manager.supported_formats,
            "ebooks": ebook_manager.supported_formats
        }
        
        return JSONResponse({
            "success": True,
            "data": formats,
            "message": "支持的文件格式列表"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取格式列表失败: {str(e)}")


# 批量处理端点
@router.post("/batch/analyze")
async def batch_analyze_files(
    file_paths: List[str] = Form(..., description="文件路径列表"),
    media_type: str = Form(..., description="媒体类型: music, image, ebook")
):
    """批量分析文件"""
    try:
        results = []
        
        for file_path in file_paths:
            if not os.path.exists(file_path):
                results.append({"file_path": file_path, "status": "error", "message": "文件不存在"})
                continue
            
            try:
                if media_type == "music":
                    result = await music_manager.analyze_music_file(file_path)
                elif media_type == "image":
                    result = await image_manager.analyze_image_file(file_path)
                elif media_type == "ebook":
                    result = await ebook_manager.analyze_ebook_file(file_path)
                else:
                    results.append({"file_path": file_path, "status": "error", "message": "不支持的媒体类型"})
                    continue
                
                if "error" in result:
                    results.append({"file_path": file_path, "status": "error", "message": result["error"]})
                else:
                    results.append({"file_path": file_path, "status": "success", "data": result})
                    
            except Exception as e:
                results.append({"file_path": file_path, "status": "error", "message": str(e)})
        
        return JSONResponse({
            "success": True,
            "data": results,
            "message": f"批量分析完成，成功: {len([r for r in results if r['status'] == 'success'])}，失败: {len([r for r in results if r['status'] == 'error'])}"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量分析失败: {str(e)}")