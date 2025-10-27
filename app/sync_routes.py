"""
同步管理API路由
集成MediaMaster的多设备同步精华功能
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any

from core.sync_engine import SyncEngine

router = APIRouter(prefix="/sync", tags=["sync"])

# 全局同步引擎实例
sync_engine = SyncEngine()


class DeviceConfig(BaseModel):
    """设备配置模型"""
    name: str = Field(..., description="设备名称")
    type: str = Field(..., description="设备类型: nas, pc, mobile, cloud")
    address: str = Field(..., description="设备地址/IP")
    port: int = Field(..., description="设备端口")
    username: Optional[str] = Field(None, description="用户名")
    password: Optional[str] = Field(None, description="密码")
    sync_path: str = Field(..., description="同步路径")


class SyncRule(BaseModel):
    """同步规则模型"""
    name: str = Field(..., description="规则名称")
    source_device: str = Field(..., description="源设备")
    target_devices: List[str] = Field(..., description="目标设备列表")
    file_patterns: List[str] = Field(..., description="文件匹配模式")
    sync_mode: str = Field(..., description="同步模式: one_way, two_way")
    conflict_resolution: str = Field(..., description="冲突解决策略: source, target, newer")


class SyncResponse(BaseModel):
    """同步响应模型"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


@router.on_event("startup")
async def startup_event():
    """应用启动时初始化同步引擎"""
    await sync_engine.initialize()


@router.get("/status", response_model=SyncResponse)
async def get_sync_status():
    """获取同步系统状态"""
    try:
        status = sync_engine.get_status()
        return SyncResponse(
            success=True,
            message="同步系统状态获取成功",
            data=status
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.post("/devices", response_model=SyncResponse)
async def add_device(device_config: DeviceConfig):
    """添加同步设备"""
    try:
        success = sync_engine.add_device(
            name=device_config.name,
            device_type=device_config.type,
            address=device_config.address,
            port=device_config.port,
            username=device_config.username,
            password=device_config.password,
            sync_path=device_config.sync_path
        )
        
        if success:
            return SyncResponse(
                success=True,
                message=f"设备 {device_config.name} 添加成功",
                data={"device_name": device_config.name}
            )
        else:
            return SyncResponse(
                success=False,
                message=f"设备 {device_config.name} 添加失败",
                data={"device_name": device_config.name}
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加设备失败: {str(e)}")


@router.get("/devices", response_model=SyncResponse)
async def list_devices():
    """获取所有同步设备列表"""
    try:
        devices = sync_engine.list_devices()
        return SyncResponse(
            success=True,
            message="设备列表获取成功",
            data={"devices": devices}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取设备列表失败: {str(e)}")


@router.delete("/devices/{device_name}", response_model=SyncResponse)
async def remove_device(device_name: str):
    """移除同步设备"""
    try:
        success = sync_engine.remove_device(device_name)
        if success:
            return SyncResponse(
                success=True,
                message=f"设备 {device_name} 移除成功"
            )
        else:
            return SyncResponse(
                success=False,
                message=f"设备 {device_name} 不存在"
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"移除设备失败: {str(e)}")


@router.post("/rules", response_model=SyncResponse)
async def create_sync_rule(sync_rule: SyncRule):
    """创建同步规则"""
    try:
        success = sync_engine.add_sync_rule(
            name=sync_rule.name,
            source_device=sync_rule.source_device,
            target_devices=sync_rule.target_devices,
            file_patterns=sync_rule.file_patterns,
            sync_mode=sync_rule.sync_mode,
            conflict_resolution=sync_rule.conflict_resolution
        )
        
        if success:
            return SyncResponse(
                success=True,
                message=f"同步规则 {sync_rule.name} 创建成功",
                data={"rule_name": sync_rule.name}
            )
        else:
            return SyncResponse(
                success=False,
                message=f"同步规则 {sync_rule.name} 创建失败",
                data={"rule_name": sync_rule.name}
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建同步规则失败: {str(e)}")


@router.get("/rules", response_model=SyncResponse)
async def list_sync_rules():
    """获取所有同步规则列表"""
    try:
        rules = sync_engine.list_sync_rules()
        return SyncResponse(
            success=True,
            message="同步规则列表获取成功",
            data={"rules": rules}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取同步规则列表失败: {str(e)}")


@router.delete("/rules/{rule_name}", response_model=SyncResponse)
async def delete_sync_rule(rule_name: str):
    """删除同步规则"""
    try:
        success = sync_engine.remove_sync_rule(rule_name)
        if success:
            return SyncResponse(
                success=True,
                message=f"同步规则 {rule_name} 删除成功"
            )
        else:
            return SyncResponse(
                success=False,
                message=f"同步规则 {rule_name} 不存在"
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除同步规则失败: {str(e)}")


@router.post("/sync/start", response_model=SyncResponse)
async def start_sync(background_tasks: BackgroundTasks):
    """启动同步任务"""
    try:
        background_tasks.add_task(sync_engine.start_sync)
        return SyncResponse(
            success=True,
            message="同步任务已启动"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动同步失败: {str(e)}")


@router.post("/sync/stop", response_model=SyncResponse)
async def stop_sync():
    """停止同步任务"""
    try:
        sync_engine.stop_sync()
        return SyncResponse(
            success=True,
            message="同步任务已停止"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止同步失败: {str(e)}")


@router.get("/jobs", response_model=SyncResponse)
async def get_sync_jobs():
    """获取当前同步任务列表"""
    try:
        jobs = sync_engine.get_sync_jobs()
        return SyncResponse(
            success=True,
            message="同步任务列表获取成功",
            data={"jobs": jobs}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取同步任务列表失败: {str(e)}")


@router.post("/jobs/{job_id}/pause", response_model=SyncResponse)
async def pause_sync_job(job_id: str):
    """暂停同步任务"""
    try:
        success = sync_engine.pause_sync_job(job_id)
        if success:
            return SyncResponse(
                success=True,
                message=f"同步任务 {job_id} 已暂停"
            )
        else:
            return SyncResponse(
                success=False,
                message=f"同步任务 {job_id} 暂停失败"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"暂停同步任务失败: {str(e)}")


@router.post("/jobs/{job_id}/resume", response_model=SyncResponse)
async def resume_sync_job(job_id: str):
    """恢复同步任务"""
    try:
        success = sync_engine.resume_sync_job(job_id)
        if success:
            return SyncResponse(
                success=True,
                message=f"同步任务 {job_id} 已恢复"
            )
        else:
            return SyncResponse(
                success=False,
                message=f"同步任务 {job_id} 恢复失败"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"恢复同步任务失败: {str(e)}")


@router.get("/stats", response_model=SyncResponse)
async def get_sync_stats():
    """获取同步统计信息"""
    try:
        stats = sync_engine.get_sync_stats()
        return SyncResponse(
            success=True,
            message="同步统计信息获取成功",
            data={"stats": stats}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取同步统计失败: {str(e)}")


@router.post("/cleanup", response_model=SyncResponse)
async def cleanup_sync_data():
    """清理同步数据"""
    try:
        sync_engine.cleanup()
        return SyncResponse(
            success=True,
            message="同步数据清理完成"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理同步数据失败: {str(e)}")