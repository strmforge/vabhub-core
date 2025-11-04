"""
文件整理系统API路由模块
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pathlib import Path

from .file_organizer import FileOrganizer, OrganizationRule, FileAction, MediaType
from .auth import get_current_user

router = APIRouter(prefix="/file-organizer", tags=["File Organizer"])

# 全局文件整理器实例
file_organizer = None


def get_file_organizer():
    """获取文件整理器实例"""
    global file_organizer
    if file_organizer is None:
        # 使用当前工作目录作为基础路径
        base_path = Path.cwd()
        file_organizer = FileOrganizer(str(base_path))
    return file_organizer


@router.post("/scan", response_model=List[Dict[str, Any]])
async def scan_directory(
    directory: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    organizer: FileOrganizer = Depends(get_file_organizer),
):
    """扫描目录获取文件信息"""
    try:
        file_infos = organizer.scan_directory(str(directory) if directory else None)

        result = []
        for file_info in file_infos:
            result.append(
                {
                    "path": file_info.path,
                    "name": file_info.name,
                    "size": file_info.size,
                    "modified_time": file_info.modified_time,
                    "media_type": file_info.media_type.value,
                    "metadata": file_info.metadata,
                }
            )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scan directory: {e}")


@router.post("/preview", response_model=List[Dict[str, Any]])
async def preview_organization(
    directory: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    organizer: FileOrganizer = Depends(get_file_organizer),
):
    """预览整理结果"""
    try:
        previews = organizer.preview_organization(directory)
        return previews

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to preview organization: {e}"
        )


@router.post("/organize", response_model=List[Dict[str, Any]])
async def organize_files(
    directory: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    organizer: FileOrganizer = Depends(get_file_organizer),
):
    """整理文件"""
    try:
        results = organizer.batch_organize(directory)
        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to organize files: {e}")


@router.post("/organize-file", response_model=Dict[str, Any])
async def organize_single_file(
    file_path: str,
    current_user: dict = Depends(get_current_user),
    organizer: FileOrganizer = Depends(get_file_organizer),
):
    """整理单个文件"""
    try:
        # 扫描文件信息
        file_infos = organizer.scan_directory(str(Path(file_path).parent))
        target_file_info = None

        for file_info in file_infos:
            if file_info.path == file_path:
                target_file_info = file_info
                break

        if not target_file_info:
            raise HTTPException(status_code=404, detail="File not found")

        # 整理文件
        result = organizer.organize_file(target_file_info)
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to organize file: {e}")


@router.get("/rules", response_model=List[Dict[str, Any]])
async def get_rules(
    current_user: dict = Depends(get_current_user),
    organizer: FileOrganizer = Depends(get_file_organizer),
):
    """获取所有整理规则"""
    try:
        rules_data = []
        for rule in organizer.rules:
            rules_data.append(
                {
                    "name": rule.name,
                    "pattern": rule.pattern,
                    "target_template": rule.target_template,
                    "action": rule.action.value,
                    "enabled": rule.enabled,
                    "priority": rule.priority,
                }
            )

        return rules_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get rules: {e}")


@router.post("/rules", response_model=Dict[str, Any])
async def add_rule(
    rule_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
    organizer: FileOrganizer = Depends(get_file_organizer),
):
    """添加整理规则"""
    try:
        rule = OrganizationRule(
            name=rule_data["name"],
            pattern=rule_data["pattern"],
            target_template=rule_data["target_template"],
            action=FileAction(rule_data.get("action", "move")),
            enabled=rule_data.get("enabled", True),
            priority=rule_data.get("priority", 1),
        )

        organizer.add_rule(rule)

        return {
            "message": "Rule added successfully",
            "rule": {
                "name": rule.name,
                "pattern": rule.pattern,
                "target_template": rule.target_template,
                "action": rule.action.value,
                "enabled": rule.enabled,
                "priority": rule.priority,
            },
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to add rule: {e}")


@router.delete("/rules/{rule_name}", response_model=Dict[str, Any])
async def remove_rule(
    rule_name: str,
    current_user: dict = Depends(get_current_user),
    organizer: FileOrganizer = Depends(get_file_organizer),
):
    """删除整理规则"""
    try:
        success = organizer.remove_rule(rule_name)
        if not success:
            raise HTTPException(status_code=404, detail="Rule not found")

        return {"message": "Rule removed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove rule: {e}")


@router.get("/validate-rules", response_model=List[Dict[str, Any]])
async def validate_rules(
    current_user: dict = Depends(get_current_user),
    organizer: FileOrganizer = Depends(get_file_organizer),
):
    """验证所有规则的有效性"""
    try:
        validation_results = organizer.validate_rules()
        return validation_results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate rules: {e}")


@router.get("/media-types", response_model=List[Dict[str, Any]])
async def get_media_types():
    """获取支持的媒体类型"""
    return [
        {"value": "movie", "label": "电影", "description": "电影类型"},
        {"value": "tv", "label": "电视剧", "description": "电视剧类型"},
        {"value": "music", "label": "音乐", "description": "音乐类型"},
        {"value": "anime", "label": "动漫", "description": "动漫类型"},
        {"value": "unknown", "label": "未知", "description": "未知类型"},
    ]


@router.get("/file-actions", response_model=List[Dict[str, Any]])
async def get_file_actions():
    """获取支持的文件操作类型"""
    return [
        {"value": "move", "label": "移动", "description": "移动文件到目标位置"},
        {"value": "copy", "label": "复制", "description": "复制文件到目标位置"},
        {"value": "link", "label": "链接", "description": "创建符号链接"},
        {"value": "rename", "label": "重命名", "description": "重命名文件"},
    ]


@router.get("/template-variables", response_model=List[Dict[str, Any]])
async def get_template_variables():
    """获取模板变量"""
    return [
        {"variable": "{title}", "description": "媒体标题"},
        {"variable": "{year}", "description": "发布年份"},
        {"variable": "{season}", "description": "季数"},
        {"variable": "{episode}", "description": "集数"},
        {"variable": "{ext}", "description": "文件扩展名"},
        {"variable": "{resolution}", "description": "分辨率"},
        {"variable": "{codec}", "description": "视频编码"},
        {"variable": "{audio}", "description": "音频编码"},
        {"variable": "{release_group}", "description": "发布组"},
        {"variable": "{artist}", "description": "艺术家（音乐）"},
        {"variable": "{album}", "description": "专辑（音乐）"},
        {"variable": "{track_number}", "description": "音轨号（音乐）"},
    ]


@router.post("/test-template", response_model=Dict[str, Any])
async def test_template(
    template: str,
    test_data: Optional[Dict[str, Any]] = None,
    current_user: dict = Depends(get_current_user),
):
    """测试模板渲染"""
    try:
        # 默认测试数据
        if test_data is None:
            test_data = {
                "title": "Test Movie",
                "year": "2023",
                "season": 1,
                "episode": 1,
                "ext": "mp4",
                "resolution": "1080p",
                "codec": "H264",
                "audio": "DTS",
                "release_group": "TEST",
            }

        # 渲染模板
        result = template
        for key, value in test_data.items():
            placeholder = f"{{{key}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))

        # 清理路径
        result = result.replace("//", "/")

        return {
            "template": template,
            "test_data": test_data,
            "result": result,
            "valid": True,
        }

    except Exception as e:
        return {
            "template": template,
            "test_data": test_data,
            "result": "",
            "valid": False,
            "error": str(e),
        }


@router.get("/statistics", response_model=Dict[str, Any])
async def get_statistics(
    directory: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    organizer: FileOrganizer = Depends(get_file_organizer),
):
    """获取目录统计信息"""
    try:
        file_infos = organizer.scan_directory(str(directory) if directory else None)

        # 统计信息
        total_files = len(file_infos)
        total_size = sum(f.size for f in file_infos)

        # 按媒体类型统计
        media_type_stats = {}
        for file_info in file_infos:
            media_type = file_info.media_type.value
            if media_type not in media_type_stats:
                media_type_stats[media_type] = {"count": 0, "size": 0}
            media_type_stats[media_type]["count"] += 1
            media_type_stats[media_type]["size"] += file_info.size

        # 按扩展名统计
        extension_stats = {}
        for file_info in file_infos:
            ext = Path(file_info.path).suffix.lower()
            if ext not in extension_stats:
                extension_stats[ext] = {"count": 0, "size": 0}
            extension_stats[ext]["count"] += 1
            extension_stats[ext]["size"] += file_info.size

        return {
            "total_files": total_files,
            "total_size": total_size,
            "media_type_stats": media_type_stats,
            "extension_stats": extension_stats,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {e}")
