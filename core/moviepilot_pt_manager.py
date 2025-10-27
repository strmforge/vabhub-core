"""
基于MoviePilot的增强PT站点管理器
集成MoviePilot多年积累的PT站点支持经验
支持NexusPHP、Gazelle、Unit3D等主流PT站点框架
"""

import asyncio
import json
import re
from abc import ABCMeta, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urljoin, urlsplit

import aiohttp
from lxml import etree

from app.log import logger
from app.utils.http import RequestUtils
from app.utils.string import StringUtils


# 站点框架枚举
class SiteSchema(Enum):
    """站点框架类型"""
    DiscuzX = "DiscuzX"
    Gazelle = "Gazelle"
    Ipt = "IPTorrents"
    NexusPhp = "NexusPhp"
    NexusProject = "NexusProject"
    NexusRabbit = "NexusRabbit"
    NexusHhanclub = "NexusHhanclub"
    NexusAudiences = "NexusAudiences"
    SmallHorse = "Small Horse"
    Unit3d = "Unit3d"
    TorrentLeech = "TorrentLeech"
    FileList = "FileList"
    TNode = "TNode"
    MTorrent = "MTorrent"
    Yema = "Yema"
    HDDolby = "HDDolby"


class SiteUserData:
    """站点用户数据"""
    
    def __init__(self):
        self.domain = ""
        self.userid = ""
        self.username = ""
        self.user_level = ""
        self.join_at = ""
        self.upload = 0
        self.download = 0
        self.ratio = 0.0
        self.bonus = 0.0
        self.seeding = 0
        self.seeding_size = 0
        self.leeching = 0
        self.leeching_size = 0
        self.message_unread = 0
        self.message_unread_contents = []
        self.err_msg = ""


class SiteParserBase(metaclass=ABCMeta):
    """站点解析器基类 - 基于MoviePilot架构"""
    
    schema = None
    request_mode = "cookie"

    def __init__(self, site_name: str, url: str, site_cookie: str = "", 
                 apikey: str = "", token: str = "", ua: str = "", 
                 proxy: bool = False):
        self._site_name = site_name
        self._site_url = url
        self._site_cookie = site_cookie
        self.apikey = apikey
        self.token = token
        self._ua = ua
        self._proxy = proxy
        
        # 解析结果
        self.userdata = SiteUserData()
        self.userdata.domain = StringUtils.get_url_domain(url)
        
        # 页面配置
        self._index_html = ""
        self._user_detail_page = "userdetails.php?id="
        self._torrent_seeding_page = "getusertorrentlistajax.php?userid="

    def parse(self) -> SiteUserData:
        """解析站点信息"""
        try:
            # 获取首页内容
            self._index_html = self._get_page_content(self._site_url)
            if not self._parse_logged_in(self._index_html):
                return self.userdata
            
            # 解析站点页面
            self._parse_site_page(self._index_html)
            
            # 解析用户基础信息
            self._parse_user_base_info(self._index_html)
            
            # 解析用户详细信息
            if self._user_detail_page:
                detail_html = self._get_page_content(
                    urljoin(self._get_base_url(), self._user_detail_page)
                )
                self._parse_user_detail_info(detail_html)
            
            # 解析用户流量信息
            self._parse_user_traffic_info(self._index_html)
            
            # 解析做种信息
            self._parse_seeding_pages()
            
        except Exception as e:
            logger.error(f"解析站点 {self._site_name} 时出错: {e}")
            self.userdata.err_msg = str(e)
        
        return self.userdata

    def _get_base_url(self) -> str:
        """获取基础URL"""
        split_url = urlsplit(self._site_url)
        return f"{split_url.scheme}://{split_url.netloc}"

    def _get_page_content(self, url: str, params: dict = None, headers: dict = None) -> str:
        """获取页面内容"""
        req_headers = {"User-Agent": self._ua} if self._ua else {}
        if headers:
            req_headers.update(headers)
        
        proxies = None
        if self._proxy:
            # 这里可以配置代理设置
            pass
        
        res = RequestUtils(
            cookies=self._site_cookie,
            headers=req_headers,
            timeout=60,
            proxies=proxies
        ).get_res(url=url)
        
        if res and res.status_code == 200:
            return res.text
        return ""

    def _parse_logged_in(self, html_text: str) -> bool:
        """检查是否已登录"""
        # 简单的登录检查逻辑
        logged_in_patterns = [
            r"logout",
            r"退出",
            r"userdetails",
            r"我的信息"
        ]
        
        for pattern in logged_in_patterns:
            if re.search(pattern, html_text, re.IGNORECASE):
                return True
        
        self.userdata.err_msg = "未检测到登录状态，请检查Cookie"
        return False

    def _parse_seeding_pages(self):
        """解析做种页面"""
        if not self._torrent_seeding_page or not self.userdata.userid:
            return
        
        seeding_url = urljoin(
            self._get_base_url(), 
            f"{self._torrent_seeding_page}{self.userdata.userid}"
        )
        
        seeding_html = self._get_page_content(seeding_url)
        if seeding_html:
            self._parse_user_torrent_seeding_info(seeding_html)

    @abstractmethod
    def _parse_site_page(self, html_text: str):
        """解析站点页面"""
        pass

    @abstractmethod
    def _parse_user_base_info(self, html_text: str):
        """解析用户基础信息"""
        pass

    @abstractmethod
    def _parse_user_detail_info(self, html_text: str):
        """解析用户详细信息"""
        pass

    @abstractmethod
    def _parse_user_traffic_info(self, html_text: str):
        """解析用户流量信息"""
        pass

    @abstractmethod
    def _parse_user_torrent_seeding_info(self, html_text: str):
        """解析用户做种信息"""
        pass


class NexusPhpSiteParser(SiteParserBase):
    """NexusPHP站点解析器"""
    
    schema = SiteSchema.NexusPhp

    def _parse_site_page(self, html_text: str):
        """解析站点页面"""
        user_detail = re.search(r"userdetails\.php\?id=(\d+)", html_text)
        if user_detail:
            self.userdata.userid = user_detail.group(1)
            self._torrent_seeding_page = f"getusertorrentlistajax.php?userid={self.userdata.userid}&type=seeding"

    def _parse_user_base_info(self, html_text: str):
        """解析用户基础信息"""
        html = etree.HTML(html_text)
        if html is None:
            return
        
        # 解析用户名
        username_elements = html.xpath('//a[contains(@href, "userdetails")]//text()')
        if username_elements:
            self.userdata.username = username_elements[0].strip()

    def _parse_user_detail_info(self, html_text: str):
        """解析用户详细信息"""
        html = etree.HTML(html_text)
        if html is None:
            return
        
        # 解析用户等级
        level_elements = html.xpath('//td[contains(text(), "等级")]/following-sibling::td//text()')
        if level_elements:
            self.userdata.user_level = level_elements[0].strip()

    def _parse_user_traffic_info(self, html_text: str):
        """解析用户流量信息"""
        # 上传量
        upload_match = re.search(r"上[传傳]量?[^\d]*([\d,.]+[KMGTP]?B)", html_text, re.IGNORECASE)
        if upload_match:
            self.userdata.upload = StringUtils.num_filesize(upload_match.group(1))
        
        # 下载量
        download_match = re.search(r"下[载載]量?[^\d]*([\d,.]+[KMGTP]?B)", html_text, re.IGNORECASE)
        if download_match:
            self.userdata.download = StringUtils.num_filesize(download_match.group(1))
        
        # 分享率
        ratio_match = re.search(r"分享率[^\d]*([\d.]+)", html_text)
        if ratio_match:
            self.userdata.ratio = float(ratio_match.group(1))
        elif self.userdata.download > 0:
            self.userdata.ratio = self.userdata.upload / self.userdata.download

    def _parse_user_torrent_seeding_info(self, html_text: str):
        """解析做种信息"""
        # 简单的做种数量统计
        seeding_match = re.findall(r"做种中", html_text)
        self.userdata.seeding = len(seeding_match)


class GazelleSiteParser(SiteParserBase):
    """Gazelle站点解析器"""
    
    schema = SiteSchema.Gazelle

    def _parse_site_page(self, html_text: str):
        """解析站点页面"""
        user_id_match = re.search(r"user\.php\?id=(\d+)", html_text)
        if user_id_match:
            self.userdata.userid = user_id_match.group(1)
            self._torrent_seeding_page = f"torrents.php?type=seeding&userid={self.userdata.userid}"

    def _parse_user_base_info(self, html_text: str):
        """解析用户基础信息"""
        html = etree.HTML(html_text)
        if html is None:
            return
        
        # 解析用户名
        username_elements = html.xpath('//a[contains(@href, "user.php?id=")]//text()')
        if username_elements:
            self.userdata.username = username_elements[0].strip()
        
        # 解析上传下载数据
        upload_elements = html.xpath('//*[contains(@id, "uploaded")]//text()')
        if upload_elements:
            self.userdata.upload = StringUtils.num_filesize(upload_elements[0])
        
        download_elements = html.xpath('//*[contains(@id, "downloaded")]//text()')
        if download_elements:
            self.userdata.download = StringUtils.num_filesize(download_elements[0])

    def _parse_user_detail_info(self, html_text: str):
        """解析用户详细信息"""
        html = etree.HTML(html_text)
        if html is None:
            return
        
        # 解析用户等级
        level_elements = html.xpath('//*[contains(@class, "class")]//text()')
        if level_elements:
            self.userdata.user_level = level_elements[0].strip()

    def _parse_user_traffic_info(self, html_text: str):
        """解析用户流量信息"""
        # Gazelle通常在基础信息中已经解析
        if self.userdata.download > 0:
            self.userdata.ratio = self.userdata.upload / self.userdata.download

    def _parse_user_torrent_seeding_info(self, html_text: str):
        """解析做种信息"""
        html = etree.HTML(html_text)
        if html is None:
            return
        
        # 统计做种数量
        seeding_elements = html.xpath('//tr[contains(@class, "torrent")]')
        self.userdata.seeding = len(seeding_elements)


class Unit3dSiteParser(SiteParserBase):
    """Unit3D站点解析器"""
    
    schema = SiteSchema.Unit3d

    def _parse_site_page(self, html_text: str):
        """解析站点页面"""
        username_match = re.search(r"/users/([^/]+)/", html_text)
        if username_match:
            self.userdata.username = username_match.group(1)
            self._torrent_seeding_page = f"/users/{self.userdata.username}/active"

    def _parse_user_base_info(self, html_text: str):
        """解析用户基础信息"""
        html = etree.HTML(html_text)
        if html is None:
            return
        
        # 解析上传下载数据
        upload_match = re.search(r"Uploaded[^\d]*([\d,.]+[KMGTP]?B)", html_text, re.IGNORECASE)
        if upload_match:
            self.userdata.upload = StringUtils.num_filesize(upload_match.group(1))
        
        download_match = re.search(r"Downloaded[^\d]*([\d,.]+[KMGTP]?B)", html_text, re.IGNORECASE)
        if download_match:
            self.userdata.download = StringUtils.num_filesize(download_match.group(1))

    def _parse_user_detail_info(self, html_text: str):
        """解析用户详细信息"""
        html = etree.HTML(html_text)
        if html is None:
            return
        
        # 解析用户等级
        level_elements = html.xpath('//span[contains(@class, "badge-user")]//text()')
        if level_elements:
            self.userdata.user_level = level_elements[0].strip()

    def _parse_user_traffic_info(self, html_text: str):
        """解析用户流量信息"""
        if self.userdata.download > 0:
            self.userdata.ratio = self.userdata.upload / self.userdata.download

    def _parse_user_torrent_seeding_info(self, html_text: str):
        """解析做种信息"""
        html = etree.HTML(html_text)
        if html is None:
            return
        
        # 统计做种数量
        seeding_elements = html.xpath('//tr[contains(@class, "active-torrent")]')
        self.userdata.seeding = len(seeding_elements)


class MoviePilotPTManager:
    """基于MoviePilot的PT站点管理器"""
    
    def __init__(self):
        self.parsers = {
            SiteSchema.NexusPhp: NexusPhpSiteParser,
            SiteSchema.Gazelle: GazelleSiteParser,
            SiteSchema.Unit3d: Unit3dSiteParser
        }
        self.sites = {}

    def add_site(self, name: str, url: str, schema: SiteSchema, 
                 cookie: str = "", apikey: str = "", ua: str = "", 
                 proxy: bool = False):
        """添加站点配置"""
        self.sites[name] = {
            'name': name,
            'url': url,
            'schema': schema,
            'cookie': cookie,
            'apikey': apikey,
            'ua': ua,
            'proxy': proxy
        }

    def get_user_data(self, site_name: str) -> Optional[SiteUserData]:
        """获取站点用户数据"""
        if site_name not in self.sites:
            return None
        
        site_config = self.sites[site_name]
        parser_class = self.parsers.get(site_config['schema'])
        
        if not parser_class:
            logger.error(f"不支持的站点框架: {site_config['schema']}")
            return None
        
        parser = parser_class(
            site_name=site_config['name'],
            url=site_config['url'],
            site_cookie=site_config['cookie'],
            apikey=site_config['apikey'],
            ua=site_config['ua'],
            proxy=site_config['proxy']
        )
        
        return parser.parse()

    async def refresh_all_sites(self) -> Dict[str, SiteUserData]:
        """异步刷新所有站点数据"""
        results = {}
        
        async def refresh_site(site_name, site_config):
            try:
                user_data = self.get_user_data(site_name)
                results[site_name] = user_data
            except Exception as e:
                logger.error(f"刷新站点 {site_name} 时出错: {e}")
                results[site_name] = None
        
        tasks = []
        for site_name, site_config in self.sites.items():
            task = asyncio.create_task(refresh_site(site_name, site_config))
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        return results

    def get_site_statistics(self) -> Dict[str, Dict]:
        """获取站点统计信息"""
        stats = {}
        for site_name in self.sites:
            user_data = self.get_user_data(site_name)
            if user_data and not user_data.err_msg:
                stats[site_name] = {
                    'username': user_data.username,
                    'upload': user_data.upload,
                    'download': user_data.download,
                    'ratio': user_data.ratio,
                    'seeding': user_data.seeding,
                    'message_unread': user_data.message_unread
                }
        return stats