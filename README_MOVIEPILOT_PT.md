# MoviePilot PT站点管理器集成文档

## 概述

基于MoviePilot项目多年积累的PT站点管理经验，我们将其核心功能集成到VabHub中，提供了专业级的PT站点管理能力。

## 核心功能

### 1. 多站点支持
- **NexusPHP站点**：支持大多数基于NexusPHP的PT站点
- **Gazelle站点**：支持Gazelle架构的站点（如HDBits、BTN等）
- **Unit3D站点**：支持Unit3D架构的站点
- **自定义站点**：支持自定义站点配置和解析规则

### 2. 智能解析器
- **自动识别**：自动识别站点类型和解析规则
- **字段提取**：精确提取种子标题、大小、做种人数、下载人数等信息
- **分类识别**：智能识别电影、电视剧、音乐、游戏等分类
- **质量识别**：识别1080p、4K、HDR、REMUX等质量信息

### 3. 搜索和下载
- **多站点并行搜索**：同时搜索多个PT站点
- **智能排序**：根据做种人数、文件大小、发布时间等智能排序
- **自动下载**：支持自动下载符合条件的种子
- **下载器集成**：支持qBittorrent、Transmission等下载器

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置站点信息
编辑 `config/moviepilot_pt_config.yaml` 文件：

```yaml
sites:
  - name: "站点1"
    url: "https://example.com"
    username: "your_username"
    password: "your_password"
    cookie: "your_cookie"
    parser: "nexusphp"  # 或 gazelle, unit3d
    enabled: true
    
  - name: "站点2"
    url: "https://example2.com"
    username: "your_username"
    password: "your_password"
    parser: "gazelle"
    enabled: true

downloader:
  type: "qbittorrent"  # 或 transmission
  host: "localhost"
  port: 8080
  username: "admin"
  password: "adminadmin"

search:
  timeout: 30
  max_results: 50
  min_seeders: 1
  preferred_quality: ["4K", "1080p", "720p"]
```

### 3. 使用示例
```python
from core.moviepilot_pt_manager import MoviePilotPTManager

# 初始化管理器
manager = MoviePilotPTManager("config/moviepilot_pt_config.yaml")

# 搜索电影
results = await manager.search_movie("阿凡达", year=2022)

# 搜索电视剧
results = await manager.search_tvshow("权力的游戏", season=1, episode=1)

# 自动下载
await manager.auto_download("电影名称", quality="4K")

# 获取站点统计
stats = await manager.get_site_stats()
```

## API参考

### MoviePilotPTManager类

#### 初始化
```python
manager = MoviePilotPTManager(config_path: str)
```

#### 搜索方法
- `search_movie(title: str, year: int = None) -> List[TorrentInfo]`
- `search_tvshow(title: str, season: int = None, episode: int = None) -> List[TorrentInfo]`
- `search_keyword(keyword: str, category: str = None) -> List[TorrentInfo]`

#### 下载方法
- `download_torrent(torrent_info: TorrentInfo, save_path: str = None) -> bool`
- `auto_download(title: str, quality: str = None, min_seeders: int = 1) -> bool`

#### 管理方法
- `get_site_stats() -> Dict[str, SiteStats]`
- `test_site_connection(site_name: str) -> bool`
- `update_site_cookie(site_name: str, cookie: str) -> bool`

## 站点解析器

### 支持的解析器类型

1. **NexusPHP解析器**
   - 支持大多数NexusPHP站点
   - 自动识别登录状态
   - 支持搜索和详情页解析

2. **Gazelle解析器**
   - 支持Gazelle API和网页解析
   - 精确的媒体信息提取
   - 支持高级搜索选项

3. **Unit3D解析器**
   - 支持Unit3D架构站点
   - 现代化的界面解析
   - 支持AJAX加载内容

### 自定义解析器

您可以创建自定义解析器来支持特定的PT站点：

```python
from core.moviepilot_pt_manager.parsers import BaseParser

class CustomParser(BaseParser):
    def parse_search_results(self, html: str) -> List[TorrentInfo]:
        # 实现自定义解析逻辑
        pass
    
    def parse_torrent_detail(self, html: str) -> TorrentInfo:
        # 实现详情页解析逻辑
        pass
```

## 高级功能

### 1. 智能过滤
- 根据文件大小、做种人数、发布时间自动过滤
- 支持自定义过滤规则
- 质量偏好设置

### 2. 批量操作
- 批量搜索和下载
- 支持任务队列
- 并发控制

### 3. 状态监控
- 实时监控下载进度
- 站点可用性检查
- 错误重试机制

## 故障排除

### 常见问题

1. **登录失败**
   - 检查用户名密码是否正确
   - 尝试使用Cookie登录
   - 确认站点是否维护中

2. **搜索无结果**
   - 检查网络连接
   - 确认搜索关键词正确
   - 检查站点搜索功能是否正常

3. **下载失败**
   - 检查下载器配置
   - 确认下载路径可写
   - 检查防火墙设置

### 调试模式

启用调试日志：
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 性能优化

### 缓存策略
- 搜索结果缓存
- 站点信息缓存
- 减少重复请求

### 并发控制
- 限制同时请求数量
- 请求间隔控制
- 错误重试机制

## 安全考虑

- 配置文件加密存储
- 敏感信息保护
- 请求频率限制
- 遵守站点规则

## 贡献指南

欢迎贡献新的站点解析器和功能改进！

## 许可证

本项目基于MoviePilot项目的开源精神，遵循相应的开源协议。