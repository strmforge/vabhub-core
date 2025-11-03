"""
路径管理API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from .path_manager import PathManager, FileOrganizer

router = APIRouter(prefix="/path", tags=["path-management"])

# 数据模型
class SanitizeRequest(BaseModel):
    filename: str

class SanitizeResponse(BaseModel):
    original: str
    sanitized: str

class UniqueFilenameRequest(BaseModel):
    filepath: str

class UniqueFilenameResponse(BaseModel):
    original: str
    unique_path: str

class OrganizeRequest(BaseModel):
    filepath: str
    media_type: str

class OrganizeResponse(BaseModel):
    original: str
    organized_path: str

class SymlinkRequest(BaseModel):
    source: str
    destination: str
    hard_link: bool = False

class SymlinkResponse(BaseModel):
    success: bool
    message: str

class BatchRenameRequest(BaseModel):
    files: List[Dict[str, Any]]
    template: str

class BatchRenameResponse(BaseModel):
    results: List[Dict[str, Any]]

class FindDuplicatesRequest(BaseModel):
    directory: str

class FindDuplicatesResponse(BaseModel):
    duplicates: List[Tuple[str, str]]

class CleanupRequest(BaseModel):
    directory: str

class CleanupResponse(BaseModel):
    removed_dirs: List[str]

class OrganizeMediaRequest(BaseModel):
    source_dir: str
    target_base: str

class OrganizeMediaResponse(BaseModel):
    processed: int
    success: int
    errors: List[Dict[str, str]]
    moved_files: List[Dict[str, str]]

# 初始化路径管理器
path_manager = PathManager("/tmp/vabhub")
file_organizer = FileOrganizer(path_manager)

# 路由
@router.post("/sanitize", response_model=SanitizeResponse)
async def sanitize_filename(request: SanitizeRequest):
    """清理文件名"""
    sanitized = path_manager.sanitize_filename(request.filename)
    return SanitizeResponse(
        original=request.filename,
        sanitized=sanitized
    )

@router.post("/unique", response_model=UniqueFilenameResponse)
async def get_unique_filename(request: UniqueFilenameRequest):
    """获取唯一的文件名"""
    unique_path = path_manager.get_unique_filename(request.filepath)
    return UniqueFilenameResponse(
        original=request.filepath,
        unique_path=str(unique_path)
    )

@router.post("/organize", response_model=OrganizeResponse)
async def organize_file(request: OrganizeRequest):
    """根据媒体类型组织文件"""
    organized_path = path_manager.organize_by_type(
        request.filepath, request.media_type
    )
    return OrganizeResponse(
        original=request.filepath,
        organized_path=str(organized_path)
    )

@router.post("/symlink", response_model=SymlinkResponse)
async def create_symlink(request: SymlinkRequest):
    """创建符号链接或硬链接"""
    success = path_manager.create_symlink(
        request.source,
        request.destination,
        request.hard_link
    )
    
    if success:
        return SymlinkResponse(
            success=True,
            message="链接创建成功"
        )
    else:
        raise HTTPException(status_code=500, detail="链接创建失败")

@router.post("/batch-rename", response_model=BatchRenameResponse)
async def batch_rename(request: BatchRenameRequest):
    """批量重命名文件"""
    results = path_manager.batch_rename(request.files, request.template)
    return BatchRenameResponse(results=results)

@router.post("/find-duplicates", response_model=FindDuplicatesResponse)
async def find_duplicates(request: FindDuplicatesRequest):
    """查找重复文件"""
    duplicates = path_manager.find_duplicates(request.directory)
    return FindDuplicatesResponse(duplicates=duplicates)

@router.post("/cleanup", response_model=CleanupResponse)
async def cleanup_empty_dirs(request: CleanupRequest):
    """清理空目录"""
    removed_dirs = path_manager.cleanup_empty_dirs(request.directory)
    return CleanupResponse(removed_dirs=removed_dirs)

@router.post("/organize-media", response_model=OrganizeMediaResponse)
async def organize_media_files(request: OrganizeMediaRequest):
    """组织媒体文件"""
    results = file_organizer.organize_media_files(
        request.source_dir, request.target_base
    )
    return OrganizeMediaResponse(**results)

# 模板示例端点
@router.get("/templates")
async def get_naming_templates():
    """获取命名模板示例"""
    templates = {
        "movie": "{title}.{year}.{quality}.{codec}",
        "tv_show": "{title}.S{season:02d}E{episode:02d}.{quality}.{codec}",
        "music": "{artist} - {album} - {track:02d} - {title}",
        "simple": "{title}.{extension}"
    }
    return templates

# 路径验证端点
@router.post("/validate")
async def validate_path(filepath: str):
    """验证文件路径"""
    path = Path(filepath)
    
    validation_result = {
        "path": str(path),
        "exists": path.exists(),
        "is_file": path.is_file() if path.exists() else False,
        "is_dir": path.is_dir() if path.exists() else False,
        "size": path.stat().st_size if path.exists() and path.is_file() else 0,
        "parent_exists": path.parent.exists(),
        "is_absolute": path.is_absolute(),
        "sanitized_name": path_manager.sanitize_filename(path.name)
    }
    
    return validation_result