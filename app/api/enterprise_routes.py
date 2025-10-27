"""
企业级功能API路由 - 集成变异版本的所有高级功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio

from core.queue_manager import QueueManager, Priority
from core.rate_limiter import RateLimiter
from core.chinese_number import ChineseNumber
from core.template_engine import TemplateEngine
from core.service_discovery import ServiceDiscovery, ServiceStatus
from core.health_check import HealthChecker, HealthStatus
from core.multi_user_auth import MultiUserAuth, UserRole, Permission
from core.history_manager import HistoryManager, OperationType, HistoryStatus

router = APIRouter(prefix="/enterprise", tags=["enterprise"])

# 初始化管理器实例
queue_manager = QueueManager()
rate_limiter = RateLimiter()
chinese_converter = ChineseNumber()
template_engine = TemplateEngine()
service_discovery = ServiceDiscovery()
health_checker = HealthChecker("media-renamer", 8000)
auth_system = MultiUserAuth("your-secret-key-here")
history_manager = HistoryManager()

# 依赖项：获取当前用户
def get_current_user(token: str = Query(..., description="JWT Token")):
    user = auth_system.verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="无效的Token")
    return user

@router.get("/queue/status")
async def get_queue_status(user: Any = Depends(get_current_user)):
    """获取队列状态"""
    if not auth_system.has_permission(user, Permission.READ):
        raise HTTPException(status_code=403, detail="权限不足")
    
    return queue_manager.get_queue_stats()

@router.post("/queue/task")
async def submit_queue_task(
    task_data: Dict[str, Any] = Body(...),
    priority: Priority = Query(Priority.NORMAL),
    user: Any = Depends(get_current_user)
):
    """提交队列任务"""
    if not auth_system.has_permission(user, Permission.WRITE):
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 应用速率限制
    if not rate_limiter.allow_request("queue_submit", user.user_id):
        raise HTTPException(status_code=429, detail="请求过于频繁")
    
    task_id = queue_manager.submit_task(
        task_type=task_data.get("type", "unknown"),
        task_data=task_data,
        priority=priority,
        user_id=user.user_id
    )
    
    # 记录操作历史
    history_manager.record_file_operation(
        user_id=user.user_id,
        operation_type=OperationType.BATCH,
        source_path=f"queue_task_{task_id}",
        details={"task_data": task_data, "priority": priority.value}
    )
    
    return {"task_id": task_id, "status": "submitted"}

@router.get("/rate-limit/status")
async def get_rate_limit_status(user: Any = Depends(get_current_user)):
    """获取速率限制状态"""
    if not auth_system.has_permission(user, Permission.READ):
        raise HTTPException(status_code=403, detail="权限不足")
    
    return rate_limiter.get_rate_limit_stats()

@router.post("/chinese-number/convert")
async def convert_chinese_number(
    text: str = Body(..., embed=True),
    user: Any = Depends(get_current_user)
):
    """中文数字转换"""
    if not auth_system.has_permission(user, Permission.READ):
        raise HTTPException(status_code=403, detail="权限不足")
    
    result = chinese_converter.convert_text(text)
    return {"original": text, "converted": result}

@router.get("/templates")
async def get_templates(user: Any = Depends(get_current_user)):
    """获取模板列表"""
    if not auth_system.has_permission(user, Permission.READ):
        raise HTTPException(status_code=403, detail="权限不足")
    
    return template_engine.get_available_templates()

@router.post("/templates/preview")
async def preview_template(
    template_name: str = Body(..., embed=True),
    variables: Dict[str, Any] = Body({}),
    user: Any = Depends(get_current_user)
):
    """预览模板"""
    if not auth_system.has_permission(user, Permission.READ):
        raise HTTPException(status_code=403, detail="权限不足")
    
    try:
        result = template_engine.render_template(template_name, variables)
        return {"template": template_name, "preview": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/services")
async def get_services(user: Any = Depends(get_current_user)):
    """获取服务列表"""
    if not auth_system.has_permission(user, Permission.READ):
        raise HTTPException(status_code=403, detail="权限不足")
    
    services = await service_discovery.discover_services()
    return {
        "services": [
            {
                "name": s.name,
                "address": s.address,
                "port": s.port,
                "status": s.status.value,
                "tags": s.tags
            }
            for s in services
        ]
    }

@router.get("/health")
async def get_health_status(user: Any = Depends(get_current_user)):
    """获取健康状态"""
    if not auth_system.has_permission(user, Permission.READ):
        raise HTTPException(status_code=403, detail="权限不足")
    
    result = await health_checker.perform_checks()
    return {
        "status": result.status.value,
        "message": result.message,
        "response_time": result.response_time,
        "details": result.details
    }

@router.post("/auth/login")
async def user_login(
    username: str = Body(..., embed=True),
    password: str = Body(..., embed=True)
):
    """用户登录"""
    token = auth_system.authenticate(username, password)
    if not token:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    return {"token": token, "message": "登录成功"}

@router.post("/auth/register")
async def user_register(
    username: str = Body(..., embed=True),
    email: str = Body(..., embed=True),
    password: str = Body(..., embed=True),
    role: UserRole = Body(UserRole.USER),
    user: Any = Depends(get_current_user)
):
    """用户注册（需要管理员权限）"""
    if not auth_system.has_permission(user, Permission.MANAGE_USERS):
        raise HTTPException(status_code=403, detail="权限不足")
    
    new_user = auth_system.create_user(username, email, password, role)
    if not new_user:
        raise HTTPException(status_code=400, detail="用户创建失败")
    
    return {"user_id": new_user.user_id, "message": "用户创建成功"}

@router.get("/history/operations")
async def get_operation_history(
    operation_type: Optional[OperationType] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    user: Any = Depends(get_current_user)
):
    """获取操作历史"""
    if not auth_system.has_permission(user, Permission.READ):
        raise HTTPException(status_code=403, detail="权限不足")
    
    operations = history_manager.get_operation_history(
        user_id=user.user_id,
        operation_type=operation_type,
        start_time=start_time,
        end_time=end_time
    )
    
    return {
        "operations": [
            {
                "operation_id": op.operation_id,
                "type": op.operation_type.value,
                "source_path": op.source_path,
                "target_path": op.target_path,
                "timestamp": op.timestamp,
                "status": op.status.value
            }
            for op in operations
        ]
    }

@router.post("/history/rollback/{operation_id}")
async def rollback_operation(
    operation_id: str,
    user: Any = Depends(get_current_user)
):
    """回滚操作"""
    if not auth_system.has_permission(user, Permission.WRITE):
        raise HTTPException(status_code=403, detail="权限不足")
    
    success = history_manager.rollback_operation(operation_id)
    if not success:
        raise HTTPException(status_code=400, detail="回滚失败")
    
    return {"message": "回滚成功", "operation_id": operation_id}

@router.get("/history/statistics")
async def get_history_statistics(user: Any = Depends(get_current_user)):
    """获取历史统计"""
    if not auth_system.has_permission(user, Permission.READ):
        raise HTTPException(status_code=403, detail="权限不足")
    
    stats = history_manager.get_statistics(user.user_id)
    return stats

@router.get("/dashboard")
async def get_enterprise_dashboard(user: Any = Depends(get_current_user)):
    """获取企业级仪表板"""
    if not auth_system.has_permission(user, Permission.READ):
        raise HTTPException(status_code=403, detail="权限不足")
    
    # 并行获取各种状态信息
    queue_stats = queue_manager.get_queue_stats()
    rate_limit_stats = rate_limiter.get_rate_limit_stats()
    health_result = await health_checker.perform_checks()
    service_stats = service_discovery.get_service_stats()
    user_stats = auth_system.get_user_stats()
    history_stats = history_manager.get_statistics(user.user_id)
    
    return {
        "queue": queue_stats,
        "rate_limit": rate_limit_stats,
        "health": {
            "status": health_result.status.value,
            "message": health_result.message
        },
        "services": service_stats,
        "users": user_stats,
        "history": history_stats,
        "timestamp": datetime.now()
    }

# 启动后台任务
@router.on_event("startup")
async def startup_event():
    """启动后台任务"""
    # 启动健康检查
    asyncio.create_task(health_checker.start_periodic_checks())
    
    # 启动服务发现
    asyncio.create_task(service_discovery.health_check_all())
    
    logger.info("企业级功能后台任务已启动")

@router.on_event("shutdown")
async def shutdown_event():
    """关闭事件"""
    # 清理资源
    await queue_manager.shutdown()
    logger.info("企业级功能已关闭")