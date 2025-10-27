"""
服务发现系统 - 基于Consul的服务注册和发现
继承自变异版本media-renamer1的成熟实现
"""

import asyncio
import json
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import aiohttp
import requests

logger = logging.getLogger(__name__)

class ServiceStatus(Enum):
    """服务状态枚举"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class ServiceInfo:
    """服务信息"""
    name: str
    address: str
    port: int
    tags: List[str]
    status: ServiceStatus
    last_check: float
    metadata: Dict[str, Any]

class ServiceDiscovery:
    """服务发现系统"""
    
    def __init__(self, consul_host: str = "localhost", consul_port: int = 8500):
        self.consul_host = consul_host
        self.consul_port = consul_port
        self.base_url = f"http://{consul_host}:{consul_port}"
        
        # 服务缓存
        self.services: Dict[str, ServiceInfo] = {}
        self.last_update = 0
        self.cache_ttl = 30  # 缓存30秒
        
        # 健康检查配置
        self.health_check_interval = 10
        self.health_check_timeout = 5
    
    async def register_service(self, name: str, address: str, port: int, 
                              tags: List[str] = None, metadata: Dict[str, Any] = None):
        """注册服务到Consul"""
        if tags is None:
            tags = []
        if metadata is None:
            metadata = {}
            
        service_data = {
            "ID": f"{name}-{address}:{port}",
            "Name": name,
            "Address": address,
            "Port": port,
            "Tags": tags,
            "Meta": metadata,
            "Check": {
                "DeregisterCriticalServiceAfter": "90m",
                "HTTP": f"http://{address}:{port}/health",
                "Interval": "10s",
                "Timeout": "5s"
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.put(
                    f"{self.base_url}/v1/agent/service/register",
                    json=service_data
                ) as response:
                    if response.status == 200:
                        logger.info(f"服务 {name} 注册成功")
                        return True
                    else:
                        logger.error(f"服务 {name} 注册失败: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"服务注册异常: {e}")
            return False
    
    async def deregister_service(self, service_id: str):
        """从Consul注销服务"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.put(
                    f"{self.base_url}/v1/agent/service/deregister/{service_id}"
                ) as response:
                    if response.status == 200:
                        logger.info(f"服务 {service_id} 注销成功")
                        return True
                    else:
                        logger.error(f"服务 {service_id} 注销失败: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"服务注销异常: {e}")
            return False
    
    async def discover_services(self, service_name: str = None) -> List[ServiceInfo]:
        """发现服务"""
        # 检查缓存
        current_time = time.time()
        if current_time - self.last_update < self.cache_ttl and not service_name:
            return list(self.services.values())
        
        try:
            url = f"{self.base_url}/v1/agent/services"
            if service_name:
                url = f"{self.base_url}/v1/health/service/{service_name}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        services = self._parse_services(data, service_name)
                        
                        # 更新缓存
                        if not service_name:
                            self.services = {s.name: s for s in services}
                            self.last_update = current_time
                        
                        return services
                    else:
                        logger.error(f"服务发现失败: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"服务发现异常: {e}")
            return []
    
    def _parse_services(self, data: Any, service_name: str = None) -> List[ServiceInfo]:
        """解析服务数据"""
        services = []
        
        if service_name:
            # 健康检查端点返回的数据格式
            for service_data in data:
                service = service_data.get('Service', {})
                checks = service_data.get('Checks', [])
                
                # 确定服务状态
                status = ServiceStatus.UNKNOWN
                for check in checks:
                    if check.get('Status') == 'passing':
                        status = ServiceStatus.HEALTHY
                    elif check.get('Status') == 'critical':
                        status = ServiceStatus.UNHEALTHY
                
                service_info = ServiceInfo(
                    name=service.get('Service', ''),
                    address=service.get('Address', ''),
                    port=service.get('Port', 0),
                    tags=service.get('Tags', []),
                    status=status,
                    last_check=time.time(),
                    metadata=service.get('Meta', {})
                )
                services.append(service_info)
        else:
            # 服务列表端点返回的数据格式
            for service_id, service_data in data.items():
                service_info = ServiceInfo(
                    name=service_data.get('Service', ''),
                    address=service_data.get('Address', ''),
                    port=service_data.get('Port', 0),
                    tags=service_data.get('Tags', []),
                    status=ServiceStatus.UNKNOWN,  # 需要单独的健康检查
                    last_check=time.time(),
                    metadata=service_data.get('Meta', {})
                )
                services.append(service_info)
        
        return services
    
    async def get_healthy_service(self, service_name: str) -> Optional[ServiceInfo]:
        """获取健康的服务实例"""
        services = await self.discover_services(service_name)
        healthy_services = [s for s in services if s.status == ServiceStatus.HEALTHY]
        
        if healthy_services:
            # 简单的负载均衡：轮询选择
            return healthy_services[0]
        return None
    
    async def health_check_all(self):
        """对所有服务进行健康检查"""
        services = await self.discover_services()
        
        for service in services:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"http://{service.address}:{service.port}/health",
                        timeout=aiohttp.ClientTimeout(total=self.health_check_timeout)
                    ) as response:
                        if response.status == 200:
                            service.status = ServiceStatus.HEALTHY
                        else:
                            service.status = ServiceStatus.UNHEALTHY
            except Exception as e:
                logger.warning(f"服务 {service.name} 健康检查失败: {e}")
                service.status = ServiceStatus.UNHEALTHY
            
            service.last_check = time.time()
    
    def get_service_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        total_services = len(self.services)
        healthy_count = len([s for s in self.services.values() if s.status == ServiceStatus.HEALTHY])
        unhealthy_count = len([s for s in self.services.values() if s.status == ServiceStatus.UNHEALTHY])
        
        return {
            "total_services": total_services,
            "healthy_services": healthy_count,
            "unhealthy_services": unhealthy_count,
            "health_ratio": healthy_count / total_services if total_services > 0 else 0,
            "last_update": self.last_update
        }