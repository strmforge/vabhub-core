"""
重命名和STRM API路由模块
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List

from .renamer import FileRenamer, STRMGenerator, MediaOrganizer, RenameTemplate
from .auth import get_current_user

router = APIRouter(prefix="/renamer", tags=["Renamer"])


@router.post("/parse-filename")
async def parse_filename(filename: str, current_user: dict = Depends(get_current_user)):
    """解析文件名获取媒体信息"""
    try:
        renamer = FileRenamer(".")
        media_info = renamer.parse_filename(filename)
        return media_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse filename: {e}")


@router.post("/generate-filename")
async def generate_filename(
    filename: str,
    media_info: Dict[str, Any] = None,
    template: str = "{title}.{year}.{SxxExx}.{codec}.{audio}",
    current_user: dict = Depends(get_current_user),
):
    """生成新文件名"""
    try:
        renamer = FileRenamer(".", template)
        new_filename = renamer.generate_new_filename(filename, media_info or {})
        return {"old_filename": filename, "new_filename": new_filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate filename: {e}")


@router.post("/rename-file")
async def rename_file(
    old_path: str,
    new_filename: str,
    strategy: str = "move",
    current_user: dict = Depends(get_current_user),
):
    """重命名文件"""
    try:
        renamer = FileRenamer(".")
        success = renamer.rename_file(old_path, new_filename, strategy)

        if success:
            return {
                "message": "File renamed successfully",
                "old_path": old_path,
                "new_filename": new_filename,
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to rename file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rename file: {e}")


@router.post("/batch-rename")
async def batch_rename(
    directory: str,
    strategy: str = "move",
    current_user: dict = Depends(get_current_user),
):
    """批量重命名目录中的文件"""
    try:
        renamer = FileRenamer(directory)
        results = renamer.batch_rename(directory, strategy)
        return {"directory": directory, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to batch rename: {e}")


@router.post("/generate-strm")
async def generate_strm_file(
    media_info: Dict[str, Any],
    url: str,
    base_path: str = ".",
    current_user: dict = Depends(get_current_user),
):
    """生成STRM文件"""
    try:
        generator = STRMGenerator(base_path)
        strm_path = generator.generate_strm_file(media_info, url)

        # 生成NFO文件
        nfo_path = generator.generate_nfo_file(media_info, strm_path)

        return {"strm_path": strm_path, "nfo_path": nfo_path, "media_info": media_info}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate STRM file: {e}"
        )


@router.post("/organize-media")
async def organize_media_file(
    file_path: str,
    media_info: Dict[str, Any],
    url: str = None,
    generate_strm: bool = False,
    base_path: str = ".",
    template: str = "{title}.{year}.{SxxExx}.{codec}.{audio}",
    current_user: dict = Depends(get_current_user),
):
    """组织单个媒体文件"""
    try:
        organizer = MediaOrganizer(base_path, template)
        results = organizer.organize_media_file(
            file_path, media_info, url, generate_strm
        )
        return {"file_path": file_path, "results": results}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to organize media file: {e}"
        )


@router.post("/scan-organize")
async def scan_and_organize(
    source_dir: str,
    target_dir: str = None,
    template: str = "{title}.{year}.{SxxExx}.{codec}.{audio}",
    current_user: dict = Depends(get_current_user),
):
    """扫描并组织目录中的媒体文件"""
    try:
        organizer = MediaOrganizer(target_dir or source_dir, template)
        results = organizer.scan_and_organize(source_dir, target_dir)
        return {"source_dir": source_dir, "target_dir": target_dir, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scan and organize: {e}")


@router.get("/templates")
async def get_templates(current_user: dict = Depends(get_current_user)):
    """获取可用的重命名模板"""
    templates = [
        {
            "name": "标准模板",
            "template": "{title}.{year}.{SxxExx}.{codec}.{audio}",
            "description": "标准命名格式，包含标题、年份、季集、编码、音频信息",
        },
        {
            "name": "简洁模板",
            "template": "{title}.{year}.{SxxExx}",
            "description": "简洁命名格式，只包含标题、年份、季集信息",
        },
        {
            "name": "详细模板",
            "template": "{title}.{year}.{SxxExx}.{resolution}.{codec}.{audio}.{group}",
            "description": "详细命名格式，包含所有可用信息",
        },
        {
            "name": "Plex模板",
            "template": "{title} ({year})/Season {season}/{title} - S{season}E{episode}",
            "description": "Plex推荐的命名格式，适用于Plex媒体服务器",
        },
    ]

    return {"templates": templates}


@router.post("/validate-template")
async def validate_template(
    template: str, current_user: dict = Depends(get_current_user)
):
    """验证重命名模板"""
    try:
        # 测试模板渲染
        test_template = RenameTemplate(template)
        test_info = {
            "title": "Test Movie",
            "year": "2023",
            "season_episode": "S01E01",
            "codec": "H264",
            "audio": "DTS",
            "resolution": "1080p",
            "release_group": "GROUP",
            "source_type": "BluRay",
        }

        result = test_template.render(test_info)

        return {
            "valid": True,
            "template": template,
            "test_result": result,
            "message": "Template is valid",
        }
    except Exception as e:
        return {
            "valid": False,
            "template": template,
            "error": str(e),
            "message": "Template validation failed",
        }
