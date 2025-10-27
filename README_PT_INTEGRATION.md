# VabHub PT功能集成文档

## 概述

本文档介绍了VabHub从media-renamer项目中集成的PT功能模块，包括PT站点管理、智能识别、下载器集成等核心功能。

## 集成功能模块

### 1. 增强PT站点管理器 (`core/enhanced_pt_manager.py`)

**功能特性:**
- 支持多种PT站点类型：NexusPHP、Gazelle、Unit3D等
- 自动站点适配器检测和连接
- 多站点并行搜索和下载
- 站点状态监控和统计

**核心类:**
- `PTManager`: PT站点管理器
- `SiteAdapter`: 站点适配器基类
- `NexusPHPAdapter`: NexusPHP站点适配器
- `GazelleAdapter`: Gazelle站点适配器

### 2. 智能识别引擎 (`core/smart_recognizer.py`)

**功能特性:**
- 基于NAS-Tools和MoviePilot算法的智能识别
- 支持100+发布组模式识别
- 视频/音频编码自动识别
- 电视剧季集信息提取

**识别能力:**
- 标题、年份、质量、编码
- 发布组、季数、集数
- 特殊格式（IMAX、HDR、DV等）
- 中英文混合文件名

### 3. 下载器管理系统 (`core/enhanced_downloader.py`)

**支持的下载器:**
- qBittorrent (推荐)
- Transmission
- Aria2 (计划支持)

**功能特性:**
- 插件化架构，支持热插拔
- 多下载器并行管理
- 速度限制和任务控制
- 实时状态监控

### 4. PT功能集成模块 (`core/pt_integration.py`)

**集成功能:**
- 统一API接口
- 智能搜索和匹配
- 自动下载规则
- 下载历史记录

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置PT站点

编辑 `config/pt_config.yaml` 文件：

```yaml
pt_sites:
  nexusphp:
    - name: "m-team"
      url: "https://tp.m-team.cc"
      cookie: "your_cookie_here"
      user_agent: "Mozilla/5.0..."

downloaders:
  qbittorrent:
    host: "localhost"
    port: 8080
    username: "admin"
    password: "adminadmin"
    enabled: true
```

### 3. 使用示例

```python
import asyncio
from core.pt_integration import get_pt_integration
import yaml

async def main():
    # 加载配置
    with open('config/pt_config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # 获取PT集成实例
    pt_integration = await get_pt_integration(config)
    
    # 搜索种子
    results = await pt_integration.search_torrents(["Avengers Endgame"])
    
    # 下载种子
    if results:
        await pt_integration.download_torrent(results[0])
    
    # 关闭连接
    await pt_integration.close()

asyncio.run(main())
```

### 4. 运行演示

```bash
python demo_pt_integration.py
```

## 核心API

### PTIntegration 类

#### 初始化
```python
pt_integration = PTIntegration(config)
await pt_integration.initialize()
```

#### 搜索种子
```python
results = await pt_integration.search_torrents(
    keywords=["keyword1", "keyword2"],
    categories=["movie", "tv"],
    sites=["m-team", "hdsky"]
)
```

#### 下载种子
```python
success = await pt_integration.download_torrent(
    torrent_info=torrent_data,
    save_path="/path/to/save",
    category="movie"
)
```

#### 获取状态
```python
status = await pt_integration.get_download_status()
```

#### 自动下载
```python
downloaded = await pt_integration.auto_download(rules_config)
```

### SmartRecognizer 类

#### 文件名解析
```python
from core.smart_recognizer import SmartRecognizer

recognizer = SmartRecognizer()
result = recognizer.parse_filename("Avengers.Endgame.2019.IMAX.2160p.BluRay.x264.mkv")
```

### DownloaderManager 类

#### 管理下载器
```python
from core.enhanced_downloader import download_manager

# 添加下载器
await download_manager.add_downloader("qbt", "qbittorrent", config)

# 设置活跃下载器
download_manager.set_active_downloader("qbt")

# 下载种子
await download_manager.download_torrent("path/to/torrent.torrent")
```

## 配置说明

### PT站点配置

```yaml
pt_sites:
  nexusphp:
    - name: "站点名称"
      url: "站点URL"
      cookie: "登录Cookie"
      user_agent: "浏览器标识"
  gazelle:
    - name: "Gazelle站点"
      # ... 类似配置
```

### 下载器配置

```yaml
downloaders:
  qbittorrent:
    host: "localhost"
    port: 8080
    username: "admin"
    password: "adminadmin"
    enabled: true
  transmission:
    host: "localhost"
    port: 9091
    username: ""
    password: ""
    enabled: false
```

### 自动下载规则

```yaml
auto_download_rules:
  movie:
    min_size: "1GB"
    max_size: "20GB"
    quality: ["4K", "1080p"]
    codec: ["H.265", "H.264"]
    min_seeds: 5
  tv:
    min_size: "500MB"
    max_size: "5GB"
    quality: ["1080p", "720p"]
    min_seeds: 3
```

## 高级功能

### 1. 自定义站点适配器

继承 `SiteAdapter` 类创建自定义适配器：

```python
from core.enhanced_pt_manager import SiteAdapter

class CustomSiteAdapter(SiteAdapter):
    async def search(self, keyword, category=None):
        # 实现搜索逻辑
        pass
    
    async def download_torrent(self, torrent_info):
        # 实现下载逻辑
        pass
```

### 2. 智能识别规则扩展

在 `smart_recognizer.py` 中添加新的识别规则：

```python
# 添加新的发布组识别
RELEASE_GROUP_PATTERNS.update({
    'NEWGROUP': r'(?i)(NEWGROUP|NG)'
})

# 添加新的质量识别
QUALITY_PATTERNS.update({
    '8K': r'(?i)(8k|7680)'
})
```

### 3. 下载器插件开发

继承 `DownloaderPlugin` 类创建新的下载器插件：

```python
from core.enhanced_downloader import DownloaderPlugin

class CustomDownloaderPlugin(DownloaderPlugin):
    async def _perform_connect(self):
        # 实现连接逻辑
        pass
    
    async def _add_torrent(self, torrent_file, save_path, category, paused):
        # 实现添加任务逻辑
        pass
```

## 故障排除

### 常见问题

1. **连接失败**
   - 检查网络连接
   - 验证配置信息
   - 检查防火墙设置

2. **认证失败**
   - 更新Cookie信息
   - 检查用户权限
   - 验证API密钥

3. **下载失败**
   - 检查磁盘空间
   - 验证下载路径权限
   - 检查下载器状态

### 日志调试

启用详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 性能优化

### 1. 并发控制

```python
# 限制并发搜索数量
MAX_CONCURRENT_SEARCHES = 3

# 限制并发下载数量  
MAX_CONCURRENT_DOWNLOADS = 2
```

### 2. 缓存策略

- 搜索结果缓存（1小时）
- 站点状态缓存（5分钟）
- 识别结果缓存（永久）

### 3. 内存优化

- 使用生成器处理大量数据
- 及时释放大文件句柄
- 分批处理任务

## 安全考虑

### 1. 敏感信息保护

- 配置文件加密存储
- API密钥环境变量管理
- 访问日志审计

### 2. 权限控制

- 下载路径权限限制
- API访问频率限制
- 用户身份验证

## 扩展开发

### 1. 添加新功能

1. 在相应模块中添加新类
2. 更新配置结构
3. 编写单元测试
4. 更新文档

### 2. 集成现有系统

- 通过API接口集成
- 使用消息队列异步处理
- 数据库同步机制

## 贡献指南

### 代码规范

- 遵循PEP 8
- 添加类型注解
- 编写文档字符串
- 单元测试覆盖

### 提交流程

1. Fork项目
2. 创建功能分支
3. 编写代码和测试
4. 提交Pull Request

## 许可证

本项目基于MIT许可证开源。

## 支持与反馈

如有问题或建议，请通过以下方式联系：

- GitHub Issues
- 邮件支持
- 社区讨论

---

**注意**: 使用PT功能请遵守相关站点的使用条款和法律法规。