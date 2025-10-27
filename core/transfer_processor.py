#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件传输处理器
处理多存储之间的文件传输和同步
"""

import os
import time
import threading
import queue
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.file_manager import FileManager, TransferTask, TransferStatus


class TransferProcessor:
    """文件传输处理器"""
    
    def __init__(self, max_workers: int = 5):
        self.file_manager = FileManager()
        self.max_workers = max_workers
        self.task_queue = queue.Queue()
        self.worker_thread = None
        self.running = False
        self.completed_tasks = []
        self.failed_tasks = []
        
    def start(self):
        """启动传输处理器"""
        if self.running:
            return
            
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        
    def stop(self):
        """停止传输处理器"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
    
    def add_transfer_task(self, 
                         operation: str,
                         source_storage: str,
                         source_path: str,
                         target_storage: str,
                         target_path: str,
                         new_name: str = None) -> str:
        """添加传输任务"""
        if operation == "copy":
            return self.file_manager.copy_file(
                source_storage, source_path, target_storage, target_path, new_name
            )
        elif operation == "move":
            return self.file_manager.move_file(
                source_storage, source_path, target_storage, target_path, new_name
            )
        elif operation == "upload":
            return self.file_manager.upload_file(
                source_path, target_storage, target_path, new_name
            )
        elif operation == "download":
            return self.file_manager.download_file(
                source_storage, source_path, target_path, new_name
            )
        else:
            raise ValueError(f"不支持的传输操作: {operation}")
    
    def batch_transfer(self, 
                      tasks: List[Dict]) -> Dict[str, str]:
        """批量传输任务"""
        task_ids = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_task = {}
            
            for task in tasks:
                future = executor.submit(
                    self._execute_single_transfer,
                    task
                )
                future_to_task[future] = task
            
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    task_id = future.result()
                    task_ids[task.get('name', 'unknown')] = task_id
                except Exception as e:
                    task_ids[task.get('name', 'unknown')] = f"error: {str(e)}"
        
        return task_ids
    
    def _execute_single_transfer(self, task: Dict) -> str:
        """执行单个传输任务"""
        operation = task.get('operation', 'copy')
        source_storage = task.get('source_storage')
        source_path = task.get('source_path')
        target_storage = task.get('target_storage')
        target_path = task.get('target_path')
        new_name = task.get('new_name')
        
        return self.add_transfer_task(
            operation, source_storage, source_path, target_storage, target_path, new_name
        )
    
    def get_task_status(self, task_id: str) -> Optional[TransferTask]:
        """获取任务状态"""
        return self.file_manager.get_task_status(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        return self.file_manager.cancel_task(task_id)
    
    def list_tasks(self) -> List[TransferTask]:
        """列出所有任务"""
        return self.file_manager.list_tasks()
    
    def get_completed_tasks(self) -> List[TransferTask]:
        """获取已完成的任务"""
        return [task for task in self.file_manager.list_tasks() 
                if task.status == TransferStatus.COMPLETED]
    
    def get_failed_tasks(self) -> List[TransferTask]:
        """获取失败的任务"""
        return [task for task in self.file_manager.list_tasks() 
                if task.status == TransferStatus.FAILED]
    
    def get_running_tasks(self) -> List[TransferTask]:
        """获取运行中的任务"""
        return [task for task in self.file_manager.list_tasks() 
                if task.status == TransferStatus.RUNNING]
    
    def _worker_loop(self):
        """工作线程循环"""
        while self.running:
            try:
                # 检查任务状态并清理已完成的任务
                self._cleanup_completed_tasks()
                time.sleep(1)
            except Exception as e:
                print(f"传输处理器工作线程错误: {e}")
    
    def _cleanup_completed_tasks(self):
        """清理已完成的任务"""
        # 这里可以添加任务清理逻辑
        # 例如：移除超过一定时间的已完成任务
        pass


class SyncManager:
    """同步管理器"""
    
    def __init__(self):
        self.transfer_processor = TransferProcessor()
        self.sync_rules = []
        
    def add_sync_rule(self, 
                      name: str,
                      source_storage: str,
                      source_path: str,
                      target_storage: str,
                      target_path: str,
                      pattern: str = "*",
                      recursive: bool = True,
                      operation: str = "copy"):
        """添加同步规则"""
        rule = {
            'name': name,
            'source_storage': source_storage,
            'source_path': source_path,
            'target_storage': target_storage,
            'target_path': target_path,
            'pattern': pattern,
            'recursive': recursive,
            'operation': operation
        }
        self.sync_rules.append(rule)
    
    def remove_sync_rule(self, name: str):
        """移除同步规则"""
        self.sync_rules = [rule for rule in self.sync_rules if rule['name'] != name]
    
    def execute_sync(self, rule_name: str = None) -> Dict[str, str]:
        """执行同步"""
        tasks = []
        
        rules_to_sync = self.sync_rules
        if rule_name:
            rules_to_sync = [rule for rule in self.sync_rules if rule['name'] == rule_name]
        
        for rule in rules_to_sync:
            sync_tasks = self._generate_sync_tasks(rule)
            tasks.extend(sync_tasks)
        
        if tasks:
            return self.transfer_processor.batch_transfer(tasks)
        else:
            return {}
    
    def _generate_sync_tasks(self, rule: Dict) -> List[Dict]:
        """生成同步任务"""
        tasks = []
        
        try:
            # 获取源存储文件列表
            file_manager = self.transfer_processor.file_manager
            files = file_manager.list_files(rule['source_storage'], rule['source_path'])
            
            for file_item in files:
                if file_item.is_dir and rule['recursive']:
                    # 递归处理子目录
                    sub_tasks = self._generate_sync_tasks_for_directory(rule, file_item)
                    tasks.extend(sub_tasks)
                elif not file_item.is_dir:
                    # 处理文件
                    if self._match_pattern(file_item.name, rule['pattern']):
                        task = {
                            'name': f"{rule['name']}_{file_item.name}",
                            'operation': rule['operation'],
                            'source_storage': rule['source_storage'],
                            'source_path': file_item.path,
                            'target_storage': rule['target_storage'],
                            'target_path': rule['target_path'],
                            'new_name': file_item.name
                        }
                        tasks.append(task)
        
        except Exception as e:
            print(f"生成同步任务失败: {e}")
        
        return tasks
    
    def _generate_sync_tasks_for_directory(self, rule: Dict, dir_item) -> List[Dict]:
        """为目录生成同步任务"""
        tasks = []
        
        try:
            file_manager = self.transfer_processor.file_manager
            files = file_manager.list_files(rule['source_storage'], dir_item.path)
            
            for file_item in files:
                if file_item.is_dir and rule['recursive']:
                    # 递归处理子目录
                    sub_tasks = self._generate_sync_tasks_for_directory(rule, file_item)
                    tasks.extend(sub_tasks)
                elif not file_item.is_dir:
                    # 处理文件
                    if self._match_pattern(file_item.name, rule['pattern']):
                        # 保持目录结构
                        relative_path = Path(file_item.path).relative_to(rule['source_path'])
                        target_path = str(Path(rule['target_path']) / relative_path.parent)
                        
                        task = {
                            'name': f"{rule['name']}_{file_item.name}",
                            'operation': rule['operation'],
                            'source_storage': rule['source_storage'],
                            'source_path': file_item.path,
                            'target_storage': rule['target_storage'],
                            'target_path': target_path,
                            'new_name': file_item.name
                        }
                        tasks.append(task)
        
        except Exception as e:
            print(f"生成目录同步任务失败: {e}")
        
        return tasks
    
    def _match_pattern(self, filename: str, pattern: str) -> bool:
        """匹配文件名模式"""
        import fnmatch
        return fnmatch.fnmatch(filename, pattern)


class AutoOrganizer:
    """自动整理器"""
    
    def __init__(self):
        self.transfer_processor = TransferProcessor()
        self.organize_rules = []
        
    def add_organize_rule(self, 
                         name: str,
                         storage: str,
                         source_path: str,
                         target_base_path: str,
                         pattern: str = "*",
                         recursive: bool = True):
        """添加整理规则"""
        rule = {
            'name': name,
            'storage': storage,
            'source_path': source_path,
            'target_base_path': target_base_path,
            'pattern': pattern,
            'recursive': recursive
        }
        self.organize_rules.append(rule)
    
    def execute_organize(self, rule_name: str = None) -> Dict[str, str]:
        """执行整理"""
        tasks = []
        
        rules_to_organize = self.organize_rules
        if rule_name:
            rules_to_organize = [rule for rule in self.organize_rules 
                               if rule['name'] == rule_name]
        
        for rule in rules_to_organize:
            organize_tasks = self._generate_organize_tasks(rule)
            tasks.extend(organize_tasks)
        
        if tasks:
            return self.transfer_processor.batch_transfer(tasks)
        else:
            return {}
    
    def _generate_organize_tasks(self, rule: Dict) -> List[Dict]:
        """生成整理任务"""
        tasks = []
        
        try:
            from core.file_manager import MediaClassifier
            classifier = MediaClassifier()
            
            file_manager = self.transfer_processor.file_manager
            files = file_manager.list_files(rule['storage'], rule['source_path'])
            
            for file_item in files:
                if file_item.is_dir and rule['recursive']:
                    # 递归处理子目录
                    sub_tasks = self._generate_organize_tasks_for_directory(rule, file_item, classifier)
                    tasks.extend(sub_tasks)
                elif not file_item.is_dir:
                    # 处理文件
                    if self._match_pattern(file_item.name, rule['pattern']):
                        # 根据文件类型分类
                        target_folder = classifier.get_target_folder(
                            file_item.name, rule['target_base_path']
                        )
                        
                        task = {
                            'name': f"{rule['name']}_{file_item.name}",
                            'operation': 'move',
                            'source_storage': rule['storage'],
                            'source_path': file_item.path,
                            'target_storage': rule['storage'],
                            'target_path': target_folder,
                            'new_name': file_item.name
                        }
                        tasks.append(task)
        
        except Exception as e:
            print(f"生成整理任务失败: {e}")
        
        return tasks
    
    def _generate_organize_tasks_for_directory(self, rule: Dict, dir_item, classifier) -> List[Dict]:
        """为目录生成整理任务"""
        tasks = []
        
        try:
            file_manager = self.transfer_processor.file_manager
            files = file_manager.list_files(rule['storage'], dir_item.path)
            
            for file_item in files:
                if file_item.is_dir and rule['recursive']:
                    # 递归处理子目录
                    sub_tasks = self._generate_organize_tasks_for_directory(rule, file_item, classifier)
                    tasks.extend(sub_tasks)
                elif not file_item.is_dir:
                    # 处理文件
                    if self._match_pattern(file_item.name, rule['pattern']):
                        # 根据文件类型分类
                        target_folder = classifier.get_target_folder(
                            file_item.name, rule['target_base_path']
                        )
                        
                        task = {
                            'name': f"{rule['name']}_{file_item.name}",
                            'operation': 'move',
                            'source_storage': rule['storage'],
                            'source_path': file_item.path,
                            'target_storage': rule['storage'],
                            'target_path': target_folder,
                            'new_name': file_item.name
                        }
                        tasks.append(task)
        
        except Exception as e:
            print(f"生成目录整理任务失败: {e}")
        
        return tasks
    
    def _match_pattern(self, filename: str, pattern: str) -> bool:
        """匹配文件名模式"""
        import fnmatch
        return fnmatch.fnmatch(filename, pattern)