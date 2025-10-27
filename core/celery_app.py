#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Celery任务队列系统
支持异步任务处理和分布式处理
"""

from celery import Celery
from celery.signals import task_postrun, task_failure
from core.config import settings
from core.monitoring import metrics_collector
import structlog

logger = structlog.get_logger()

# 创建Celery应用
celery_app = Celery(
    'media_renamer',
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=['core.tasks']
)

# 配置Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    task_send_sent_event=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    broker_connection_retry_on_startup=True,
)


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwargs):
    """任务完成后处理"""
    metrics_collector.increment("celery.tasks.completed")
    logger.info("Celery任务完成", task_id=task_id, task_name=task.name, state=state)


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwargs):
    """任务失败处理"""
    metrics_collector.increment("celery.tasks.failed")
    logger.error("Celery任务失败", task_id=task_id, exception=str(exception))


if __name__ == '__main__':
    celery_app.start()