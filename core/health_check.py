"""
健康检查系统 - 基于变异版本media-renamer1的成熟实现
提供全面的服务健康监控和故障检测
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import psutil
import aiohttp

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class HealthCheckResult:
    """健康检查结果"""
    component: str
    status: HealthStatus
    message: str
    timestamp: float
    response_time: float
    details: Dict[str, Any]

class HealthChecker:
    """健康检查器"""
    
    def __init__(self, service_name: str, service_port: int):
        self.service_name = service_name
        self.service_port = service_port
        
        # 检查配置
        self.checks: List[Callable] = []
        self.check_interval = 30  # 默认30秒检查一次
        self.timeout = 10  # 默认10秒超时
        
        # 历史记录
        self.history: List[HealthCheckResult] = []
        self.max_history = 100  # 保留最近100条记录
        
        # 状态跟踪
        self.current_status = HealthStatus.UNKNOWN
        self.last_check_time = 0
        self.consecutive_failures = 0
        self.max_consecutive_failures = 3
    
    def add_check(self, check_func: Callable):
        """添加健康检查函数"""
        self.checks.append(check_func)
    
    async def perform_checks(self) -> HealthCheckResult:
        """执行所有健康检查"""
        start_time = time.time()
        
        # 执行系统级检查
        system_result = await self._check_system_health()
        
        # 执行服务级检查
        service_result = await self._check_service_health()
        
        # 执行自定义检查
        custom_results = []
        for check_func in self.checks:
            try:
                result = await check_func()
                custom_results.append(result)
            except Exception as e:
                logger.error(f"自定义健康检查失败: {e}")
                custom_results.append(HealthCheckResult(
                    component="custom_check",
                    status=HealthStatus.UNHEALTHY,
                    message=f"检查异常: {e}",
                    timestamp=time.time(),
                    response_time=0,
                    details={"error": str(e)}
                ))
        
        # 综合评估整体状态
        overall_status = self._evaluate_overall_status([system_result, service_result] + custom_results)
        
        # 构建最终结果
        final_result = HealthCheckResult(
            component="overall",
            status=overall_status,
            message=f"综合健康检查完成",
            timestamp=time.time(),
            response_time=time.time() - start_time,
            details={
                "system": system_result.details,
                "service": service_result.details,
                "custom_checks": [r.details for r in custom_results]
            }
        )
        
        # 更新状态跟踪
        self._update_status_tracking(final_result)
        
        # 保存历史记录
        self.history.append(final_result)
        if len(self.history) > self.max_history:
            self.history.pop(0)
        
        return final_result
    
    async def _check_system_health(self) -> HealthCheckResult:
        """检查系统健康状况"""
        start_time = time.time()
        details = {}
        
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            details["cpu_usage"] = cpu_percent
            
            # 内存使用率
            memory = psutil.virtual_memory()
            details["memory_usage"] = memory.percent
            details["memory_available"] = memory.available
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            details["disk_usage"] = disk.percent
            details["disk_free"] = disk.free
            
            # 网络连接
            net_io = psutil.net_io_counters()
            details["network_bytes_sent"] = net_io.bytes_sent
            details["network_bytes_recv"] = net_io.bytes_recv
            
            # 判断系统状态
            status = HealthStatus.HEALTHY
            message = "系统运行正常"
            
            if cpu_percent > 90:
                status = HealthStatus.DEGRADED
                message = "CPU使用率过高"
            elif memory.percent > 90:
                status = HealthStatus.DEGRADED
                message = "内存使用率过高"
            elif disk.percent > 95:
                status = HealthStatus.DEGRADED
                message = "磁盘空间不足"
                
        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = f"系统检查异常: {e}"
            details["error"] = str(e)
        
        return HealthCheckResult(
            component="system",
            status=status,
            message=message,
            timestamp=time.time(),
            response_time=time.time() - start_time,
            details=details
        )
    
    async def _check_service_health(self) -> HealthCheckResult:
        """检查服务健康状况"""
        start_time = time.time()
        details = {}
        
        try:
            # 检查服务端口是否在监听
            connections = psutil.net_connections()
            service_ports = [conn.laddr.port for conn in connections 
                           if conn.status == 'LISTEN' and conn.laddr.port == self.service_port]
            
            details["port_listening"] = len(service_ports) > 0
            
            # 检查HTTP健康端点
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        f"http://localhost:{self.service_port}/health",
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        details["http_status"] = response.status
                        details["response_time"] = time.time() - start_time
                        
                        if response.status == 200:
                            status = HealthStatus.HEALTHY
                            message = "服务运行正常"
                        else:
                            status = HealthStatus.DEGRADED
                            message = f"HTTP状态异常: {response.status}"
                except asyncio.TimeoutError:
                    status = HealthStatus.UNHEALTHY
                    message = "HTTP请求超时"
                    details["timeout"] = True
                except Exception as e:
                    status = HealthStatus.UNHEALTHY
                    message = f"HTTP请求异常: {e}"
                    details["error"] = str(e)
                    
        except Exception as e:
            status = HealthStatus.UNHEALTHY
            message = f"服务检查异常: {e}"
            details["error"] = str(e)
        
        return HealthCheckResult(
            component="service",
            status=status,
            message=message,
            timestamp=time.time(),
            response_time=time.time() - start_time,
            details=details
        )
    
    def _evaluate_overall_status(self, results: List[HealthCheckResult]) -> HealthStatus:
        """评估整体健康状态"""
        if not results:
            return HealthStatus.UNKNOWN
        
        # 如果有任何UNHEALTHY状态，整体为UNHEALTHY
        if any(r.status == HealthStatus.UNHEALTHY for r in results):
            return HealthStatus.UNHEALTHY
        
        # 如果有任何DEGRADED状态，整体为DEGRADED
        if any(r.status == HealthStatus.DEGRADED for r in results):
            return HealthStatus.DEGRADED
        
        # 如果所有都是HEALTHY，整体为HEALTHY
        if all(r.status == HealthStatus.HEALTHY for r in results):
            return HealthStatus.HEALTHY
        
        return HealthStatus.UNKNOWN
    
    def _update_status_tracking(self, result: HealthCheckResult):
        """更新状态跟踪"""
        self.last_check_time = time.time()
        
        if result.status == HealthStatus.HEALTHY:
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
        
        # 更新当前状态
        if self.consecutive_failures >= self.max_consecutive_failures:
            self.current_status = HealthStatus.UNHEALTHY
        elif result.status == HealthStatus.DEGRADED:
            self.current_status = HealthStatus.DEGRADED
        else:
            self.current_status = result.status
    
    def get_summary(self) -> Dict[str, Any]:
        """获取健康检查摘要"""
        if not self.history:
            return {"status": "unknown", "message": "暂无检查记录"}
        
        latest_result = self.history[-1]
        
        # 计算统计信息
        total_checks = len(self.history)
        healthy_checks = len([r for r in self.history if r.status == HealthStatus.HEALTHY])
        degraded_checks = len([r for r in self.history if r.status == HealthStatus.DEGRADED])
        unhealthy_checks = len([r for r in self.history if r.status == HealthStatus.UNHEALTHY])
        
        # 计算平均响应时间
        avg_response_time = sum(r.response_time for r in self.history) / total_checks
        
        return {
            "service_name": self.service_name,
            "current_status": self.current_status.value,
            "last_check_time": self.last_check_time,
            "consecutive_failures": self.consecutive_failures,
            "latest_result": {
                "status": latest_result.status.value,
                "message": latest_result.message,
                "response_time": latest_result.response_time
            },
            "statistics": {
                "total_checks": total_checks,
                "healthy_checks": healthy_checks,
                "degraded_checks": degraded_checks,
                "unhealthy_checks": unhealthy_checks,
                "success_rate": healthy_checks / total_checks if total_checks > 0 else 0,
                "avg_response_time": avg_response_time
            }
        }
    
    async def start_periodic_checks(self):
        """启动周期性健康检查"""
        while True:
            try:
                await self.perform_checks()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"周期性健康检查异常: {e}")
                await asyncio.sleep(self.check_interval)