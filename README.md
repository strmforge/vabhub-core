# VabHub Core · 后端服务

[![Build](https://img.shields.io/badge/build-passing-brightgreen.svg)](#)
[![Docker](https://img.shields.io/badge/docker-image-blue)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](#)

**唯一后端服务**：REST/GraphQL API、识别/重命名内核、站点/下载器统一抽象、媒体库集成、日志与任务调度、插件运行时（接口/SDK）。
> 插件“实现”请放 `vabhub-plugins`，本仓仅提供运行时与接口。

## 快速开始（开发）
```bash
cp config/.env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn core.api.main:app --host 0.0.0.0 --port 8081 --reload
```
**Docker**
```bash
docker build -t ghcr.io/strmforge/vabhub-core:dev .
docker run --env-file .env -p 8081:8081 ghcr.io/strmforge/vabhub-core:dev
```
