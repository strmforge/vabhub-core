"""
站点包管理API
集成MoviePilot规则的站点包管理系统
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
import yaml  # type: ignore
import json
import os
from pathlib import Path

from .site_bundle_manager import SiteBundleManager, SiteBundle

router = APIRouter(prefix="/api/site-bundles", tags=["site-bundles"])

# 依赖注入
site_bundle_manager = SiteBundleManager()


class SiteBundleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    selectors: List[str]
    site_overrides: Optional[dict] = {}
    version: str = "1.0.0"


class SiteBundleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    selectors: Optional[List[str]] = None
    site_overrides: Optional[dict] = None
    version: Optional[str] = None


@router.get("/")
async def list_site_bundles():
    """获取所有站点包"""
    try:
        bundles = site_bundle_manager.get_all_bundles()
        return {"bundles": bundles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取站点包失败: {str(e)}")


@router.get("/{bundle_id}")
async def get_site_bundle(bundle_id: str):
    """获取指定站点包"""
    try:
        bundle = site_bundle_manager.get_bundle(bundle_id)
        if not bundle:
            raise HTTPException(status_code=404, detail="站点包不存在")
        return bundle
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取站点包失败: {str(e)}")


@router.post("/")
async def create_site_bundle(bundle_data: SiteBundleCreate):
    """创建新站点包"""
    try:
        # 将description, site_overrides, version放入meta字典
        meta_data = {
            "description": bundle_data.description,
            "site_overrides": bundle_data.site_overrides,
            "version": bundle_data.version
        }
        
        result = site_bundle_manager.create_bundle(
            name=bundle_data.name,
            selectors=bundle_data.selectors,
            meta=meta_data
        )
        return {"message": "站点包创建成功", "bundle": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建站点包失败: {str(e)}")


@router.put("/{bundle_id}")
async def update_site_bundle(bundle_id: str, bundle_data: SiteBundleUpdate):
    """更新站点包"""
    try:
        existing_bundle = site_bundle_manager.get_bundle(bundle_id)
        if not existing_bundle:
            raise HTTPException(status_code=404, detail="站点包不存在")

        # 准备更新数据
        name = None
        selectors = None
        meta = None
        
        update_data = bundle_data.dict(exclude_unset=True)
        
        if "name" in update_data:
            name = update_data["name"]
        if "selectors" in update_data:
            selectors = update_data["selectors"]
        
        # 如果有需要更新的meta字段
        meta_fields = ["description", "site_overrides", "version"]
        if any(field in update_data for field in meta_fields):
            # 获取现有meta数据
            meta = getattr(existing_bundle, 'meta', {}).copy()
            # 更新meta字段
            for field in meta_fields:
                if field in update_data:
                    meta[field] = update_data[field]
        
        result = site_bundle_manager.update_bundle(
            bundle_id, 
            name=name,
            selectors=selectors,
            meta=meta
        )

        return {"message": "站点包更新成功", "bundle": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新站点包失败: {str(e)}")


@router.delete("/{bundle_id}")
async def delete_site_bundle(bundle_id: str):
    """删除站点包"""
    try:
        existing_bundle = site_bundle_manager.get_bundle(bundle_id)
        if not existing_bundle:
            raise HTTPException(status_code=404, detail="站点包不存在")

        site_bundle_manager.delete_bundle(bundle_id)
        return {"message": "站点包删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除站点包失败: {str(e)}")


@router.post("/import")
async def import_site_bundle(file_content: str):
    """导入站点包配置"""
    try:
        # 尝试解析YAML或JSON
        try:
            config = yaml.safe_load(file_content)
        except:
            config = json.loads(file_content)

        # 验证配置格式
        if not isinstance(config, dict) or "name" not in config:
            raise HTTPException(status_code=400, detail="无效的站点包格式")

        # 将description, site_overrides, version放入meta字典
        meta_data = {
            "description": config.get("description"),
            "site_overrides": config.get("site_overrides", {}),
            "version": config.get("version", "1.0.0")
        }
        
        # 创建站点包
        result = site_bundle_manager.create_bundle(
            name=config.get("name", "Imported Bundle"),
            selectors=config.get("selectors", []),
            meta=meta_data
        )

        return {"message": "站点包导入成功", "bundle": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入站点包失败: {str(e)}")


@router.get("/{bundle_id}/export")
async def export_site_bundle(bundle_id: str):
    """导出站点包配置"""
    try:
        bundle = site_bundle_manager.get_bundle(bundle_id)
        if not bundle:
            raise HTTPException(status_code=404, detail="站点包不存在")

        # 从meta字典中获取相关信息
        meta = getattr(bundle, 'meta', {})
        
        # 转换为YAML格式
        export_data = {
            "name": bundle.name,
            "description": meta.get("description"),
            "selectors": bundle.selectors,
            "site_overrides": meta.get("site_overrides", {}),
            "version": meta.get("version", "1.0.0"),
        }

        yaml_content = yaml.dump(
            export_data, default_flow_style=False, allow_unicode=True
        )
        return {"content": yaml_content, "format": "yaml"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出站点包失败: {str(e)}")
