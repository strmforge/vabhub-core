#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版批量处理器
集成队列管理和速率限制
"""

import time
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
import uuid


class ProcessingStats:
    """处理统计"""
    
    def __init__(self):
        self.stats = {
            "total_files": 0,
            "processed_files": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "chinese_title_queries": 0,
            "template_renders": 0,
            "start_time": None,
            "end_time": None,
            "duration": 0,
        }
        self.errors = []
    
    def start(self, total_files: int):
        """开始处理"""
        self.stats["total_files"] = total_files
        self.stats["start_time"] = time.time()
    
    def update(self, success: bool, error: str = None):
        """更新统计"""
        self.stats["processed_files"] += 1
        
        if success:
            self.stats["success"] += 1
        else:
            self.stats["failed"] += 1
            if error:
                self.errors.append(error)
    
    def skip(self):
        """跳过文件"""
        self.stats["skipped"] += 1
        self.stats["processed_files"] += 1
    
    def finish(self):
        """完成处理"""
        self.stats["end_time"] = time.time()
        if self.stats["start_time"]:
            self.stats["duration"] = self.stats["end_time"] - self.stats["start_time"]
    
    def get_progress(self) -> float:
        """获取进度（0-1）"""
        if self.stats["total_files"] == 0:
            return 0.0
        return self.stats["processed_files"] / self.stats["total_files"]
    
    def get_eta(self) -> float:
        """获取预计剩余时间（秒）"""
        if self.stats["processed_files"] == 0:
            return 0.0
        
        elapsed = time.time() - self.stats["start_time"]
        avg_time = elapsed / self.stats["processed_files"]
        remaining = self.stats["total_files"] - self.stats["processed_files"]
        
        return avg_time * remaining
    
    def get_summary(self) -> Dict[str, Any]:
        """获取统计摘要"""
        return {
            **self.stats,
            "progress": self.get_progress(),
            "eta": self.get_eta(),
            "success_rate": self.stats["success"] / self.stats["processed_files"] if self.stats["processed_files"] > 0 else 0,
            "errors": self.errors,
        }


class EnhancedBatchProcessor:
    """增强版批量处理器"""
    
    def __init__(
        self,
        use_queue: bool = False,
        use_rate_limit: bool = False,
        max_workers: int = 4,
        rate_limit: int = 10
    ):
        from core.chinese_title_resolver import ChineseTitleResolver
        from core.enhanced_recognizer import EnhancedRecognizer
        
        self.recognizer = EnhancedRecognizer()
        self.title_resolver = ChineseTitleResolver()
        self.stats = ProcessingStats()
        
        # 队列管理和速率限制
        self.use_queue = use_queue
        self.use_rate_limit = use_rate_limit
        self.queue_manager = None
        self.rate_limiter = None
        
        if use_queue:
            from core.enhanced_queue_manager import get_enhanced_queue_manager
            self.queue_manager = get_enhanced_queue_manager(max_workers=max_workers)
        
        if use_rate_limit:
            from core.rate_limiter import RateLimiter
            self.rate_limiter = RateLimiter(
                algorithm='token_bucket',
                max_requests=rate_limit,
                time_window=1.0
            )
        
        # 默认配置
        self.default_template = {
            'movie': 'movie_default',
            'tv': 'tv_default',
        }
    
    def process_batch(
        self,
        file_paths: List[str],
        progress_callback: Optional[Callable] = None,
        template_name: str = None
    ) -> Dict[str, Any]:
        """
        批量处理文件
        
        Args:
            file_paths: 文件路径列表
            progress_callback: 进度回调函数 callback(progress, current_file, result)
            template_name: 模板名称（可选）
            
        Returns:
            处理结果
        """
        # 初始化统计
        self.stats.start(len(file_paths))
        
        results = []
        
        for i, file_path in enumerate(file_paths):
            try:
                # 处理单个文件
                result = self._process_single_file(file_path, template_name)
                
                # 更新统计
                self.stats.update(result['success'], result.get('error'))
                
                # 记录结果
                results.append(result)
                
                # 计算进度
                progress = (i + 1) / len(file_paths)
                
                # 进度回调
                if progress_callback:
                    progress_callback(progress, file_path, result)
                
            except Exception as e:
                error_msg = f"处理失败: {file_path} - {e}"
                self.stats.update(False, error_msg)
                
                results.append({
                    'file_path': file_path,
                    'success': False,
                    'error': str(e),
                    'message': error_msg
                })
                
                print(error_msg)
        
        # 完成处理
        self.stats.finish()
        
        return {
            'results': results,
            'stats': self.stats.get_summary()
        }
    
    def process_batch_with_queue(
        self,
        file_paths: List[str],
        progress_callback: Optional[Callable] = None,
        template_name: str = None,
        priority: int = 5
    ) -> Dict[str, Any]:
        """
        使用队列管理器批量处理文件
        
        Args:
            file_paths: 文件路径列表
            progress_callback: 进度回调函数
            template_name: 模板名称
            priority: 任务优先级（1-10）
            
        Returns:
            处理结果
        """
        if not self.use_queue or not self.queue_manager:
            # 降级到普通批量处理
            return self.process_batch(file_paths, progress_callback, template_name)
        
        # 初始化统计
        self.stats.start(len(file_paths))
        
        results = []
        completed_count = 0
        
        # 提交所有任务到队列
        task_ids = []
        for i, file_path in enumerate(file_paths):
            task_id = f"process-{uuid.uuid4().hex[:8]}"
            task_ids.append(task_id)
            
            # 应用速率限制
            if self.use_rate_limit and self.rate_limiter:
                self.rate_limiter.wait(timeout=30)
            
            # 提交任务
            self.queue_manager.submit(
                task_id=task_id,
                data={'file_path': file_path, 'template_name': template_name},
                callback=lambda data: self._process_single_file(data['file_path'], data['template_name']),
                priority=priority,
                timeout=60
            )
        
        # 等待所有任务完成
        print(f"✓ 已提交 {len(task_ids)} 个任务到队列")
        
        while completed_count < len(task_ids):
            time.sleep(0.5)
            
            # 检查任务状态
            for task_id in task_ids:
                task = self.queue_manager.get_task(task_id)
                if task and task.status in [2, 3, 4]:  # COMPLETED, FAILED, TIMEOUT
                    if task.task_id not in [r.get('task_id') for r in results]:
                        result = task.result if task.result else {
                            'file_path': task.data['file_path'],
                            'success': False,
                            'error': task.error or 'Unknown error'
                        }
                        result['task_id'] = task.task_id
                        results.append(result)
                        completed_count += 1
                        
                        # 更新统计
                        self.stats.update(result.get('success', False), result.get('error'))
                        
                        # 进度回调
                        if progress_callback:
                            progress = completed_count / len(task_ids)
                            progress_callback(progress, task.data['file_path'], result)
        
        # 完成处理
        self.stats.finish()
        
        return {
            'results': results,
            'stats': self.stats.get_summary()
        }
    
    def _process_single_file(self, file_path: str, template_name: str = None) -> Dict[str, Any]:
        """处理单个文件"""
        try:
            # 1. 识别文件
            print(f"识别文件: {Path(file_path).name}")
            info = self.recognizer.recognize(Path(file_path).name)
            
            # 统计中文标题查询
            if info.original_title:
                self.stats.stats["chinese_title_queries"] += 1
            
            # 2. 确定模板
            if not template_name:
                template_name = self.default_template['tv'] if info.media_type == 'tv' else self.default_template['movie']
            
            # 3. 生成新文件名
            context = {
                'title': info.title,
                'year': info.year,
                'season': info.season,
                'episode': info.episode,
                'resolution': info.quality,
                'video_codec': '',
                'audio_codec': '',
                'source': info.source,
                'ext': Path(file_path).suffix[1:],  # 移除点号
            }
            
            # 使用简单模板生成新文件名
            if info.media_type == 'tv':
                if info.season and info.episode:
                    new_name = f"{info.title} S{info.season:02d}E{info.episode:02d}.{Path(file_path).suffix[1:]}"
                elif info.season:
                    new_name = f"{info.title} S{info.season:02d}.{Path(file_path).suffix[1:]}"
                else:
                    new_name = f"{info.title}.{Path(file_path).suffix[1:]}"
            else:
                if info.year:
                    new_name = f"{info.title} ({info.year}).{Path(file_path).suffix[1:]}"
                else:
                    new_name = f"{info.title}.{Path(file_path).suffix[1:]}"
            
            self.stats.stats["template_renders"] += 1
            
            # 4. 返回结果
            return {
                'file_path': file_path,
                'success': True,
                'original_name': Path(file_path).name,
                'new_name': new_name,
                'info': {
                    'title': info.title,
                    'year': info.year,
                    'season': info.season,
                    'episode': info.episode,
                    'media_type': info.media_type,
                    'quality': info.quality,
                    'source': info.source,
                    'group': info.group,
                    'confidence': info.confidence
                },
                'template': template_name,
                'quality_score': info.confidence,
                'message': f"成功: {Path(file_path).name} → {new_name}"
            }
            
        except Exception as e:
            return {
                'file_path': file_path,
                'success': False,
                'error': str(e),
                'message': f"失败: {e}"
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.get_summary()
        
        # 添加队列统计
        if self.use_queue and self.queue_manager:
            stats['queue_stats'] = self.queue_manager.get_stats()
        
        # 添加速率限制统计
        if self.use_rate_limit and self.rate_limiter:
            stats['rate_limit_stats'] = self.rate_limiter.get_stats()
        
        return stats


# 全局实例
_enhanced_batch_processor = None


def get_enhanced_batch_processor(
    use_queue: bool = False,
    use_rate_limit: bool = False
) -> EnhancedBatchProcessor:
    """获取增强版批量处理器实例"""
    global _enhanced_batch_processor
    if _enhanced_batch_processor is None:
        _enhanced_batch_processor = EnhancedBatchProcessor(
            use_queue=use_queue,
            use_rate_limit=use_rate_limit
        )
    return _enhanced_batch_processor