# VabHub Core 测试套件

## 概述

VabHub Core 项目包含完整的单元测试和集成测试套件，确保代码质量和功能稳定性。

## 测试结构

```
tests/
├── __init__.py              # 测试包初始化
├── conftest.py              # pytest 配置和共享fixtures
├── test_database.py          # 数据库模块单元测试
├── test_cache.py             # 缓存模块单元测试
├── test_charts.py            # 图表服务单元测试
├── test_api.py               # API端点单元测试
├── test_auth.py              # 认证模块单元测试
├── test_config.py            # 配置模块单元测试
├── test_integration.py       # 集成测试
└── README.md                 # 测试文档
```

## 运行测试

### 基本测试命令

```bash
# 运行所有测试
pytest tests/

# 运行单元测试
pytest tests/ -k "not integration"

# 运行集成测试
pytest tests/test_integration.py

# 运行特定测试文件
pytest tests/test_database.py

# 运行测试并生成覆盖率报告
pytest tests/ --cov=core --cov-report=html
```

### 使用 Makefile

```bash
# 运行所有测试
make test

# 仅运行单元测试
make test-unit

# 仅运行集成测试
make test-integration

# 运行测试并生成覆盖率报告
make test-coverage

# 生成测试报告
make test-report

# 清理测试文件
make clean-test
```

## 测试类型

### 单元测试

- **test_database.py**: 测试数据库连接、CRUD操作、事务处理
- **test_cache.py**: 测试Redis缓存操作、TTL管理、序列化
- **test_charts.py**: 测试图表数据获取、处理、缓存逻辑
- **test_api.py**: 测试API端点、请求验证、响应格式
- **test_auth.py**: 测试认证中间件、JWT令牌管理
- **test_config.py**: 测试配置加载、环境变量处理

### 集成测试

- **test_integration.py**: 测试完整的工作流程，包括：
  - 图表数据获取和缓存
  - 数据库和缓存同步
  - 并发请求处理
  - 错误恢复机制
  - 性能测试
  - 安全测试

## 测试配置

### pytest.ini

```ini
[pytest]
markers =
    unit: 单元测试
    integration: 集成测试
    slow: 慢速测试
    performance: 性能测试
    security: 安全测试

asyncio_mode = auto
addopts = -v --strict-markers --tb=short
```

### conftest.py

提供共享的测试fixtures：

- `temp_db_path`: 临时数据库文件路径
- `mock_redis`: 模拟Redis连接
- `test_config`: 测试配置对象
- `integration_setup`: 集成测试环境设置

## 测试覆盖率

项目目标覆盖率：**85%+**

### 查看覆盖率报告

```bash
# 生成HTML覆盖率报告
pytest tests/ --cov=core --cov-report=html

# 在浏览器中打开报告
open htmlcov/index.html
```

### 覆盖率要求

- 核心业务逻辑：90%+
- API端点：85%+
- 数据库操作：80%+
- 缓存操作：85%+

## CI/CD 集成

测试套件已集成到GitHub Actions工作流中：

### 触发条件

- 推送到 `main` 或 `develop` 分支
- 创建Pull Request到 `main` 分支
- 每日凌晨2点自动运行

### 测试矩阵

- Python版本：3.9, 3.10, 3.11
- Redis服务：7-alpine
- 操作系统：Ubuntu最新版

### 测试阶段

1. **单元测试**: 运行所有单元测试
2. **集成测试**: 运行集成测试
3. **代码质量**: 代码格式检查和类型检查
4. **安全扫描**: 依赖安全检查和代码安全扫描
5. **构建测试**: 包构建测试

## 测试最佳实践

### 编写测试

1. **命名规范**: 测试方法名应描述测试行为
2. **单一职责**: 每个测试只测试一个功能
3. **隔离性**: 测试之间不相互依赖
4. **可读性**: 测试代码应清晰易懂
5. **错误处理**: 测试应验证错误情况

### 测试数据

- 使用fixture管理测试数据
- 避免硬编码敏感信息
- 使用工厂模式创建测试对象
- 清理测试产生的临时数据

### 异步测试

- 使用 `pytest-asyncio` 处理异步代码
- 正确使用 `async` 和 `await`
- 测试异步异常处理

## 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查数据库服务是否运行
   - 验证连接字符串格式

2. **Redis连接失败**
   - 检查Redis服务是否运行
   - 验证端口和认证配置

3. **异步测试超时**
   - 增加测试超时时间
   - 检查异步操作是否阻塞

4. **导入错误**
   - 检查Python路径设置
   - 验证模块导入路径

### 调试技巧

```bash
# 启用详细输出
pytest tests/ -v -s

# 运行特定测试方法
pytest tests/test_database.py::TestDatabase::test_connection -v

# 启用调试模式
pytest tests/ --pdb
```

## 贡献指南

### 添加新测试

1. 为新功能编写对应的测试
2. 遵循现有的测试模式
3. 确保测试覆盖所有边界情况
4. 运行测试验证功能正确性

### 修改现有测试

1. 确保修改不会破坏现有功能
2. 更新测试以反映功能变更
3. 验证所有相关测试通过

### 测试审查

- 确保测试覆盖所有关键路径
- 验证错误处理逻辑
- 检查测试的可维护性
- 确认性能要求满足

## 性能基准

测试套件应在以下时间内完成：

- 单元测试：< 30秒
- 集成测试：< 2分钟
- 完整测试套件：< 3分钟

## 安全考虑

- 测试中不使用真实API密钥
- 敏感数据使用环境变量或模拟数据
- 测试数据库使用临时文件
- 清理测试产生的所有临时数据