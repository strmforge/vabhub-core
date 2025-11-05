VabHub Core Documentation
=========================

.. image:: https://img.shields.io/badge/build-passing-brightgreen.svg
   :alt: Build Status

.. image:: https://img.shields.io/badge/docker-image-blue
   :alt: Docker

.. image:: https://img.shields.io/badge/license-MIT-green.svg
   :alt: License

VabHub Core 是一个媒体管理和自动化系统的核心后端服务，提供了 REST/GraphQL API、媒体识别和重命名内核、站点和下载器的统一抽象、媒体库集成、日志与任务调度以及插件运行时等功能。

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   usage
   modules
   code_quality_improvements
   performance_optimization_guide

Overview
--------

VabHub Core 提供了以下核心功能：

- REST/GraphQL API 接口
- 媒体文件识别和重命名内核
- 站点和下载器的统一抽象层
- 媒体库集成支持
- 日志记录和任务调度
- 插件运行时环境（接口/SDK）

系统要求
--------

- Python 3.8 或更高版本
- 支持的数据库（SQLite, PostgreSQL, MySQL）
- Redis（用于缓存和任务队列）

快速开始
--------

请参阅 :doc:`installation` 页面了解安装指南。

API 文档
--------

启动服务后，可以通过以下地址访问 API 文档：

- Swagger UI: ``http://localhost:8000/docs``
- ReDoc: ``http://localhost:8000/redoc``

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`