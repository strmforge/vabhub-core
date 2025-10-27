#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流引擎
参考StrataMedia的完整工作流设计
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum

from .config_loader import get_config_loader
from .plugin_base import get_plugin_manager


class WorkflowStage(Enum):
    """工作流阶段"""
    SCAN = "scan"
    CLASSIFY = "classify"
    RENAME = "rename"
    METADATA = "metadata"
    STRM = "strm"
    NOTIFY = "notify"


@dataclass
class FileInfo:
    """文件信息"""
    path: str
    filename: str
    size: int
    extension: str
    kind: str = "unknown"
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class WorkflowResult:
    """工作流结果"""
    file_info: FileInfo
    stage: WorkflowStage
    success: bool
    message: str
    data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}


class WorkflowEngine:
    """工作流引擎"""
    
    def __init__(self):
        self.config_loader = get_config_loader()
        self.plugin_manager = get_plugin_manager()
        self.executor = ThreadPoolExecutor(
            max_workers=self.config_loader.get('workflow.max_workers', 4)
        )
        
        # 注册阶段处理器
        self.stage_handlers = {
            WorkflowStage.SCAN: self._scan_stage,
            WorkflowStage.CLASSIFY: self._classify_stage,
            WorkflowStage.RENAME: self._rename_stage,
            WorkflowStage.METADATA: self._metadata_stage,
            WorkflowStage.STRM: self._strm_stage,
            WorkflowStage.NOTIFY: self._notify_stage
        }
    
    async def process_file(self, file_path: str, stages: List[WorkflowStage] = None) -> List[WorkflowResult]:
        """处理单个文件"""
        if stages is None:
            stages = self._get_default_stages()
        
        file_info = FileInfo(
            path=file_path,
            filename=Path(file_path).name,
            size=Path(file_path).stat().st_size if Path(file_path).exists() else 0,
            extension=Path(file_path).suffix.lower()
        )
        
        results = []
        
        for stage in stages:
            try:
                result = await self._process_stage(stage, file_info)
                results.append(result)
                
                # 如果阶段失败且不是最后一个阶段，可以选择继续或停止
                if not result.success and stage != stages[-1]:
                    print(f"阶段 {stage.value} 失败: {result.message}")
                    # 可以根据配置决定是否继续
                    if self.config_loader.get('workflow.continue_on_error', False):
                        continue
                    else:
                        break
                
                # 更新文件信息用于下一个阶段
                file_info = self._update_file_info(file_info, result)
                
            except Exception as e:
                results.append(WorkflowResult(
                    file_info=file_info,
                    stage=stage,
                    success=False,
                    message=f"阶段处理异常: {str(e)}"
                ))
                break
        
        return results
    
    async def process_batch(self, file_paths: List[str], 
                           stages: List[WorkflowStage] = None,
                           progress_callback: Callable = None) -> Dict[str, List[WorkflowResult]]:
        """批量处理文件"""
        if stages is None:
            stages = self._get_default_stages()
        
        batch_size = self.config_loader.get('workflow.batch_size', 10)
        results = {}
        
        # 分批处理
        for i in range(0, len(file_paths), batch_size):
            batch = file_paths[i:i + batch_size]
            
            # 并行处理批次
            batch_tasks = [
                self.process_file(file_path, stages) 
                for file_path in batch
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # 收集结果
            for file_path, file_results in zip(batch, batch_results):
                if isinstance(file_results, Exception):
                    results[file_path] = [WorkflowResult(
                        file_info=FileInfo(path=file_path, filename=Path(file_path).name, size=0, extension=""),
                        stage=WorkflowStage.SCAN,
                        success=False,
                        message=f"处理异常: {str(file_results)}"
                    )]
                else:
                    results[file_path] = file_results
            
            # 进度回调
            if progress_callback:
                progress = (i + len(batch)) / len(file_paths) * 100
                progress_callback(progress, f"已处理 {i + len(batch)}/{len(file_paths)} 个文件")
        
        return results
    
    def _get_default_stages(self) -> List[WorkflowStage]:
        """获取默认阶段顺序"""
        stage_names = self.config_loader.get('workflow.stages', [
            'scan', 'classify', 'rename', 'metadata', 'strm', 'notify'
        ])
        
        stages = []
        for name in stage_names:
            try:
                stages.append(WorkflowStage(name))
            except ValueError:
                print(f"警告: 未知的工作流阶段: {name}")
        
        return stages
    
    async def _process_stage(self, stage: WorkflowStage, file_info: FileInfo) -> WorkflowResult:
        """处理单个阶段"""
        handler = self.stage_handlers.get(stage)
        if not handler:
            return WorkflowResult(
                file_info=file_info,
                stage=stage,
                success=False,
                message=f"未找到阶段处理器: {stage.value}"
            )
        
        # 在线程池中执行阻塞操作
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(self.executor, handler, file_info)
        return result
    
    def _scan_stage(self, file_info: FileInfo) -> WorkflowResult:
        """扫描阶段"""
        # 检查文件是否存在
        if not Path(file_info.path).exists():
            return WorkflowResult(
                file_info=file_info,
                stage=WorkflowStage.SCAN,
                success=False,
                message="文件不存在"
            )
        
        # 使用云存储插件扫描（如果配置）
        cloud_plugins = self.plugin_manager.get_plugins_by_type('cloud')
        for plugin in cloud_plugins:
            try:
                # 这里可以集成云存储扫描逻辑
                pass
            except Exception as e:
                print(f"云存储插件 {plugin.name} 扫描失败: {e}")
        
        return WorkflowResult(
            file_info=file_info,
            stage=WorkflowStage.SCAN,
            success=True,
            message="扫描完成"
        )
    
    def _classify_stage(self, file_info: FileInfo) -> WorkflowResult:
        """分类阶段"""
        from .enhanced_recognizer import EnhancedRecognizer
        
        try:
            recognizer = EnhancedRecognizer()
            
            # 应用分类规则
            rules = self.config_loader.get_classifier_rules()
            special_rules = self.config_loader.get_special_rules()
            
            # 检查特殊规则
            for rule in special_rules:
                if self._matches_rule(file_info, rule.get('when', {})):
                    action = rule.get('action', 'skip')
                    if action == 'skip':
                        return WorkflowResult(
                            file_info=file_info,
                            stage=WorkflowStage.CLASSIFY,
                            success=True,
                            message=f"跳过文件: {rule.get('reason', '特殊规则')}",
                            data={'action': 'skip'}
                        )
            
            # 应用分类规则
            for rule in rules:
                if self._matches_rule(file_info, rule.get('when', {})):
                    file_info.kind = rule['set'].get('kind', 'unknown')
                    file_info.tags = rule['set'].get('tags', [])
                    
                    return WorkflowResult(
                        file_info=file_info,
                        stage=WorkflowStage.CLASSIFY,
                        success=True,
                        message=f"分类为: {file_info.kind}",
                        data={'kind': file_info.kind, 'tags': file_info.tags}
                    )
            
            # 默认分类
            default_config = self.config_loader.get('classifiers.default', {})
            file_info.kind = default_config.get('kind', 'unknown')
            file_info.tags = default_config.get('tags', ['unknown'])
            
            return WorkflowResult(
                file_info=file_info,
                stage=WorkflowStage.CLASSIFY,
                success=True,
                message=f"默认分类为: {file_info.kind}",
                data={'kind': file_info.kind, 'tags': file_info.tags}
            )
            
        except Exception as e:
            return WorkflowResult(
                file_info=file_info,
                stage=WorkflowStage.CLASSIFY,
                success=False,
                message=f"分类失败: {str(e)}"
            )
    
    def _rename_stage(self, file_info: FileInfo) -> WorkflowResult:
        """重命名阶段"""
        from .enhanced_batch_processor import EnhancedBatchProcessor
        
        try:
            processor = EnhancedBatchProcessor()
            
            # 根据文件类型选择模板
            templates = self.config_loader.get_templates()
            template_key = file_info.kind if file_info.kind in templates else 'video'
            template = templates.get(template_key, "{title}")
            
            # 这里集成您现有的重命名逻辑
            result = processor.process_single_file(file_info.path)
            
            if result.get('success'):
                return WorkflowResult(
                    file_info=file_info,
                    stage=WorkflowStage.RENAME,
                    success=True,
                    message=f"重命名成功: {result.get('new_name', '')}",
                    data={'new_name': result.get('new_name')}
                )
            else:
                return WorkflowResult(
                    file_info=file_info,
                    stage=WorkflowStage.RENAME,
                    success=False,
                    message=result.get('message', '重命名失败')
                )
                
        except Exception as e:
            return WorkflowResult(
                file_info=file_info,
                stage=WorkflowStage.RENAME,
                success=False,
                message=f"重命名异常: {str(e)}"
            )
    
    def _metadata_stage(self, file_info: FileInfo) -> WorkflowResult:
        """元数据阶段"""
        try:
            # 根据文件类型选择元数据插件
            if file_info.kind in ['movie', 'tv', 'anime']:
                plugins = self.plugin_manager.get_plugins_by_type('metadata')
            elif file_info.kind == 'music':
                plugins = self.plugin_manager.get_plugins_by_type('music_metadata')
            else:
                plugins = []
            
            metadata = {}
            for plugin in plugins:
                try:
                    if hasattr(plugin, 'fetch_video'):
                        # 视频元数据
                        plugin_metadata = plugin.fetch_video(file_info.filename)
                        metadata.update(plugin_metadata)
                    elif hasattr(plugin, 'search_track'):
                        # 音乐元数据
                        plugin_metadata = plugin.search_track("", file_info.filename)
                        metadata.update(plugin_metadata)
                except Exception as e:
                    print(f"元数据插件 {plugin.name} 失败: {e}")
            
            file_info.metadata = metadata
            
            return WorkflowResult(
                file_info=file_info,
                stage=WorkflowStage.METADATA,
                success=bool(metadata),
                message=f"获取到 {len(metadata)} 条元数据" if metadata else "未获取到元数据",
                data={'metadata': metadata}
            )
            
        except Exception as e:
            return WorkflowResult(
                file_info=file_info,
                stage=WorkflowStage.METADATA,
                success=False,
                message=f"元数据获取异常: {str(e)}"
            )
    
    def _strm_stage(self, file_info: FileInfo) -> WorkflowResult:
        """STRM生成阶段"""
        try:
            # 检查是否启用STRM
            strm_enabled = self.config_loader.get('strm.enable', False)
            if not strm_enabled or file_info.kind not in ['movie', 'tv']:
                return WorkflowResult(
                    file_info=file_info,
                    stage=WorkflowStage.STRM,
                    success=True,
                    message="STRM生成跳过",
                    data={'skipped': True}
                )
            
            # 生成STRM文件逻辑
            strm_prefix = self.config_loader.get('strm.prefix', 'strm://')
            strm_content = f"{strm_prefix}{file_info.path}"
            
            strm_path = Path(file_info.path).with_suffix('.strm')
            with open(strm_path, 'w', encoding='utf-8') as f:
                f.write(strm_content)
            
            return WorkflowResult(
                file_info=file_info,
                stage=WorkflowStage.STRM,
                success=True,
                message=f"STRM文件生成: {strm_path.name}",
                data={'strm_path': str(strm_path)}
            )
            
        except Exception as e:
            return WorkflowResult(
                file_info=file_info,
                stage=WorkflowStage.STRM,
                success=False,
                message=f"STRM生成异常: {str(e)}"
            )
    
    def _notify_stage(self, file_info: FileInfo) -> WorkflowResult:
        """通知阶段"""
        try:
            # 获取通知插件
            notifiers = self.plugin_manager.get_plugins_by_type('notifier')
            
            success_count = 0
            for notifier in notifiers:
                try:
                    if notifier.notify(file_info.path, 'default'):
                        success_count += 1
                except Exception as e:
                    print(f"通知插件 {notifier.name} 失败: {e}")
            
            return WorkflowResult(
                file_info=file_info,
                stage=WorkflowStage.NOTIFY,
                success=success_count > 0,
                message=f"通知了 {success_count}/{len(notifiers)} 个媒体库",
                data={'notified_count': success_count}
            )
            
        except Exception as e:
            return WorkflowResult(
                file_info=file_info,
                stage=WorkflowStage.NOTIFY,
                success=False,
                message=f"通知异常: {str(e)}"
            )
    
    def _matches_rule(self, file_info: FileInfo, conditions: Dict[str, Any]) -> bool:
        """检查文件是否匹配规则条件"""
        # 扩展名匹配
        if 'ext_in' in conditions:
            if file_info.extension not in conditions['ext_in']:
                return False
        
        # 路径包含匹配
        if 'path_contains' in conditions:
            contains_any = any(keyword in file_info.path for keyword in conditions['path_contains'])
            if not contains_any:
                return False
        
        # 路径不包含匹配
        if 'path_not_contains' in conditions:
            contains_any = any(keyword in file_info.path for keyword in conditions['path_not_contains'])
            if contains_any:
                return False
        
        # 正则匹配
        if 'regex_match' in conditions:
            import re
            if not re.search(conditions['regex_match'], file_info.filename, re.IGNORECASE):
                return False
        
        # 大小匹配
        if 'size_gt' in conditions:
            size_limit = self._parse_size(conditions['size_gt'])
            if file_info.size <= size_limit:
                return False
        
        if 'size_lt' in conditions:
            size_limit = self._parse_size(conditions['size_lt'])
            if file_info.size >= size_limit:
                return False
        
        return True
    
    def _parse_size(self, size_str: str) -> int:
        """解析大小字符串"""
        size_str = size_str.upper().strip()
        
        multipliers = {
            'KB': 1024,
            'MB': 1024 * 1024,
            'GB': 1024 * 1024 * 1024,
            'TB': 1024 * 1024 * 1024 * 1024
        }
        
        for unit, multiplier in multipliers.items():
            if size_str.endswith(unit):
                number = size_str[:-len(unit)].strip()
                try:
                    return int(float(number)) * multiplier
                except ValueError:
                    pass
        
        # 默认字节
        try:
            return int(size_str)
        except ValueError:
            return 0
    
    def _update_file_info(self, original_info: FileInfo, result: WorkflowResult) -> FileInfo:
        """更新文件信息"""
        # 创建新的文件信息对象，合并更新
        updated_info = FileInfo(
            path=original_info.path,
            filename=original_info.filename,
            size=original_info.size,
            extension=original_info.extension,
            kind=result.file_info.kind if result.file_info.kind != 'unknown' else original_info.kind,
            tags=result.file_info.tags or original_info.tags,
            metadata={**original_info.metadata, **(result.file_info.metadata or {})}
        )
        
        # 处理重命名结果
        if result.stage == WorkflowStage.RENAME and result.data.get('new_name'):
            updated_info.filename = result.data['new_name']
            updated_info.path = str(Path(original_info.path).parent / result.data['new_name'])
        
        return updated_info
    
    def shutdown(self):
        """关闭工作流引擎"""
        self.executor.shutdown(wait=True)