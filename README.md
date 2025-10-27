# VabHub-Core

VabHub 后端核心服务，基于 FastAPI 构建的媒体管理系统核心。

## 🚀 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
```

### 启动服务
```bash
python start.py
# 或使用轻量级版本
python start_lightweight.py
```

### 访问API文档
启动后访问: http://localhost:8090/docs

## 📁 项目结构

```
VabHub-Core/
├── app/                    # API路由模块
│   ├── __init__.py
│   ├── main.py             # 主应用入口
│   ├── api.py             # API路由
│   ├── auth_routes.py     # 认证路由
│   ├── admin_routes.py    # 管理路由
│   └── ...
├── core/                   # 业务逻辑核心
│   ├── __init__.py
│   ├── config.py          # 配置管理
│   ├── database.py        # 数据库操作
│   ├── ai_processor.py    # AI处理
│   └── ...
├── config/                 # 配置文件
│   ├── config.yaml        # 主配置
│   ├── categories.yaml    # 分类配置
│   └── ...
├── utils/                  # 工具函数
│   ├── __init__.py
│   ├── file_utils.py      # 文件操作
│   └── network_utils.py   # 网络工具
├── requirements.txt       # Python依赖
├── start.py               # 启动脚本
└── README.md
```

## 🔧 核心功能

### API服务
- RESTful API 设计
- OpenAPI 文档自动生成
- JWT 认证机制
- 异步请求处理

### 媒体管理
- 智能媒体识别
- 自动分类和重命名
- 元数据提取
- 批量处理

### AI集成
- 智能推荐系统
- 内容分析
- 自动标签生成
- 语音处理

### 插件系统
- 动态插件加载
- 插件生命周期管理
- 插件间通信

## 📊 API接口

### 认证接口
- `POST /api/auth/login` - 用户登录
- `POST /api/auth/register` - 用户注册
- `GET /api/auth/me` - 获取当前用户信息

### 媒体接口
- `GET /api/media` - 获取媒体列表
- `POST /api/media/scan` - 扫描媒体库
- `PUT /api/media/{id}` - 更新媒体信息
- `DELETE /api/media/{id}` - 删除媒体

### 管理接口
- `GET /api/admin/stats` - 系统统计
- `POST /api/admin/backup` - 备份数据
- `GET /api/admin/logs` - 查看日志

## 🔌 依赖关系

### 核心依赖
- FastAPI >= 0.104.1
- SQLAlchemy >= 2.0.23
- Pydantic >= 2.5.0
- Uvicorn >= 0.24.0

### 可选依赖
- 插件系统: vabhub-plugins
- 资源文件: vabhub-resources
- 前端界面: vabhub-frontend

## 🚀 部署

### Docker部署
```bash
cd ../VabHub-Deploy
docker-compose up -d
```

### 手动部署
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp config/config.example.yaml config/config.yaml

# 3. 启动服务
python start.py
```

## 🔗 相关仓库

- [VabHub-Frontend](https://github.com/vabhub/vabhub-frontend) - 前端界面
- [VabHub-Plugins](https://github.com/vabhub/vabhub-plugins) - 插件系统
- [VabHub-Deploy](https://github.com/vabhub/vabhub-deploy) - 部署配置
- [VabHub-Resources](https://github.com/vabhub/vabhub-resources) - 资源文件

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 开发环境设置
```bash
# 1. Fork 仓库
# 2. 克隆到本地
git clone https://github.com/your-username/vabhub-core.git

# 3. 创建开发分支
git checkout -b feature/your-feature

# 4. 提交更改
git commit -m "feat: add your feature"

# 5. 推送到远程
git push origin feature/your-feature

# 6. 创建 Pull Request
```

### 代码规范
- 遵循 PEP 8 代码风格
- 使用类型注解
- 编写单元测试
- 更新文档

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 📞 支持

- 文档: [VabHub Wiki](https://github.com/vabhub/vabhub-wiki)
- 问题: [GitHub Issues](https://github.com/vabhub/vabhub-core/issues)
- 讨论: [GitHub Discussions](https://github.com/vabhub/vabhub-core/discussions)