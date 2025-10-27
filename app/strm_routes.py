"""
STRM文件管理API路由
处理STRM文件生成、管理和302跳转功能
"""

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pathlib import Path
import os

from core.strm_generator import STRMGenerator, STRMType
from core.strm_proxy import strm_proxy
from core.file_manager import FileManager

# 创建STRM路由器
strm_router = APIRouter(prefix="/api/strm", tags=["STRM管理"])


class STRMGenerateRequest(BaseModel):
    """STRM生成请求"""
    storage_type: str
    file_ids: List[str]
    output_dir: str
    organize_by_type: bool = True
    strm_type: str = "proxy"


class STRMValidateRequest(BaseModel):
    """STRM验证请求"""
    strm_paths: List[str]


class STRMRepairRequest(BaseModel):
    """STRM修复请求"""
    strm_path: str
    new_url: Optional[str] = None


class STRMResponse(BaseModel):
    """STRM响应"""
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None


@strm_router.post("/generate", response_model=STRMResponse)
async def generate_strm_files(request: STRMGenerateRequest):
    """
    生成STRM文件
    """
    try:
        # 获取文件管理器实例
        file_manager = FileManager()
        
        # 获取文件信息
        file_items = []
        for file_id in request.file_ids:
            # 这里需要根据存储类型和文件ID获取文件信息
            # 简化实现：创建虚拟文件项
            file_item = {
                "storage_type": request.storage_type,
                "file_id": file_id,
                "file_name": f"file_{file_id}.mp4",  # 简化文件名
                "metadata": {
                    "media_type": "movie"  # 简化媒体类型
                }
            }
            file_items.append(file_item)
        
        # 创建STRM生成器
        strm_gen = STRMGenerator()
        
        # 批量生成STRM文件
        results = strm_gen.batch_generate_strm(
            file_items, request.output_dir, request.organize_by_type
        )
        
        return STRMResponse(
            status="success",
            message=f"成功生成 {results['success']} 个STRM文件，失败 {results['failed']} 个",
            data=results
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成STRM文件失败: {str(e)}")


@strm_router.post("/validate", response_model=STRMResponse)
async def validate_strm_files(request: STRMValidateRequest):
    """
    验证STRM文件
    """
    try:
        strm_gen = STRMGenerator()
        validation_results = []
        
        for strm_path in request.strm_paths:
            result = strm_gen.validate_strm_file(strm_path)
            validation_results.append({
                "strm_path": strm_path,
                "valid": result["valid"],
                "error": result.get("error"),
                "url": result.get("url")
            })
        
        valid_count = sum(1 for r in validation_results if r["valid"])
        invalid_count = len(validation_results) - valid_count
        
        return STRMResponse(
            status="success",
            message=f"验证完成：有效 {valid_count} 个，无效 {invalid_count} 个",
            data={"results": validation_results}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"验证STRM文件失败: {str(e)}")


@strm_router.post("/repair", response_model=STRMResponse)
async def repair_strm_file(request: STRMRepairRequest):
    """
    修复STRM文件
    """
    try:
        strm_gen = STRMGenerator()
        
        success = strm_gen.repair_strm_file(request.strm_path, request.new_url)
        
        if success:
            return STRMResponse(
                status="success",
                message="STRM文件修复成功"
            )
        else:
            return STRMResponse(
                status="error",
                message="STRM文件修复失败"
            )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"修复STRM文件失败: {str(e)}")


@strm_router.get("/stream/{storage_type}/{file_id}")
async def stream_file(storage_type: str, file_id: str, request: Request):
    """
    流媒体文件重定向（302跳转）
    """
    try:
        # 验证访问权限
        if not strm_proxy.validate_access_permission(storage_type, file_id):
            raise HTTPException(status_code=403, detail="无访问权限")
        
        # 处理重定向
        return await strm_proxy.handle_strm_redirect(storage_type, file_id, request)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"流媒体重定向失败: {str(e)}")


@strm_router.get("/proxy")
async def proxy_stream(url: str, request: Request):
    """
    代理流媒体请求
    """
    try:
        # 代理流媒体请求
        return await strm_proxy.proxy_stream(url, request)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"代理流媒体失败: {str(e)}")


@strm_router.get("/info/{storage_type}/{file_id}", response_model=STRMResponse)
async def get_file_info(storage_type: str, file_id: str):
    """
    获取文件信息
    """
    try:
        file_info = await strm_proxy.get_file_info(storage_type, file_id)
        
        return STRMResponse(
            status="success",
            message="文件信息获取成功",
            data=file_info
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件信息失败: {str(e)}")


@strm_router.get("/list")
async def list_strm_files(directory: str = ""):
    """
    列出指定目录下的STRM文件
    """
    try:
        base_dir = Path(directory) if directory else Path("./strm_files")
        
        if not base_dir.exists():
            return STRMResponse(
                status="error",
                message="目录不存在",
                data={"files": []}
            )
        
        strm_files = []
        strm_gen = STRMGenerator()
        
        # 递归查找STRM文件
        for file_path in base_dir.rglob("*.strm"):
            validation = strm_gen.validate_strm_file(str(file_path))
            
            strm_files.append({
                "path": str(file_path),
                "name": file_path.name,
                "valid": validation["valid"],
                "url": validation.get("url"),
                "error": validation.get("error")
            })
        
        return STRMResponse(
            status="success",
            message=f"找到 {len(strm_files)} 个STRM文件",
            data={"files": strm_files}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"列出STRM文件失败: {str(e)}")


@strm_router.delete("/delete")
async def delete_strm_file(file_path: str):
    """
    删除STRM文件
    """
    try:
        path = Path(file_path)
        
        if not path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        if path.suffix != ".strm":
            raise HTTPException(status_code=400, detail="只能删除STRM文件")
        
        path.unlink()
        
        return STRMResponse(
            status="success",
            message="STRM文件删除成功"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除STRM文件失败: {str(e)}")