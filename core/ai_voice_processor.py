#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI语音识别处理器
支持语音控制和自然语言交互的智能媒体管理
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path

from core.config import settings


class AIVoiceProcessor:
    """AI语音识别处理器"""
    
    def __init__(self):
        self.voice_commands = self._load_voice_commands()
        self.speech_recognition_enabled = True
        self.text_to_speech_enabled = True
        self.conversation_history = []
        self.max_history_length = 100
    
    def _load_voice_commands(self) -> Dict[str, Any]:
        """加载语音命令配置"""
        return {
            "scan_files": {
                "keywords": ["扫描", "查找", "搜索", "scan", "find", "search"],
                "action": "scan_files",
                "description": "扫描媒体文件"
            },
            "analyze_media": {
                "keywords": ["分析", "识别", "检测", "analyze", "identify", "detect"],
                "action": "analyze_media",
                "description": "分析媒体内容"
            },
            "smart_rename": {
                "keywords": ["重命名", "改名", "整理", "rename", "organize"],
                "action": "smart_rename",
                "description": "智能重命名文件"
            },
            "get_status": {
                "keywords": ["状态", "进度", "统计", "status", "progress", "stats"],
                "action": "get_status",
                "description": "获取处理状态"
            },
            "help": {
                "keywords": ["帮助", "说明", "怎么用", "help", "how", "usage"],
                "action": "show_help",
                "description": "显示帮助信息"
            }
        }
    
    async def process_voice_command(self, voice_input: str) -> Dict[str, Any]:
        """处理语音命令"""
        # 记录对话历史
        self._add_to_history("user", voice_input)
        
        # 识别命令意图
        intent = self._recognize_intent(voice_input)
        
        # 执行相应操作
        response = await self._execute_intent(intent, voice_input)
        
        # 记录系统响应
        self._add_to_history("system", response.get("response_text", ""))
        
        return response
    
    def _recognize_intent(self, voice_input: str) -> Dict[str, Any]:
        """识别命令意图"""
        input_lower = voice_input.lower()
        
        # 匹配语音命令
        best_match = None
        best_score = 0
        
        for command_name, command_config in self.voice_commands.items():
            score = self._calculate_match_score(input_lower, command_config["keywords"])
            if score > best_score:
                best_score = score
                best_match = {
                    "command": command_name,
                    "action": command_config["action"],
                    "confidence": score,
                    "keywords_found": [kw for kw in command_config["keywords"] if kw in input_lower]
                }
        
        # 如果没有匹配到命令，尝试理解自然语言
        if best_score < 0.3:
            return self._understand_natural_language(input_lower)
        
        return best_match
    
    def _calculate_match_score(self, input_text: str, keywords: List[str]) -> float:
        """计算匹配分数"""
        if not keywords:
            return 0
        
        matches = sum(1 for keyword in keywords if keyword in input_text)
        return matches / len(keywords)
    
    def _understand_natural_language(self, input_text: str) -> Dict[str, Any]:
        """理解自然语言"""
        # 简单的自然语言理解
        if any(word in input_text for word in ["你好", "hello", "hi"]):
            return {
                "command": "greeting",
                "action": "greet_user",
                "confidence": 0.9,
                "type": "greeting"
            }
        elif any(word in input_text for word in ["谢谢", "thank", "thanks"]):
            return {
                "command": "thanks",
                "action": "acknowledge_thanks",
                "confidence": 0.9,
                "type": "thanks"
            }
        elif any(word in input_text for word in ["再见", "拜拜", "bye"]):
            return {
                "command": "goodbye",
                "action": "say_goodbye",
                "confidence": 0.9,
                "type": "goodbye"
            }
        else:
            return {
                "command": "unknown",
                "action": "handle_unknown",
                "confidence": 0.1,
                "type": "unknown"
            }
    
    async def _execute_intent(self, intent: Dict[str, Any], original_input: str) -> Dict[str, Any]:
        """执行意图"""
        action = intent.get("action")
        confidence = intent.get("confidence", 0)
        
        if confidence < 0.3:
            return self._create_response(
                "抱歉，我没有理解您的意思。您可以尝试说：扫描文件、分析媒体、智能重命名等。",
                "unknown_command"
            )
        
        # 根据动作类型执行相应操作
        if action == "scan_files":
            return await self._handle_scan_files(original_input)
        elif action == "analyze_media":
            return await self._handle_analyze_media(original_input)
        elif action == "smart_rename":
            return await self._handle_smart_rename(original_input)
        elif action == "get_status":
            return await self._handle_get_status(original_input)
        elif action == "show_help":
            return self._handle_show_help()
        elif action == "greet_user":
            return self._handle_greeting()
        elif action == "acknowledge_thanks":
            return self._handle_thanks()
        elif action == "say_goodbye":
            return self._handle_goodbye()
        else:
            return self._create_response(
                "我理解您的意思，但暂时无法执行这个操作。",
                "unsupported_action"
            )
    
    async def _handle_scan_files(self, input_text: str) -> Dict[str, Any]:
        """处理扫描文件命令"""
        # 提取路径信息
        path = self._extract_path_from_text(input_text)
        
        response_text = f"好的，我将扫描媒体文件"
        if path:
            response_text += f"，路径：{path}"
        
        return self._create_response(
            response_text + "。请稍等...",
            "scan_files_started",
            {"scan_path": path or settings.scan_path}
        )
    
    async def _handle_analyze_media(self, input_text: str) -> Dict[str, Any]:
        """处理分析媒体命令"""
        return self._create_response(
            "好的，我将使用AI分析媒体内容。这可能需要一些时间...",
            "analyze_media_started",
            {"use_ai": True}
        )
    
    async def _handle_smart_rename(self, input_text: str) -> Dict[str, Any]:
        """处理智能重命名命令"""
        return self._create_response(
            "好的，我将智能重命名媒体文件。请确认您要处理的文件...",
            "smart_rename_started",
            {"strategy": "smart"}
        )
    
    async def _handle_get_status(self, input_text: str) -> Dict[str, Any]:
        """处理获取状态命令"""
        # 这里可以集成实际的处理器状态
        status_info = {
            "total_files": 150,
            "processed_files": 120,
            "progress_percentage": 80,
            "current_operation": "analyzing"
        }
        
        return self._create_response(
            f"当前处理进度：{status_info['progress_percentage']}%，已处理 {status_info['processed_files']} 个文件。",
            "status_report",
            status_info
        )
    
    def _handle_show_help(self) -> Dict[str, Any]:
        """处理显示帮助命令"""
        help_text = """我可以帮您：
• 扫描媒体文件 - 说"扫描文件"或"查找媒体"
• 分析媒体内容 - 说"分析视频"或"识别内容"
• 智能重命名 - 说"重命名文件"或"整理媒体"
• 查看状态 - 说"当前状态"或"处理进度"

请告诉我您需要什么帮助？"""
        
        return self._create_response(help_text, "help_displayed")
    
    def _handle_greeting(self) -> Dict[str, Any]:
        """处理问候"""
        return self._create_response(
            "您好！我是您的智能媒体助手。我可以帮您扫描、分析和整理媒体文件。",
            "greeting_response"
        )
    
    def _handle_thanks(self) -> Dict[str, Any]:
        """处理感谢"""
        return self._create_response(
            "不客气！很高兴能帮助您。还有什么需要我做的吗？",
            "thanks_response"
        )
    
    def _handle_goodbye(self) -> Dict[str, Any]:
        """处理告别"""
        return self._create_response(
            "再见！如果您需要帮助，随时可以叫我。",
            "goodbye_response"
        )
    
    def _extract_path_from_text(self, text: str) -> Optional[str]:
        """从文本中提取路径信息"""
        # 简单的路径提取逻辑
        path_keywords = ["路径", "目录", "文件夹", "path", "directory", "folder"]
        
        for keyword in path_keywords:
            if keyword in text:
                # 尝试提取路径（简化版）
                words = text.split()
                for i, word in enumerate(words):
                    if word == keyword and i + 1 < len(words):
                        potential_path = words[i + 1]
                        if "/" in potential_path or "\\" in potential_path:
                            return potential_path
        
        return None
    
    def _create_response(self, text: str, response_type: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """创建响应"""
        return {
            "response_text": text,
            "response_type": response_type,
            "timestamp": self._get_timestamp(),
            "data": data or {}
        }
    
    def _add_to_history(self, role: str, content: str):
        """添加到对话历史"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": self._get_timestamp()
        })
        
        # 限制历史长度
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history = self.conversation_history[-self.max_history_length:]
    
    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_conversation_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取对话历史"""
        return self.conversation_history[-limit:]
    
    def clear_conversation_history(self):
        """清空对话历史"""
        self.conversation_history = []
    
    def get_voice_capabilities(self) -> Dict[str, Any]:
        """获取语音能力信息"""
        return {
            "speech_recognition": self.speech_recognition_enabled,
            "text_to_speech": self.text_to_speech_enabled,
            "supported_commands": list(self.voice_commands.keys()),
            "conversation_history_size": len(self.conversation_history),
            "max_history_length": self.max_history_length,
            "version": "1.0.0"
        }