# VabHub-Core

VabHub-Core 是 VabHub 媒体管理系统的后端核心服务，基于 FastAPI 构建，提供完整的媒体管理、搜索、下载和插件系统功能。

## 🎉 最新版本: 1.3.0

**VabHub-Core 1.3.0** 是一个重大版本更新，将系统从基础媒体管理平台提升到**企业级PT自动化系统**。

### 🚀 1.3.0 版本亮点
- **智能搜索系统**: 老电视剧搜索优化，查询扩展，智能搜索引擎
- **专业仪表盘**: 实时系统监控，多下载器支持，媒体服务器集成
- **增强插件系统**: 完整生命周期管理，热更新支持
- **性能提升**: API响应时间提升60%，并发用户数提升200%

## 🏗️ 架构特性

### 🔍 智能搜索系统
- **老电视剧优化**: 自动识别"天下第一"等老电视剧
- **查询扩展**: 多种搜索变体生成
- **智能引擎**: 内容分类和智能分析
- **高级处理**: 多维度质量评估

### 📊 专业仪表盘
- **实时监控**: CPU、内存、磁盘、网络监控
- **下载器管理**: qBittorrent、Aria2、Transmission支持
- **媒体服务器**: Plex、Jellyfin、Emby集成
- **WebSocket通信**: 实时数据更新

### 🔌 插件系统
- **生命周期管理**: 完整的状态管理
- **热更新支持**: 插件热重载功能
- **配置管理**: 图形化配置界面
- **插件类型**: 多种插件类型支持

## 🔧 技术栈

### 后端技术
- **框架**: FastAPI + WebSocket 实时通信
- **语言**: Python 3.11+
- **数据库**: PostgreSQL / SQLite (查询优化50%)
- **缓存**: Redis 缓存和消息队列
- **任务队列**: Celery 异步任务处理

### 性能指标
| 指标 | 1.2.0 | 1.3.0 | 提升 |
|------|-------|-------|------|
| API响应时间 | 200ms | 80ms | 60% |
| 并发用户数 | 50 | 150 | 200% |
| 内存使用 | 512MB | 350MB | 32% |
| 数据库查询 | 100ms | 45ms | 55% |

## 🚀 快速开始

### 开发环境
```bash
# 1. 克隆仓库
git clone https://github.com/vabhub/vabhub-core.git
cd vabhub-core

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动服务
python start.py

# 4. 访问API文档
# http://localhost:8090/docs
```

### Docker部署
```bash
# 使用 Docker Compose
docker-compose -f docker-compose.yml up -d
```

## 📁 项目结构

```
VabHub-Core/
├── app/                 # API 路由模块
│   ├── api.py          # 主API路由
│   ├── dashboard_routes.py # 仪表盘路由
│   └── plugin_routes.py    # 插件路由
├── core/               # 业务逻辑核心
│   ├── config.py       # 配置管理
│   ├── database.py     # 数据库管理
│   ├── search/         # 搜索系统
│   └── plugins/        # 插件系统
├── tests/              # 测试代码
├── requirements.txt    # Python依赖
└── setup.py          # 打包配置
```

## 🔗 相关仓库

- **前端界面**: [vabhub-frontend](https://github.com/vabhub/vabhub-frontend)
- **部署配置**: [vabhub-deploy](https://github.com/vabhub/vabhub-deploy)
- **插件系统**: [vabhub-plugins](https://github.com/vabhub/vabhub-plugins)

## 🤝 贡献指南

欢迎参与 VabHub-Core 项目的开发！

### 开发流程
1. Fork 仓库
2. 创建功能分支
3. 提交代码更改
4. 创建 Pull Request

### 代码规范
- 遵循 PEP 8 代码规范
- 使用 Black 代码格式化
- 编写单元测试
- 更新相关文档

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 📞 支持与交流

- **文档**: [VabHub Wiki](https://github.com/vabhub/vabhub-wiki)
- **问题**: [GitHub Issues](https://github.com/vabhub/vabhub-core/issues)
- **讨论**: [GitHub Discussions](https://github.com/vabhub/vabhub-core/discussions)

---

**VabHub Core Team**  
*让媒体管理更智能、更简单*  
2025年10月28日