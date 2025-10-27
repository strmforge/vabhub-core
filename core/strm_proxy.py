"""
STRM代理服务
处理302跳转和流媒体代理功能
"""

import asyncio
import aiohttp
import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse, RedirectResponse
from urllib.parse import quote, unquote


class STRMProxy:
    """STRM代理服务"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        """获取aiohttp会话"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=3600)  # 1小时超时
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def close_session(self):
        """关闭会话"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def generate_redirect_url(self, 
                            storage_type: str, 
                            file_id: str, 
                            direct_download: bool = False) -> str:
        """
        生成302跳转URL
        
        Args:
            storage_type: 存储类型
            file_id: 文件ID
            direct_download: 是否直接下载
            
        Returns:
            跳转URL
        """
        # 这里需要根据不同的存储类型生成对应的下载URL
        # 实际实现需要调用各个存储适配器的获取下载链接方法
        
        if storage_type == "u115":
            # 115网盘下载URL
            return f"https://proapi.115.com/app/chrome/downurl?pickcode={file_id}"
        elif storage_type == "alipan":
            # 阿里云盘下载URL
            return f"https://api.aliyundrive.com/v2/file/download?file_id={file_id}"
        elif storage_type == "alist":
            # Alist下载URL
            return f"http://your-alist-server.com/d/{file_id}"
        else:
            raise HTTPException(status_code=400, detail=f"不支持的存储类型: {storage_type}")
    
    async def proxy_stream(self, 
                          url: str, 
                          request: Request,
                          chunk_size: int = 8192) -> StreamingResponse:
        """
        代理流媒体请求
        
        Args:
            url: 目标URL
            request: 原始请求
            chunk_size: 块大小
            
        Returns:
            流媒体响应
        """
        try:
            session = await self.get_session()
            
            # 构建请求头
            headers = {}
            if "range" in request.headers:
                headers["range"] = request.headers["range"]
            
            # 发送请求
            async with session.get(url, headers=headers) as response:
                if response.status != 200 and response.status != 206:
                    raise HTTPException(status_code=response.status, detail="远程服务器错误")
                
                # 构建流媒体响应
                return StreamingResponse(
                    self._chunk_generator(response, chunk_size),
                    status_code=response.status,
                    headers=dict(response.headers),
                    media_type=response.headers.get("content-type", "video/mp4")
                )
                
        except aiohttp.ClientError as e:
            self.logger.error(f"代理请求失败: {e}")
            raise HTTPException(status_code=500, detail=f"代理请求失败: {str(e)}")
    
    async def _chunk_generator(self, response: aiohttp.ClientResponse, chunk_size: int):
        """生成数据块"""
        async for chunk in response.content.iter_chunked(chunk_size):
            yield chunk
    
    async def handle_strm_redirect(self, 
                                  storage_type: str, 
                                  file_id: str,
                                  request: Request) -> RedirectResponse:
        """
        处理STRM重定向
        
        Args:
            storage_type: 存储类型
            file_id: 文件ID
            request: 请求对象
            
        Returns:
            重定向响应
        """
        try:
            # 生成下载URL
            download_url = self.generate_redirect_url(storage_type, file_id)
            
            # 记录访问日志
            self.logger.info(f"STRM重定向: {storage_type}/{file_id} -> {download_url}")
            
            # 返回302重定向
            return RedirectResponse(url=download_url, status_code=302)
            
        except Exception as e:
            self.logger.error(f"STRM重定向失败: {e}")
            raise HTTPException(status_code=500, detail=f"重定向失败: {str(e)}")
    
    async def get_file_info(self, storage_type: str, file_id: str) -> Dict[str, Any]:
        """
        获取文件信息
        
        Args:
            storage_type: 存储类型
            file_id: 文件ID
            
        Returns:
            文件信息
        """
        # 这里需要调用对应的存储适配器获取文件信息
        # 实际实现需要集成到存储管理系统中
        
        try:
            # 模拟返回文件信息
            return {
                "storage_type": storage_type,
                "file_id": file_id,
                "file_name": "unknown",
                "size": 0,
                "mime_type": "video/mp4",
                "available": True
            }
        except Exception as e:
            self.logger.error(f"获取文件信息失败: {e}")
            raise HTTPException(status_code=500, detail=f"获取文件信息失败: {str(e)}")
    
    def validate_access_permission(self, storage_type: str, file_id: str) -> bool:
        """
        验证访问权限
        
        Args:
            storage_type: 存储类型
            file_id: 文件ID
            
        Returns:
            是否有权限访问
        """
        # 这里可以实现权限验证逻辑
        # 例如：检查用户权限、文件是否公开等
        
        # 暂时返回True，实际实现需要根据业务需求
        return True


# 全局代理实例
strm_proxy = STRMProxy()