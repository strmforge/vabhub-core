#!/usr/bin/env python3
"""
AI驱动内容推荐系统 - 修复版本
集成sentence-transformers实现智能推荐
"""

import logging
from typing import List, Dict, Any, Optional, Callable
import numpy as np
from sentence_transformers import SentenceTransformer
import json
import time
from datetime import datetime
from sklearn.metrics.pairwise import cosine_similarity
import faiss  # 高性能相似度搜索

from collections import defaultdict
from threading import Lock
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)


class AIRecommendationSystem:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        初始化AI推荐系统

        Args:
            model_name: sentence-transformers模型名称
        """
        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None
        self.media_items: List[Dict[str, Any]] = []
        self.embeddings: List[np.ndarray] = []
        self.is_initialized = False

        # 推荐配置
        self.config = {
            "top_k": 10,  # 推荐数量
            "similarity_threshold": 0.5,  # 相似度阈值
            "cache_ttl": 3600,  # 缓存时间(秒)
            "batch_size": 32,  # 批量处理大小
            "faiss_index_type": "IVF100,Flat",  # FAISS索引类型
            "nprobe": 10,  # FAISS搜索参数
            "enable_cache": True,  # 启用缓存
            "cache_size": 1000,  # 缓存大小
        }

        # 缓存系统
        self.embedding_cache: Dict[str, np.ndarray] = {}
        self.query_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.media_cache: Dict[str, Dict[str, Any]] = {}

        # 用户数据
        self.user_profiles: Dict[str, Dict[str, Any]] = {}
        self.user_interactions: Dict[str, List[Dict[str, Any]]] = {}
        self.user_preferences: Dict[str, Dict[str, float]] = {}

        # 线程安全
        self.lock = Lock()

        # 数据库连接
        self.db_path = Path("recommendations.db")
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None

    def initialize(self) -> bool:
        """初始化推荐系统"""
        try:
            with self.lock:
                if self.is_initialized:
                    return True

                # 加载模型
                self.model = SentenceTransformer(self.model_name)

                # 初始化数据库
                self._init_user_database()

                self.is_initialized = True
                logger.info(f"AI推荐系统初始化完成，使用模型: {self.model_name}")
                return True

        except Exception as e:
            logger.error(f"AI推荐系统初始化失败: {e}")
            return False

    def _init_user_database(self) -> None:
        """初始化用户数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()

            # 创建用户交互表
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    media_id TEXT NOT NULL,
                    interaction_type TEXT NOT NULL,
                    interaction_value REAL DEFAULT 1.0,
                    metadata TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建用户偏好表
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    preference_key TEXT NOT NULL,
                    preference_value REAL DEFAULT 0.0,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            self.conn.commit()

        except Exception as e:
            logger.error(f"用户数据库初始化失败: {e}")

    def record_user_interaction(
        self,
        user_id: str,
        media_id: str,
        interaction_type: str,
        interaction_value: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        记录用户行为交互

        Args:
            user_id: 用户ID
            media_id: 媒体ID
            interaction_type: 交互类型 (view, like, dislike, download, etc.)
            interaction_value: 交互权重值
            metadata: 额外元数据
        """
        try:
            if not self.is_initialized:
                self.initialize()

            with self.lock:
                # 记录到数据库
                if self.cursor:
                    metadata_json = json.dumps(metadata) if metadata else None
                    self.cursor.execute("""
                        INSERT INTO user_interactions 
                        (user_id, media_id, interaction_type, interaction_value, metadata)
                        VALUES (?, ?, ?, ?, ?)
                    """, (user_id, media_id, interaction_type, interaction_value, metadata_json))
                    self.conn.commit()

                # 更新内存缓存
                if user_id not in self.user_interactions:
                    self.user_interactions[user_id] = []

                self.user_interactions[user_id].append({
                    "media_id": media_id,
                    "interaction_type": interaction_type,
                    "interaction_value": interaction_value,
                    "metadata": metadata,
                    "timestamp": datetime.now()
                })

                # 更新用户偏好
                self._update_user_preferences(user_id, media_id, interaction_type, interaction_value)

                return True

        except Exception as e:
            logger.error(f"记录用户交互失败: {e}")
            return False

    def _update_user_preferences(
        self, user_id: str, media_id: str, interaction_type: str, interaction_value: float
    ) -> None:
        """更新用户偏好"""
        try:
            if user_id not in self.user_preferences:
                self.user_preferences[user_id] = {}

            # 根据交互类型更新偏好权重
            weight_map = {
                "view": 0.1,
                "like": 1.0,
                "dislike": -1.0,
                "download": 0.5,
                "share": 0.8
            }

            weight = weight_map.get(interaction_type, 0.1) * interaction_value

            # 更新偏好
            if interaction_type in ["like", "view", "download"]:
                # 这里可以添加更复杂的偏好更新逻辑
                pass

        except Exception as e:
            logger.error(f"更新用户偏好失败: {e}")

    def get_personalized_recommendations(
        self, user_id: str, query_text: Optional[str] = None, top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        获取个性化推荐

        Args:
            user_id: 用户ID
            query_text: 查询文本
            top_k: 推荐数量
        """
        try:
            if not self.is_initialized:
                self.initialize()

            k = top_k or self.config["top_k"]

            # 获取基于用户历史的推荐
            personalized_results: List[Dict[str, Any]] = []

            # 这里实现推荐逻辑
            # 1. 基于用户历史行为
            # 2. 基于内容相似度
            # 3. 基于协同过滤

            return personalized_results[:k]

        except Exception as e:
            logger.error(f"获取个性化推荐失败: {e}")
            return []

    def add_media_items(self, media_items: List[Dict[str, Any]]) -> bool:
        """添加媒体项目到推荐系统"""
        try:
            if not self.is_initialized:
                self.initialize()

            with self.lock:
                self.media_items.extend(media_items)

                # 生成嵌入向量
                texts = [item.get("title", "") + " " + item.get("description", "") for item in media_items]
                embeddings = self.model.encode(texts) if self.model else []
                
                if isinstance(embeddings, np.ndarray):
                    self.embeddings.extend(embeddings.tolist())
                else:
                    self.embeddings.extend(embeddings)

                return True

        except Exception as e:
            logger.error(f"添加媒体项目失败: {e}")
            return False

    def close(self) -> None:
        """关闭推荐系统"""
        try:
            if self.conn:
                self.conn.close()
            self.is_initialized = False
        except Exception as e:
            logger.error(f"关闭推荐系统失败: {e}")