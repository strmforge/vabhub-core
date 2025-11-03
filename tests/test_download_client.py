"""
DownloadClient测试用例
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from core.download_client import (
    DownloadClientFactory, DownloadClientConfig, 
    DownloadClientType, TorrentStatus, QbittorrentClient
)
from core.download_manager import DownloadManager


class TestDownloadClient:
    """DownloadClient测试类"""
    
    @pytest.fixture
    def qbittorrent_config(self):
        """qBittorrent配置fixture"""
        return DownloadClientConfig(
            client_type=DownloadClientType.QBITTORRENT,
            host="localhost",
            port=8080,
            username="admin",
            password="adminadmin"
        )
    
    @pytest.fixture
    def download_manager_instance(self):
        """下载管理器实例fixture"""
        return DownloadManager()
    
    def test_download_client_factory(self, qbittorrent_config):
        """测试下载器工厂"""
        # 测试创建qBittorrent客户端
        client = DownloadClientFactory.create_client(qbittorrent_config)
        assert isinstance(client, QbittorrentClient)
        assert client.config.client_type == DownloadClientType.QBITTORRENT
        
        # 测试不支持的客户端类型
        invalid_config = DownloadClientConfig(
            client_type=DownloadClientType.TRANSMISSION,
            host="localhost",
            port=9091
        )
        with pytest.raises(NotImplementedError):
            DownloadClientFactory.create_client(invalid_config)
    
    @pytest.mark.asyncio
    async def test_qbittorrent_client_connection(self, qbittorrent_config):
        """测试qBittorrent客户端连接"""
        with patch('core.download_client.Client') as mock_client_class:
            # 模拟客户端
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.auth_log_in.return_value = None
            
            client = QbittorrentClient(qbittorrent_config)
            
            # 测试连接成功
            connected = await client.connect()
            assert connected is True
            assert client.is_connected is True
            
            # 测试断开连接
            await client.disconnect()
            assert client.is_connected is False
    
    @pytest.mark.asyncio
    async def test_qbittorrent_client_add_torrent(self, qbittorrent_config):
        """测试qBittorrent添加种子"""
        with patch('core.download_client.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.auth_log_in.return_value = None
            mock_client.torrents_add.return_value = None
            
            client = QbittorrentClient(qbittorrent_config)
            await client.connect()
            
            # 测试添加磁力链接
            success = await client.add_torrent("magnet:?xt=urn:btih:test123")
            assert success is True
            
            # 测试添加种子文件
            torrent_data = b"d8:announce"
            success = await client.add_torrent(torrent_data)
            assert success is True
    
    @pytest.mark.asyncio
    async def test_qbittorrent_client_torrent_operations(self, qbittorrent_config):
        """测试qBittorrent种子操作"""
        with patch('core.download_client.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.auth_log_in.return_value = None
            
            # 模拟种子信息
            mock_torrent = Mock()
            mock_torrent.hash = "test_hash"
            mock_torrent.name = "Test Torrent"
            mock_torrent.size = 1024 * 1024 * 1024  # 1GB
            mock_torrent.progress = 0.5
            mock_torrent.state = "downloading"
            mock_torrent.dlspeed = 1024 * 1024  # 1MB/s
            mock_torrent.upspeed = 512 * 1024  # 512KB/s
            mock_torrent.ratio = 0.0
            mock_torrent.eta = 3600  # 1小时
            mock_torrent.save_path = "/downloads"
            mock_torrent.category = "movies"
            mock_torrent.added_on = 1234567890
            
            mock_client.torrents_info.return_value = [mock_torrent]
            
            client = QbittorrentClient(qbittorrent_config)
            await client.connect()
            
            # 测试获取种子列表
            torrents = await client.get_torrents()
            assert len(torrents) == 1
            assert torrents[0].hash == "test_hash"
            assert torrents[0].status == TorrentStatus.DOWNLOADING
            
            # 测试获取单个种子
            torrent = await client.get_torrent("test_hash")
            assert torrent is not None
            assert torrent.hash == "test_hash"
    
    @pytest.mark.asyncio
    async def test_download_manager_add_client(self, download_manager_instance):
        """测试下载管理器添加客户端"""
        with patch('core.download_client.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.auth_log_in.return_value = None
            mock_client.app_version.return_value = "4.6.0"
            
            # 测试添加客户端
            success = await download_manager_instance.add_client(
                client_id="qb_test",
                client_type=DownloadClientType.QBITTORRENT,
                host="localhost",
                port=8080,
                username="admin",
                password="adminadmin",
                set_as_default=True
            )
            
            assert success is True
            assert "qb_test" in download_manager_instance._clients
            assert download_manager_instance._default_client == "qb_test"
    
    @pytest.mark.asyncio
    async def test_download_manager_torrent_operations(self, download_manager_instance):
        """测试下载管理器种子操作"""
        with patch('core.download_client.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.auth_log_in.return_value = None
            mock_client.torrents_add.return_value = None
            mock_client.torrents_pause.return_value = None
            mock_client.torrents_resume.return_value = None
            mock_client.torrents_delete.return_value = None
            
            # 添加客户端
            await download_manager_instance.add_client(
                client_id="qb_test",
                client_type=DownloadClientType.QBITTORRENT,
                host="localhost",
                port=8080
            )
            
            # 测试添加种子
            success = await download_manager_instance.add_torrent(
                torrent="magnet:?xt=urn:btih:test123",
                client_id="qb_test"
            )
            assert success is True
            
            # 测试暂停种子
            success = await download_manager_instance.pause_torrent(
                torrent_hash="test_hash",
                client_id="qb_test"
            )
            assert success is True
            
            # 测试恢复种子
            success = await download_manager_instance.resume_torrent(
                torrent_hash="test_hash",
                client_id="qb_test"
            )
            assert success is True
            
            # 测试删除种子
            success = await download_manager_instance.remove_torrent(
                torrent_hash="test_hash",
                client_id="qb_test"
            )
            assert success is True
    
    def test_torrent_status_mapping(self):
        """测试种子状态映射"""
        client = QbittorrentClient(DownloadClientConfig(
            client_type=DownloadClientType.QBITTORRENT,
            host="localhost",
            port=8080
        ))
        
        # 测试各种状态映射
        assert client._map_qbittorrent_status("downloading") == TorrentStatus.DOWNLOADING
        assert client._map_qbittorrent_status("seeding") == TorrentStatus.SEEDING
        assert client._map_qbittorrent_status("pausedDL") == TorrentStatus.PAUSED
        assert client._map_qbittorrent_status("error") == TorrentStatus.ERROR
        assert client._map_qbittorrent_status("unknown") == TorrentStatus.ERROR
    
    @pytest.mark.asyncio
    async def test_download_manager_list_clients(self, download_manager_instance):
        """测试下载管理器列出客户端"""
        with patch('core.download_client.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.auth_log_in.return_value = None
            mock_client.app_version.return_value = "4.6.0"
            
            # 添加多个客户端
            await download_manager_instance.add_client(
                client_id="qb1",
                client_type=DownloadClientType.QBITTORRENT,
                host="localhost",
                port=8080
            )
            
            await download_manager_instance.add_client(
                client_id="qb2",
                client_type=DownloadClientType.QBITTORRENT,
                host="192.168.1.100",
                port=8080
            )
            
            # 测试列出客户端
            clients = download_manager_instance.list_clients()
            assert len(clients) == 2
            assert clients[0]['id'] == "qb1"
            assert clients[1]['id'] == "qb2"
    
    @pytest.mark.asyncio
    async def test_download_manager_close_all(self, download_manager_instance):
        """测试下载管理器关闭所有连接"""
        with patch('core.download_client.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.auth_log_in.return_value = None
            mock_client.auth_log_out.return_value = None
            
            # 添加客户端
            await download_manager_instance.add_client(
                client_id="qb_test",
                client_type=DownloadClientType.QBITTORRENT,
                host="localhost",
                port=8080
            )
            
            # 测试关闭所有连接
            await download_manager_instance.close_all()
            assert len(download_manager_instance._clients) == 0
            assert download_manager_instance._default_client is None