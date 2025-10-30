# VabHub Core — Backend API & Orchestrator

[![CI](https://img.shields.io/github/actions/workflow/status/strmforge/vabhub-Core/ci.yml?branch=main&label=CI)](https://github.com/strmforge/vabhub-Core/actions)
[![Release](https://img.shields.io/github/v/release/strmforge/vabhub-Core?label=Release)](https://github.com/strmforge/vabhub-Core/releases)
[![Image](https://img.shields.io/badge/ghcr.io-strmforge/vabhub--core-blue)](https://ghcr.io/strmforge/vabhub-core)
[![License](https://img.shields.io/badge/License-MIT-green)](#license)

后端主仓：统一接口、任务编排、存储适配器（123/115）。**SemVer Tag 为唯一兼容依据**。

## 快速开始（Docker）
```bash
docker run -p 8080:8000 ghcr.io/strmforge/vabhub-core:latest
# 打开 http://localhost:8080
```

## 本地开发
```bash
# 例：FastAPI
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 环境变量（后端-only）
- 123：`Y123_CLIENT_ID`、`Y123_CLIENT_SECRET`、`Y123_REFRESH_TOKEN?`
- 115：`Y115_CLIENT_ID`、`Y115_CLIENT_SECRET`、`Y115_REFRESH_TOKEN?`
> 不在前端注入任何密钥（禁止 `VITE_*` 暴露）。

## 兼容性
- WebUI 最低兼容：见 `vabhub-frontend` README 中的 engine 字段
- 部署版本组合：以 `vabhub-deploy` 仓的 `versions.json` 为准

## License
MIT
