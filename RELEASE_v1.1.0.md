# VabHub Core v1.1.0 发布说明

## 🎉 版本亮点

VabHub Core v1.1.0 带来了完整的媒体管理系统，包括数据库集成、异步API、增强的插件系统和完整的错误处理机制。

## 🚀 主要特性

### 完整的媒体管理系统
- 支持媒体库、媒体项、电视剧季和剧集管理
- 完整的CRUD操作和搜索功能
- 智能媒体识别和分类

### 数据库集成
- SQLAlchemy ORM支持SQLite和PostgreSQL
- 异步数据库操作
- 数据模型关系管理

### 增强的插件系统
- 改进的插件生命周期管理
- 插件市场功能
- 插件设置持久化

### 错误处理和日志
- 结构化日志记录
- 统一的错误响应格式
- 请求日志中间件

## 📋 系统要求

- Python 3.8+
- 数据库：SQLite 3.32+ 或 PostgreSQL 12+
- 内存：至少 512MB RAM
- 存储：根据媒体库大小而定

## 🔧 安装说明

```bash
pip install vabhub-core==1.1.0
```

## 📖 使用说明

1. 配置数据库连接
2. 启动核心服务
3. 访问API文档：http://localhost:8000/docs

## 🔗 相关链接

- [文档](https://github.com/vabhub/vabhub-core/docs)
- [API参考](https://github.com/vabhub/vabhub-core/api)
- [问题反馈](https://github.com/vabhub/vabhub-core/issues)

## 🙏 致谢

感谢所有贡献者和用户的支持！