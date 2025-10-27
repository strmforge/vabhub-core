#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强工作流引擎
整合MoviePilot的工作流管理和执行功能
"""

import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable

import structlog
from app.utils.commons import SingletonMeta

from .enhanced_event import EventType, Event, event_manager

logger = structlog.get_logger()


class WorkflowStatus(Enum):
    """工作流状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    """步骤状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """工作流步骤"""
    name: str
    action: str
    parameters: Dict[str, Any]
    conditions: Optional[List[str]] = None
    timeout: int = 300
    retry_count: int = 3
    retry_delay: int = 5


@dataclass
class WorkflowExecution:
    """工作流执行记录"""
    execution_id: str
    workflow_id: str
    status: WorkflowStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    steps_executed: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.steps_executed is None:
            self.steps_executed = []


class WorkflowAction(ABC):
    """工作流动作基类"""
    
    @abstractmethod
    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行动作"""
        pass
    
    @abstractmethod
    def validate(self, parameters: Dict[str, Any]) -> bool:
        """验证参数"""
        pass


class WorkflowCondition(ABC):
    """工作流条件基类"""
    
    @abstractmethod
    async def evaluate(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """评估条件"""
        pass


class EnhancedWorkflowEngine(metaclass=SingletonMeta):
    """增强工作流引擎 - 整合MoviePilot的工作流管理"""
    
    def __init__(self):
        # 工作流存储
        self.workflows: Dict[str, Dict[str, Any]] = {}
        self.executions: Dict[str, WorkflowExecution] = {}
        
        # 动作注册
        self.actions: Dict[str, WorkflowAction] = {}
        self.conditions: Dict[str, WorkflowCondition] = {}
        
        # 执行队列
        self.execution_queue = asyncio.Queue()
        self._execution_task = None
        self._active = False
        
        # 注册内置动作和条件
        self._register_builtin_actions()
        self._register_builtin_conditions()
    
    def _register_builtin_actions(self):
        """注册内置动作"""
        # 文件处理动作
        self.register_action("file_scan", FileScanAction())
        self.register_action("file_rename", FileRenameAction())
        self.register_action("file_move", FileMoveAction())
        
        # 下载动作
        self.register_action("download_torrent", DownloadTorrentAction())
        self.register_action("add_download", AddDownloadAction())
        
        # 媒体识别动作
        self.register_action("identify_media", IdentifyMediaAction())
        self.register_action("search_metadata", SearchMetadataAction())
        
        # 通知动作
        self.register_action("send_notification", SendNotificationAction())
    
    def _register_builtin_conditions(self):
        """注册内置条件"""
        self.register_condition("file_exists", FileExistsCondition())
        self.register_condition("media_identified", MediaIdentifiedCondition())
        self.register_condition("download_completed", DownloadCompletedCondition())
    
    def register_action(self, action_name: str, action: WorkflowAction):
        """注册动作"""
        self.actions[action_name] = action
        logger.info("工作流动作已注册", action=action_name)
    
    def register_condition(self, condition_name: str, condition: WorkflowCondition):
        """注册条件"""
        self.conditions[condition_name] = condition
        logger.info("工作流条件已注册", condition=condition_name)
    
    def create_workflow(self, name: str, description: str, steps: List[WorkflowStep]) -> str:
        """创建工作流"""
        workflow_id = str(uuid.uuid4())
        
        workflow = {
            "id": workflow_id,
            "name": name,
            "description": description,
            "steps": [step.__dict__ for step in steps],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        self.workflows[workflow_id] = workflow
        
        logger.info("工作流已创建", workflow_id=workflow_id, name=name)
        return workflow_id
    
    async def execute_workflow(self, workflow_id: str, parameters: Dict[str, Any] = None) -> str:
        """执行工作流"""
        if workflow_id not in self.workflows:
            raise ValueError(f"工作流不存在: {workflow_id}")
        
        execution_id = str(uuid.uuid4())
        
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow_id,
            status=WorkflowStatus.PENDING,
            start_time=datetime.now()
        )
        
        self.executions[execution_id] = execution
        
        # 添加到执行队列
        await self.execution_queue.put({
            "execution_id": execution_id,
            "parameters": parameters or {}
        })
        
        logger.info("工作流执行已排队", execution_id=execution_id, workflow_id=workflow_id)
        return execution_id
    
    def start(self):
        """启动工作流引擎"""
        if self._active:
            return
        
        self._active = True
        self._execution_task = asyncio.create_task(self._process_executions())
        
        logger.info("增强工作流引擎已启动")
    
    def stop(self):
        """停止工作流引擎"""
        if not self._active:
            return
        
        self._active = False
        
        if self._execution_task:
            self._execution_task.cancel()
        
        logger.info("增强工作流引擎已停止")
    
    async def _process_executions(self):
        """处理执行队列"""
        while self._active:
            try:
                # 从队列获取执行任务
                task = await asyncio.wait_for(self.execution_queue.get(), timeout=1)
                
                execution_id = task["execution_id"]
                parameters = task["parameters"]
                
                # 执行工作流
                await self._execute_workflow(execution_id, parameters)
                
                self.execution_queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error("工作流执行处理异常", error=str(e))
    
    async def _execute_workflow(self, execution_id: str, parameters: Dict[str, Any]):
        """执行具体工作流"""
        execution = self.executions[execution_id]
        workflow = self.workflows[execution.workflow_id]
        
        execution.status = WorkflowStatus.RUNNING
        
        context = {
            "execution_id": execution_id,
            "workflow_id": execution.workflow_id,
            "parameters": parameters,
            "start_time": execution.start_time
        }
        
        try:
            # 执行每个步骤
            for step_data in workflow["steps"]:
                step = WorkflowStep(**step_data)
                
                # 检查条件
                if step.conditions:
                    should_execute = await self._evaluate_conditions(step.conditions, context)
                    if not should_execute:
                        execution.steps_executed.append({
                            "step_name": step.name,
                            "status": StepStatus.SKIPPED.value,
                            "timestamp": datetime.now().isoformat()
                        })
                        continue
                
                # 执行步骤
                step_result = await self._execute_step(step, context)
                
                execution.steps_executed.append({
                    "step_name": step.name,
                    "status": step_result["status"].value,
                    "result": step_result.get("result"),
                    "error": step_result.get("error"),
                    "timestamp": datetime.now().isoformat()
                })
                
                # 更新上下文
                context.update(step_result.get("context_updates", {}))
                
                # 检查步骤执行结果
                if step_result["status"] == StepStatus.FAILED:
                    execution.status = WorkflowStatus.FAILED
                    execution.error_message = step_result.get("error")
                    break
            
            # 设置完成状态
            if execution.status == WorkflowStatus.RUNNING:
                execution.status = WorkflowStatus.COMPLETED
                execution.end_time = datetime.now()
            
            # 发布工作流完成事件
            event = Event(
                event_type=EventType.WORKFLOW_COMPLETED,
                data={
                    "execution_id": execution_id,
                    "workflow_id": execution.workflow_id,
                    "status": execution.status.value,
                    "duration": (execution.end_time - execution.start_time).total_seconds()
                }
            )
            event_manager.publish(event)
            
            logger.info("工作流执行完成", 
                       execution_id=execution_id,
                       status=execution.status.value)
            
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error_message = str(e)
            execution.end_time = datetime.now()
            
            logger.error("工作流执行失败", 
                        execution_id=execution_id,
                        error=str(e))
    
    async def _execute_step(self, step: WorkflowStep, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个步骤"""
        if step.action not in self.actions:
            return {
                "status": StepStatus.FAILED,
                "error": f"未知动作: {step.action}"
            }
        
        action = self.actions[step.action]
        
        # 验证参数
        if not action.validate(step.parameters):
            return {
                "status": StepStatus.FAILED,
                "error": f"动作参数验证失败: {step.action}"
            }
        
        # 执行动作（带重试机制）
        for attempt in range(step.retry_count + 1):
            try:
                result = await asyncio.wait_for(
                    action.execute(step.parameters, context),
                    timeout=step.timeout
                )
                
                return {
                    "status": StepStatus.SUCCESS,
                    "result": result,
                    "context_updates": result.get("context_updates", {})
                }
                
            except asyncio.TimeoutError:
                if attempt < step.retry_count:
                    await asyncio.sleep(step.retry_delay)
                    continue
                return {
                    "status": StepStatus.FAILED,
                    "error": f"动作执行超时: {step.action}"
                }
            except Exception as e:
                if attempt < step.retry_count:
                    await asyncio.sleep(step.retry_delay)
                    continue
                return {
                    "status": StepStatus.FAILED,
                    "error": f"动作执行失败: {str(e)}"
                }
    
    async def _evaluate_conditions(self, conditions: List[str], context: Dict[str, Any]) -> bool:
        """评估条件"""
        for condition_str in conditions:
            # 解析条件字符串（格式：condition_name:parameters）
            parts = condition_str.split(":", 1)
            condition_name = parts[0]
            parameters_str = parts[1] if len(parts) > 1 else "{}"
            
            try:
                parameters = json.loads(parameters_str)
            except json.JSONDecodeError:
                parameters = {}
            
            if condition_name not in self.conditions:
                logger.warning("未知条件，跳过", condition=condition_name)
                continue
            
            condition = self.conditions[condition_name]
            
            try:
                result = await condition.evaluate(parameters, context)
                if not result:
                    return False
            except Exception as e:
                logger.error("条件评估失败", condition=condition_name, error=str(e))
                return False
        
        return True
    
    def get_execution_status(self, execution_id: str) -> Optional[WorkflowExecution]:
        """获取执行状态"""
        return self.executions.get(execution_id)
    
    def list_executions(self, workflow_id: str = None) -> List[WorkflowExecution]:
        """列出执行记录"""
        executions = list(self.executions.values())
        
        if workflow_id:
            executions = [e for e in executions if e.workflow_id == workflow_id]
        
        return sorted(executions, key=lambda x: x.start_time, reverse=True)


# 内置动作实现
class FileScanAction(WorkflowAction):
    """文件扫描动作"""
    
    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        scan_path = parameters.get("path", "")
        # 实现文件扫描逻辑
        return {"files_found": 0, "context_updates": {"scan_path": scan_path}}
    
    def validate(self, parameters: Dict[str, Any]) -> bool:
        return "path" in parameters


class FileRenameAction(WorkflowAction):
    """文件重命名动作"""
    
    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        # 实现文件重命名逻辑
        return {"renamed_files": 0}
    
    def validate(self, parameters: Dict[str, Any]) -> bool:
        return True


class DownloadTorrentAction(WorkflowAction):
    """下载种子动作"""
    
    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        # 实现种子下载逻辑
        return {"download_url": parameters.get("url")}
    
    def validate(self, parameters: Dict[str, Any]) -> bool:
        return "url" in parameters


class IdentifyMediaAction(WorkflowAction):
    """媒体识别动作"""
    
    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        # 实现媒体识别逻辑
        return {"media_type": "unknown", "title": "Unknown"}
    
    def validate(self, parameters: Dict[str, Any]) -> bool:
        return True


# 内置条件实现
class FileExistsCondition(WorkflowCondition):
    """文件存在条件"""
    
    async def evaluate(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> bool:
        file_path = parameters.get("path", "")
        import os
        return os.path.exists(file_path)


class MediaIdentifiedCondition(WorkflowCondition):
    """媒体已识别条件"""
    
    async def evaluate(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> bool:
        # 检查媒体是否已识别
        return context.get("media_identified", False)


# 全局工作流引擎实例
workflow_engine = EnhancedWorkflowEngine()