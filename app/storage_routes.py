"""
存储 & 目录管理API路由
基于MoviePilot设计，完整复刻存储管理功能，增强音乐支持
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from ..core.storage_schemas import (
    StorageConfig, StorageInfo, FileItem, TransferRequest, 
    TransferResult, RenameRequest, RenameResult, MediaInfo
)
from ..core.file_manager_v2 import get_file_manager
from ..core.music_renamer import music_renamer
from ..core.music_classifier import music_classifier
from ..core.unified_classifier import unified_classifier

router = APIRouter(prefix="/api/storage", tags=["存储管理"])

# 文件管理器实例
file_manager = get_file_manager()

class StorageListResponse(BaseModel):
    """存储列表响应"""
    storages: List[StorageInfo]

class FileListResponse(BaseModel):
    """文件列表响应"""
    files: List[FileItem]
    total: int
    path: str

class StorageTestResponse(BaseModel):
    """存储测试响应"""
    success: bool
    message: str

class TransferResponse(BaseModel):
    """文件转移响应"""
    success: bool
    results: List[TransferResult]
    message: str

class RenameResponse(BaseModel):
    """重命名响应"""
    success: bool
    result: RenameResult
    message: str

class MusicClassificationRequest(BaseModel):
    """音乐分类请求"""
    file_paths: List[str]
    metadata: Optional[Dict[str, Any]] = None

class MusicClassificationResponse(BaseModel):
    """音乐分类响应"""
    classifications: Dict[str, Dict[str, Any]]
    statistics: Dict[str, Any]

class MusicRenameRequest(BaseModel):
    """音乐重命名请求"""
    source_path: str
    target_dir: str
    template: str = "standard"
    structure_type: str = "artist_album"
    operation: str = "move"  # rename, copy, move

class MusicRenameResponse(BaseModel):
    """音乐重命名响应"""
    success: bool
    old_path: str
    new_path: str
    media_info: Optional[MediaInfo] = None
    message: str

class MediaClassificationRequest(BaseModel):
    """媒体分类请求"""
    file_paths: List[str]
    metadata: Optional[Dict[str, Any]] = None

class MediaClassificationResponse(BaseModel):
    """媒体分类响应"""
    classifications: Dict[str, Dict[str, Any]]
    statistics: Dict[str, Any]
    directory_structures: Dict[str, str]

@router.get("/storages", response_model=StorageListResponse)
async def list_storages():
    """获取存储列表"""
    try:
        storages = file_manager.list_storages()
        return StorageListResponse(storages=storages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取存储列表失败: {str(e)}")

@router.get("/storages/{storage_id}/files")
async def list_files(
    storage_id: str,
    path: str = Query("/", description="目录路径"),
    recursive: bool = Query(False, description="是否递归"),
    page: int = Query(1, description="页码"),
    size: int = Query(100, description="每页大小")
):
    """浏览文件列表"""
    try:
        files, total = file_manager.list_files(storage_id, path, recursive, page, size)
        return FileListResponse(files=files, total=total, path=path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"浏览文件失败: {str(e)}")

@router.post("/storages/{storage_id}/mkdir")
async def create_directory(storage_id: str, path: str):
    """创建目录"""
    try:
        success = file_manager.create_directory(storage_id, path)
        return {"success": success, "message": "目录创建成功" if success else "目录创建失败"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建目录失败: {str(e)}")

@router.delete("/storages/{storage_id}/files")
async def delete_files(storage_id: str, paths: List[str]):
    """删除文件/目录"""
    try:
        success = file_manager.delete_files(storage_id, paths)
        return {"success": success, "message": "文件删除成功" if success else "文件删除失败"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")

@router.put("/storages/{storage_id}/rename")
async def rename_file(storage_id: str, old_path: str, new_path: str):
    """重命名文件"""
    try:
        success = file_manager.rename_file(storage_id, old_path, new_path)
        return {"success": success, "message": "重命名成功" if success else "重命名失败"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重命名失败: {str(e)}")

@router.post("/transfer", response_model=TransferResponse)
async def transfer_files(request: TransferRequest):
    """转移文件"""
    try:
        results = file_manager.transfer_files(
            source_storage=request.source_storage,
            source_paths=request.source_paths,
            target_storage=request.target_storage,
            target_path=request.target_path,
            transfer_type=request.transfer_type,
            overwrite=request.overwrite
        )
        
        success = all(result.success for result in results)
        return TransferResponse(
            success=success,
            results=results,
            message="文件转移完成" if success else "部分文件转移失败"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件转移失败: {str(e)}")

@router.post("/rename", response_model=RenameResponse)
async def rename_media(request: RenameRequest):
    """智能重命名媒体文件"""
    try:
        result = file_manager.rename_media(
            storage_id=request.storage_id,
            file_path=request.file_path,
            media_info=request.media_info,
            naming_rule=request.naming_rule
        )
        
        return RenameResponse(
            success=result.success,
            result=result,
            message=result.message
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重命名失败: {str(e)}")

@router.get("/storages/{storage_id}/test")
async def test_storage(storage_id: str):
    """测试存储连接"""
    try:
        success, message = file_manager.test_storage(storage_id)
        return StorageTestResponse(success=success, message=message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"存储测试失败: {str(e)}")

@router.get("/search")
async def search_files(
    storage_id: str,
    keyword: str,
    extensions: Optional[List[str]] = Query(None),
    path: str = Query("/", description="搜索路径")
):
    """搜索文件"""
    try:
        files = file_manager.search_files(storage_id, keyword, extensions, path)
        return FileListResponse(files=files, total=len(files), path=path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索文件失败: {str(e)}")

@router.get("/storages/{storage_id}/space")
async def get_storage_space(storage_id: str):
    """获取存储空间信息"""
    try:
        space_info = file_manager.get_storage_space(storage_id)
        return space_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取存储空间失败: {str(e)}")

# 二维码登录相关接口
@router.get("/storages/{storage_id}/qrcode")
async def get_qrcode(storage_id: str):
    """获取二维码登录信息"""
    try:
        qrcode_info = file_manager.get_qrcode(storage_id)
        return qrcode_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取二维码失败: {str(e)}")

@router.get("/storages/{storage_id}/login-status")
async def check_login_status(storage_id: str):
    """检查登录状态"""
    try:
        status = file_manager.check_login_status(storage_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检查登录状态失败: {str(e)}")

# ==================== 音乐功能API ====================

@router.post("/music/classify", response_model=MusicClassificationResponse)
async def classify_music_files(request: MusicClassificationRequest):
    """分类音乐文件"""
    try:
        classifications = music_classifier.batch_classify(request.file_paths)
        statistics = music_classifier.get_category_statistics(classifications)
        
        return MusicClassificationResponse(
            classifications=classifications,
            statistics=statistics
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"音乐分类失败: {str(e)}")

@router.post("/music/rename", response_model=MusicRenameResponse)
async def rename_music_file(request: MusicRenameRequest):
    """重命名音乐文件"""
    try:
        rename_request = RenameRequest(
            source_path=request.source_path,
            target_dir=request.target_dir,
            template=request.template,
            structure_type=request.structure_type,
            operation=request.operation
        )
        
        result = music_renamer.rename_music_file(rename_request)
        
        return MusicRenameResponse(
            success=result.success,
            old_path=result.old_path,
            new_path=result.new_path,
            media_info=result.media_info,
            message=result.message
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"音乐重命名失败: {str(e)}")

@router.post("/music/batch-rename")
async def batch_rename_music_files(requests: List[MusicRenameRequest]):
    """批量重命名音乐文件"""
    try:
        rename_requests = [
            RenameRequest(
                source_path=req.source_path,
                target_dir=req.target_dir,
                template=req.template,
                structure_type=req.structure_type,
                operation=req.operation
            )
            for req in requests
        ]
        
        results = music_renamer.batch_rename_music_files(rename_requests)
        
        return {
            "success": all(r.success for r in results),
            "results": [
                {
                    "success": r.success,
                    "old_path": r.old_path,
                    "new_path": r.new_path,
                    "message": r.message
                }
                for r in results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量重命名失败: {str(e)}")

@router.get("/music/templates")
async def get_music_rename_templates():
    """获取音乐重命名模板"""
    try:
        templates = music_renamer.get_rename_templates()
        return {"templates": templates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模板失败: {str(e)}")

@router.post("/music/templates/{template_name}")
async def add_music_rename_template(template_name: str, template: str):
    """添加自定义音乐重命名模板"""
    try:
        success = music_renamer.add_custom_template(template_name, template)
        return {"success": success, "message": "模板添加成功" if success else "模板添加失败"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加模板失败: {str(e)}")

@router.get("/music/supported-formats")
async def get_supported_music_formats():
    """获取支持的音乐格式"""
    try:
        formats = music_renamer.get_supported_formats()
        return {"formats": formats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取格式失败: {str(e)}")

# ==================== 统一媒体分类API ====================

@router.post("/media/classify", response_model=MediaClassificationResponse)
async def classify_media_files(request: MediaClassificationRequest):
    """分类媒体文件（支持电影、电视剧、音乐等）"""
    try:
        classifications = unified_classifier.batch_classify(request.file_paths)
        statistics = unified_classifier.get_classification_statistics(classifications)
        
        # 生成目录结构
        directory_structures = {}
        for file_path, classification in classifications.items():
            directory_structures[file_path] = unified_classifier.get_media_directory_structure(classification)
        
        return MediaClassificationResponse(
            classifications=classifications,
            statistics=statistics,
            directory_structures=directory_structures
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"媒体分类失败: {str(e)}")

@router.get("/media/detect-type")
async def detect_media_type(file_path: str):
    """检测媒体类型"""
    try:
        media_type = unified_classifier.detect_media_type(file_path)
        return {"file_path": file_path, "media_type": media_type}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检测媒体类型失败: {str(e)}")

@router.get("/media/supported-types")
async def get_supported_media_types():
    """获取支持的媒体类型"""
    try:
        return {"media_types": unified_classifier.media_types}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取媒体类型失败: {str(e)}")

# ==================== 文件上传和验证API ====================

@router.post("/upload")
async def upload_file(
    storage_id: str,
    file: UploadFile = File(...),
    target_path: str = Query("/", description="目标路径")
):
    """上传文件到指定存储"""
    try:
        # 验证文件
        validation = music_renamer.validate_music_file(file.filename)
        if not validation["valid"]:
            raise HTTPException(status_code=400, detail=validation["error"])
        
        # 保存文件到临时位置
        temp_path = f"/tmp/{file.filename}"
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 上传到存储
        success = file_manager.upload_file(storage_id, temp_path, target_path)
        
        # 清理临时文件
        import os
        os.remove(temp_path)
        
        return {"success": success, "message": "上传成功" if success else "上传失败"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

@router.post("/validate-file")
async def validate_file(file_path: str):
    """验证文件有效性"""
    try:
        validation = music_renamer.validate_music_file(file_path)
        return validation
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件验证失败: {str(e)}")

# ==================== 配置管理API ====================

@router.get("/config/classification")
async def get_classification_config():
    """获取分类配置"""
    try:
        return {"config": unified_classifier.config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")

@router.post("/config/classification/export")
async def export_classification_config(output_path: str):
    """导出分类配置"""
    try:
        success = unified_classifier.export_classification_config(output_path)
        return {"success": success, "message": "导出成功" if success else "导出失败"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出配置失败: {str(e)}")

@router.post("/config/classification/import")
async def import_classification_config(config_path: str):
    """导入分类配置"""
    try:
        success = unified_classifier.import_classification_config(config_path)
        return {"success": success, "message": "导入成功" if success else "导入失败"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入配置失败: {str(e)}")

# ==================== 123云盘特定API ====================

class Cloud123AuthRequest(BaseModel):
    """123云盘认证请求"""
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None

class Cloud123AuthResponse(BaseModel):
    """123云盘认证响应"""
    success: bool
    message: str
    qrcode_url: Optional[str] = None
    qrcode_key: Optional[str] = None

@router.post("/cloud123/auth", response_model=Cloud123AuthResponse)
async def cloud123_auth(request: Cloud123AuthRequest):
    """123云盘认证配置"""
    try:
        # 获取123云盘存储实例
        cloud123_storage = file_manager.get_storage("cloud123")
        if not cloud123_storage:
            raise HTTPException(status_code=404, detail="123云盘存储未配置")
        
        # 更新配置
        config = {}
        if request.client_id:
            config["client_id"] = request.client_id
        if request.client_secret:
            config["client_secret"] = request.client_secret
        if request.access_token:
            config["access_token"] = request.access_token
        if request.refresh_token:
            config["refresh_token"] = request.refresh_token
        
        # 初始化存储
        success = await cloud123_storage.initialize()
        
        if success:
            # 获取二维码登录信息
            qrcode_info = await cloud123_storage.get_qrcode()
            
            return Cloud123AuthResponse(
                success=True,
                message="认证配置成功",
                qrcode_url=qrcode_info.get("qrcode_url"),
                qrcode_key=qrcode_info.get("qrcode_key")
            )
        else:
            return Cloud123AuthResponse(
                success=False,
                message="认证配置失败"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"123云盘认证失败: {str(e)}")

@router.get("/cloud123/qrcode-status")
async def cloud123_qrcode_status(qrcode_key: str):
    """检查123云盘二维码登录状态"""
    try:
        cloud123_storage = file_manager.get_storage("cloud123")
        if not cloud123_storage:
            raise HTTPException(status_code=404, detail="123云盘存储未配置")
        
        status = await cloud123_storage.check_qrcode(qrcode_key)
        return status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检查二维码状态失败: {str(e)}")

@router.post("/cloud123/upload")
async def cloud123_upload_file(
    source_path: str,
    target_path: str
):
    """上传文件到123云盘"""
    try:
        cloud123_storage = file_manager.get_storage("cloud123")
        if not cloud123_storage:
            raise HTTPException(status_code=404, detail="123云盘存储未配置")
        
        success = await cloud123_storage.upload_file(source_path, target_path)
        return {"success": success, "message": "上传成功" if success else "上传失败"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

@router.post("/cloud123/download")
async def cloud123_download_file(
    remote_path: str,
    local_path: str
):
    """从123云盘下载文件"""
    try:
        cloud123_storage = file_manager.get_storage("cloud123")
        if not cloud123_storage:
            raise HTTPException(status_code=404, detail="123云盘存储未配置")
        
        success = await cloud123_storage.download_file(remote_path, local_path)
        return {"success": success, "message": "下载成功" if success else "下载失败"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件下载失败: {str(e)}")

@router.get("/cloud123/space")
async def cloud123_storage_space():
    """获取123云盘存储空间信息"""
    try:
        cloud123_storage = file_manager.get_storage("cloud123")
        if not cloud123_storage:
            raise HTTPException(status_code=404, detail="123云盘存储未配置")
        
        space_info = await cloud123_storage.get_storage_info()
        return space_info
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取存储空间失败: {str(e)}")