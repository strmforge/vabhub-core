"""
智能历史记录管理系统 - 基于变异版本media-renamer1的成熟实现
提供完整的操作审计、版本控制、一键回滚功能
"""

import json
import time
import hashlib
import secrets
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class OperationType(Enum):
    """操作类型枚举"""
    RENAME = "rename"
    DELETE = "delete"
    MOVE = "move"
    COPY = "copy"
    BATCH = "batch"
    CONFIG = "config"

class HistoryStatus(Enum):
    """历史记录状态"""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    ROLLED_BACK = "rolled_back"

@dataclass
class FileOperation:
    """文件操作记录"""
    operation_id: str
    user_id: str
    operation_type: OperationType
    source_path: str
    target_path: str
    file_size: int
    file_hash: str
    timestamp: datetime
    status: HistoryStatus
    details: Dict[str, Any]

@dataclass
class BatchOperation:
    """批量操作记录"""
    batch_id: str
    user_id: str
    operation_type: OperationType
    file_operations: List[FileOperation]
    timestamp: datetime
    status: HistoryStatus
    summary: Dict[str, Any]

class HistoryManager:
    """历史记录管理器"""
    
    def __init__(self, storage_dir: str = "data/history"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 内存缓存
        self.file_operations: Dict[str, FileOperation] = {}
        self.batch_operations: Dict[str, BatchOperation] = {}
        
        # 配置
        self.max_history_days = 365  # 保留1年历史
        self.max_operations = 10000  # 最大操作记录数
        
        # 加载历史数据
        self._load_history()
    
    def _load_history(self):
        """加载历史数据"""
        try:
            # 加载文件操作历史
            file_ops_file = self.storage_dir / "file_operations.json"
            if file_ops_file.exists():
                with open(file_ops_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for op_data in data:
                        op = FileOperation(**op_data)
                        self.file_operations[op.operation_id] = op
            
            # 加载批量操作历史
            batch_ops_file = self.storage_dir / "batch_operations.json"
            if batch_ops_file.exists():
                with open(batch_ops_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for batch_data in data:
                        batch = BatchOperation(**batch_data)
                        self.batch_operations[batch.batch_id] = batch
            
            logger.info(f"加载历史记录: {len(self.file_operations)} 文件操作, {len(self.batch_operations)} 批量操作")
            
        except Exception as e:
            logger.error(f"加载历史记录失败: {e}")
    
    def _save_history(self):
        """保存历史数据"""
        try:
            # 保存文件操作历史
            file_ops_file = self.storage_dir / "file_operations.json"
            with open(file_ops_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(op) for op in self.file_operations.values()], f, 
                         indent=2, default=str)
            
            # 保存批量操作历史
            batch_ops_file = self.storage_dir / "batch_operations.json"
            with open(batch_ops_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(batch) for batch in self.batch_operations.values()], f, 
                         indent=2, default=str)
            
        except Exception as e:
            logger.error(f"保存历史记录失败: {e}")
    
    def _generate_id(self) -> str:
        """生成唯一ID"""
        return f"{int(time.time())}_{secrets.token_hex(8)}"
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希"""
        try:
            path = Path(file_path)
            if not path.exists():
                return ""
            
            # 使用文件大小和修改时间作为简化哈希
            stat = path.stat()
            content = f"{path.name}_{stat.st_size}_{stat.st_mtime}"
            return hashlib.md5(content.encode()).hexdigest()
            
        except Exception as e:
            logger.warning(f"计算文件哈希失败 {file_path}: {e}")
            return ""
    
    def record_file_operation(self, user_id: str, operation_type: OperationType, 
                             source_path: str, target_path: str = "", 
                             details: Dict[str, Any] = None) -> str:
        """记录文件操作"""
        operation_id = self._generate_id()
        
        # 获取文件信息
        source_path_obj = Path(source_path)
        file_size = source_path_obj.stat().st_size if source_path_obj.exists() else 0
        file_hash = self._calculate_file_hash(source_path)
        
        # 创建操作记录
        operation = FileOperation(
            operation_id=operation_id,
            user_id=user_id,
            operation_type=operation_type,
            source_path=source_path,
            target_path=target_path,
            file_size=file_size,
            file_hash=file_hash,
            timestamp=datetime.now(),
            status=HistoryStatus.SUCCESS,
            details=details or {}
        )
        
        # 保存记录
        self.file_operations[operation_id] = operation
        
        # 清理过期记录
        self._cleanup_old_records()
        
        # 保存到文件
        self._save_history()
        
        logger.info(f"记录文件操作: {operation_type.value} {source_path} -> {target_path}")
        return operation_id
    
    def record_batch_operation(self, user_id: str, operation_type: OperationType,
                              file_operations: List[FileOperation], 
                              summary: Dict[str, Any] = None) -> str:
        """记录批量操作"""
        batch_id = self._generate_id()
        
        batch_operation = BatchOperation(
            batch_id=batch_id,
            user_id=user_id,
            operation_type=operation_type,
            file_operations=file_operations,
            timestamp=datetime.now(),
            status=HistoryStatus.SUCCESS,
            summary=summary or {}
        )
        
        self.batch_operations[batch_id] = batch_operation
        
        # 清理过期记录
        self._cleanup_old_records()
        
        # 保存到文件
        self._save_history()
        
        logger.info(f"记录批量操作: {operation_type.value} 包含 {len(file_operations)} 个文件")
        return batch_id
    
    def _cleanup_old_records(self):
        """清理过期记录"""
        current_time = time.time()
        max_timestamp = current_time - (self.max_history_days * 86400)
        
        # 清理文件操作记录
        old_file_ops = [
            op_id for op_id, op in self.file_operations.items()
            if op.timestamp.timestamp() < max_timestamp
        ]
        for op_id in old_file_ops:
            del self.file_operations[op_id]
        
        # 清理批量操作记录
        old_batch_ops = [
            batch_id for batch_id, batch in self.batch_operations.items()
            if batch.timestamp.timestamp() < max_timestamp
        ]
        for batch_id in old_batch_ops:
            del self.batch_operations[batch_id]
        
        # 限制记录数量
        if len(self.file_operations) > self.max_operations:
            # 保留最新的记录
            sorted_ops = sorted(self.file_operations.items(), 
                               key=lambda x: x[1].timestamp, reverse=True)
            self.file_operations = dict(sorted_ops[:self.max_operations])
        
        if len(self.batch_operations) > self.max_operations:
            # 保留最新的记录
            sorted_batches = sorted(self.batch_operations.items(), 
                                   key=lambda x: x[1].timestamp, reverse=True)
            self.batch_operations = dict(sorted_batches[:self.max_operations])
    
    def get_operation_history(self, user_id: str = None, 
                             operation_type: OperationType = None,
                             start_time: datetime = None, 
                             end_time: datetime = None) -> List[FileOperation]:
        """获取操作历史"""
        operations = list(self.file_operations.values())
        
        if user_id:
            operations = [op for op in operations if op.user_id == user_id]
        if operation_type:
            operations = [op for op in operations if op.operation_type == operation_type]
        if start_time:
            operations = [op for op in operations if op.timestamp >= start_time]
        if end_time:
            operations = [op for op in operations if op.timestamp <= end_time]
        
        # 按时间倒序排列
        operations.sort(key=lambda x: x.timestamp, reverse=True)
        return operations
    
    def get_batch_history(self, user_id: str = None,
                         operation_type: OperationType = None,
                         start_time: datetime = None,
                         end_time: datetime = None) -> List[BatchOperation]:
        """获取批量操作历史"""
        batches = list(self.batch_operations.values())
        
        if user_id:
            batches = [batch for batch in batches if batch.user_id == user_id]
        if operation_type:
            batches = [batch for batch in batches if batch.operation_type == operation_type]
        if start_time:
            batches = [batch for batch in batches if batch.timestamp >= start_time]
        if end_time:
            batches = [batch for batch in batches if batch.timestamp <= end_time]
        
        # 按时间倒序排列
        batches.sort(key=lambda x: x.timestamp, reverse=True)
        return batches
    
    def rollback_operation(self, operation_id: str) -> bool:
        """回滚单个操作"""
        if operation_id not in self.file_operations:
            logger.warning(f"操作记录不存在: {operation_id}")
            return False
        
        operation = self.file_operations[operation_id]
        
        try:
            # 根据操作类型执行回滚
            if operation.operation_type == OperationType.RENAME:
                # 重命名回滚：将目标文件重命名回源文件名
                if operation.target_path and Path(operation.target_path).exists():
                    Path(operation.target_path).rename(operation.source_path)
                    logger.info(f"回滚重命名: {operation.target_path} -> {operation.source_path}")
            
            elif operation.operation_type == OperationType.MOVE:
                # 移动回滚：将文件移回原位置
                if operation.target_path and Path(operation.target_path).exists():
                    Path(operation.target_path).rename(operation.source_path)
                    logger.info(f"回滚移动: {operation.target_path} -> {operation.source_path}")
            
            elif operation.operation_type == OperationType.DELETE:
                # 删除操作无法回滚，只能记录
                logger.warning(f"删除操作无法回滚: {operation.source_path}")
                return False
            
            # 更新操作状态
            operation.status = HistoryStatus.ROLLED_BACK
            operation.details["rollback_time"] = datetime.now()
            
            # 保存历史记录
            self._save_history()
            
            logger.info(f"成功回滚操作: {operation_id}")
            return True
            
        except Exception as e:
            logger.error(f"回滚操作失败 {operation_id}: {e}")
            return False
    
    def rollback_batch_operation(self, batch_id: str) -> Dict[str, Any]:
        """回滚批量操作"""
        if batch_id not in self.batch_operations:
            logger.warning(f"批量操作记录不存在: {batch_id}")
            return {"success": False, "message": "批量操作记录不存在"}
        
        batch = self.batch_operations[batch_id]
        results = {
            "total_operations": len(batch.file_operations),
            "successful_rollbacks": 0,
            "failed_rollbacks": 0,
            "details": []
        }
        
        # 按时间倒序回滚（后进先出）
        sorted_operations = sorted(batch.file_operations, 
                                  key=lambda x: x.timestamp, reverse=True)
        
        for operation in sorted_operations:
            try:
                success = self.rollback_operation(operation.operation_id)
                if success:
                    results["successful_rollbacks"] += 1
                    results["details"].append({
                        "operation_id": operation.operation_id,
                        "status": "success",
                        "message": f"成功回滚: {operation.source_path}"
                    })
                else:
                    results["failed_rollbacks"] += 1
                    results["details"].append({
                        "operation_id": operation.operation_id,
                        "status": "failed",
                        "message": f"回滚失败: {operation.source_path}"
                    })
            except Exception as e:
                results["failed_rollbacks"] += 1
                results["details"].append({
                    "operation_id": operation.operation_id,
                    "status": "error",
                    "message": f"回滚异常: {str(e)}"
                })
        
        # 更新批量操作状态
        batch.status = HistoryStatus.ROLLED_BACK
        batch.summary["rollback_results"] = results
        
        # 保存历史记录
        self._save_history()
        
        results["success"] = results["failed_rollbacks"] == 0
        logger.info(f"批量回滚完成: 成功 {results['successful_rollbacks']}, 失败 {results['failed_rollbacks']}")
        return results
    
    def get_statistics(self, user_id: str = None) -> Dict[str, Any]:
        """获取统计信息"""
        operations = self.get_operation_history(user_id)
        batches = self.get_batch_history(user_id)
        
        # 按操作类型统计
        type_stats = {}
        for op_type in OperationType:
            count = len([op for op in operations if op.operation_type == op_type])
            type_stats[op_type.value] = count
        
        # 按状态统计
        status_stats = {}
        for status in HistoryStatus:
            count = len([op for op in operations if op.status == status])
            status_stats[status.value] = count
        
        # 时间范围统计
        if operations:
            earliest_op = min(operations, key=lambda x: x.timestamp)
            latest_op = max(operations, key=lambda x: x.timestamp)
            time_range = {
                "earliest": earliest_op.timestamp,
                "latest": latest_op.timestamp,
                "total_days": (latest_op.timestamp - earliest_op.timestamp).days
            }
        else:
            time_range = {"earliest": None, "latest": None, "total_days": 0}
        
        return {
            "total_operations": len(operations),
            "total_batches": len(batches),
            "operation_type_stats": type_stats,
            "status_stats": status_stats,
            "time_range": time_range,
            "storage_size": len(self.file_operations) + len(self.batch_operations)
        }