#!/usr/bin/env python3
"""
AI驱动内容推荐系统
集成sentence-transformers实现智能推荐
"""

import logging
from typing import List, Dict, Any, Optional, Union
import numpy as np  # type: ignore
import json
import time
from datetime import datetime

# 这些导入已经在上面的代码块中定义

# 尝试导入sentence-transformers，如果失败则设置为None
# 预定义SentenceTransformer类型
try:
    from typing import Any

    SentenceTransformer: Any = None
    # 添加兼容性处理
    import torch  # type: ignore

    # 安全地处理PyTorch版本兼容性
    try:
        # 应用PyTorch兼容性补丁
        if hasattr(torch.utils._pytree, "_register_pytree_node") and not hasattr(
            torch.utils._pytree, "register_pytree_node"
        ):
            # 创建兼容性别名
            torch.utils._pytree.register_pytree_node = (
                torch.utils._pytree._register_pytree_node
            )
    except AttributeError:
        pass  # 忽略任何属性错误
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import faiss  # type: ignore

    FAISS_AVAILABLE = True
except ImportError:
    faiss = None  # type: ignore
    FAISS_AVAILABLE = False

try:
    from sklearn.metrics.pairwise import cosine_similarity  # type: ignore

    COSINE_SIMILARITY_AVAILABLE = True
except ImportError:
    cosine_similarity = None  # type: ignore
    COSINE_SIMILARITY_AVAILABLE = False

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
        self.model = None  # type: ignore
        self.media_items: List[Dict[str, Any]] = []
        self.embeddings: List[np.ndarray] = []
        self.is_initialized = False

        # 推荐配置
        self.config: Dict[str, Any] = {
            "top_k": 10,  # 推荐数量
            "similarity_threshold": 0.5,  # 相似度阈值
            "cache_ttl": 3600,  # 缓存时间(秒)
            "batch_size": 32,  # 批量处理大小
            "faiss_index_type": "IVF100,Flat",  # FAISS索引类型
            "nprobe": 10,  # FAISS搜索参数
            "enable_cache": True,  # 启用缓存
            "cache_size": 1000,  # 缓存大小
        }

        # 性能优化相关
        self.faiss_index = None  # type: ignore
        self.embedding_cache: Dict[Any, np.ndarray] = {}
        self.query_cache: Dict[str, Dict[str, Any]] = {}
        self.media_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_lock = Lock()
        self.last_cache_cleanup: float = time.time()

        # 个性化推荐相关
        from collections import defaultdict

        self.user_profiles: defaultdict[str, Dict[str, Any]] = defaultdict(dict)
        self.user_interactions: defaultdict[str, List[Dict[str, Any]]] = defaultdict(
            list
        )
        self.user_preferences: defaultdict[str, Dict[str, Any]] = defaultdict(dict)
        self._init_user_database()

    def record_user_interaction(
        self,
        user_id: str,
        media_id: str,
        interaction_type: str,
        interaction_value: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ):
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
            if self.conn:
                metadata_str = json.dumps(metadata) if metadata else None
                self.cursor.execute(
                    """
                    INSERT INTO user_interactions 
                    (user_id, media_id, interaction_type, interaction_value, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        user_id,
                        media_id,
                        interaction_type,
                        interaction_value,
                        metadata_str,
                    ),
                )
                self.conn.commit()

            # 更新内存中的用户交互记录
            interaction = {
                "media_id": media_id,
                "type": interaction_type,
                "value": interaction_value,
                "timestamp": datetime.now(),
                "metadata": metadata or {},
            }
            self.user_interactions[user_id].append(interaction)

            # 更新用户偏好
            self._update_user_preferences(
                user_id, media_id, interaction_type, interaction_value
            )

            logger.debug(f"记录用户交互: {user_id} -> {media_id} ({interaction_type})")

        except Exception as e:
            logger.error(f"记录用户交互失败: {e}")

    def _update_user_preferences(
        self, user_id: str, media_id: str, interaction_type: str, value: float
    ) -> None:
        """根据用户交互更新用户偏好"""
        try:
            # 查找媒体信息
            media_item = None
            for item in self.media_items:
                if item.get("id") == media_id:
                    media_item = item
                    break

            if not media_item:
                return

            # 根据交互类型更新偏好权重
            weight_multiplier = 1.0
            if interaction_type == "like":
                weight_multiplier = 2.0
            elif interaction_type == "dislike":
                weight_multiplier = -1.0
            elif interaction_type == "download":
                weight_multiplier = 1.5
            elif interaction_type == "view":
                weight_multiplier = 0.5

            # 更新分类偏好
            if media_item.get("genres"):
                for genre in media_item["genres"]:
                    self._update_preference_weight(
                        user_id, "genre", genre, value * weight_multiplier
                    )

            # 更新导演偏好
            if media_item.get("directors"):
                for director in media_item["directors"]:
                    self._update_preference_weight(
                        user_id, "director", director, value * weight_multiplier
                    )

        except Exception as e:
            logger.error(f"更新用户偏好失败: {e}")

    def get_personalized_recommendations(
        self,
        user_id: str,
        query_text: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取个性化推荐

        Args:
            user_id: 用户ID
            query_text: 查询文本（可选）
            top_k: 推荐数量

        Returns:
            个性化推荐结果
        """
        if not self.is_initialized or len(self.media_items) == 0:
            return []

        # 确保top_k是整数类型
        # 安全获取默认top_k值
        config_top_k = self.config.get("top_k")
        if isinstance(config_top_k, (int, float)) and config_top_k is not None:
            default_top_k = int(config_top_k)
        else:
            default_top_k = 10

        # 安全处理传入的top_k参数
        if isinstance(top_k, (int, float)) and top_k is not None:
            top_k = int(top_k)
        else:
            top_k = default_top_k

        try:
            # 获取基础推荐结果
            limit = top_k * 2
            if query_text:
                base_results = self.get_similar_items(query_text, limit)
            else:
                # 如果没有查询文本，返回空列表
                base_results = []

            if not base_results:
                return []

            # 应用个性化权重
            personalized_results = self._apply_personalization_weights(
                user_id, base_results
            )

            # 排序并返回前top_k个结果
            personalized_results.sort(
                key=lambda x: x.get("personalized_score", 0), reverse=True
            )

            return personalized_results[:top_k]

        except Exception as e:
            logger.error(f"获取个性化推荐失败: {e}")
            return []

    def _apply_personalization_weights(
        self, user_id: str, recommendations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """应用个性化权重到推荐结果"""
        try:
            personalized_results: List[Dict[str, Any]] = []

            for item in recommendations:
                personalized_item = item.copy()
                base_score = item.get("similarity_score", 0)
                personalization_score = 0.0
                diversity_bonus = 0.0

                # 计算个性化得分
                if item.get("genres"):
                    for genre in item["genres"]:
                        pref_key = f"genre:{genre}"
                        personalization_score += self.user_preferences[user_id].get(
                            pref_key, 0.1
                        )

                if item.get("directors"):
                    for director in item["directors"]:
                        pref_key = f"director:{director}"
                        personalization_score += self.user_preferences[user_id].get(
                            pref_key, 0.1
                        )

                if item.get("actors"):
                    for actor in item["actors"][:3]:
                        pref_key = f"actor:{actor}"
                        personalization_score += self.user_preferences[user_id].get(
                            pref_key, 0.1
                        )

                if item.get("type"):
                    pref_key = f"media_type:{item['type']}"
                    personalization_score += self.user_preferences[user_id].get(
                        pref_key, 0.1
                    )

                # 多样性奖励：鼓励不同类型的推荐
                if len(personalized_results) > 0:
                    # 检查当前结果中是否已经有相似类型
                    existing_types = [r.get("type") for r in personalized_results]
                    if item.get("type") not in existing_types:
                        diversity_bonus += 0.2

                    # 检查是否有相似导演
                    existing_directors = []
                    for r in personalized_results:
                        if r.get("directors"):
                            existing_directors.extend(r["directors"])

                    if item.get("directors"):
                        new_directors = set(item["directors"]) - set(existing_directors)
                        if new_directors:
                            diversity_bonus += 0.1

                # 评分奖励：高评分内容获得额外加分
                rating_bonus = 0.0
                if item.get("rating"):
                    if item["rating"] >= 9.0:
                        rating_bonus += 0.3
                    elif item["rating"] >= 8.0:
                        rating_bonus += 0.2
                    elif item["rating"] >= 7.0:
                        rating_bonus += 0.1

                # 新鲜度奖励：较新的内容获得加分
                recency_bonus = 0.0
                if item.get("year"):
                    current_year = datetime.now().year
                    if item["year"] >= current_year - 2:  # 近两年的内容
                        recency_bonus += 0.2
                    elif item["year"] >= current_year - 5:  # 近五年的内容
                        recency_bonus += 0.1

                # 计算综合得分
                personalized_score = (
                    base_score
                    + (personalization_score * 0.1)
                    + diversity_bonus
                    + rating_bonus
                    + recency_bonus
                )
                personalized_item["personalized_score"] = personalized_score
                personalized_item["base_similarity"] = base_score
                personalized_item["personalization_bonus"] = personalization_score
                personalized_item["diversity_bonus"] = diversity_bonus
                personalized_item["rating_bonus"] = rating_bonus
                personalized_item["recency_bonus"] = recency_bonus

                personalized_results.append(personalized_item)

            return personalized_results

        except Exception as e:
            logger.error(f"应用个性化权重失败: {e}")
            return recommendations
            logger.error(f"更新用户偏好失败: {e}")

    def _init_user_database(self):
        """初始化用户行为数据库"""
        try:
            db_path = Path("user_recommendations.db")
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()

            # 创建用户行为表
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    media_id TEXT NOT NULL,
                    interaction_type TEXT NOT NULL,  -- view, like, dislike, download, etc.
                    interaction_value REAL DEFAULT 1.0,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """
            )

            # 创建用户偏好表
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    preference_type TEXT NOT NULL,  -- genre, director, actor, etc.
                    preference_value TEXT NOT NULL,
                    preference_weight REAL DEFAULT 1.0,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # 创建用户配置文件
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    profile_data TEXT,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            self.conn.commit()
            logger.info("用户推荐数据库初始化成功")

        except Exception as e:
            logger.error(f"用户数据库初始化失败: {e}")
            # 如果数据库初始化失败，使用内存存储
            self.conn = None
            self.cursor = None

            # 更新分类偏好
            if media_item.get("genres"):
                for genre in media_item["genres"]:
                    self._update_preference_weight(
                        user_id, "genre", genre, value * weight_multiplier
                    )

            # 更新导演偏好
            if media_item.get("directors"):
                for director in media_item["directors"]:
                    self._update_preference_weight(
                        user_id, "director", director, value * weight_multiplier
                    )

            # 更新音乐特定偏好
            if media_item.get("album"):
                self._update_preference_weight(
                    user_id,
                    "music_album",
                    media_item["album"],
                    value * weight_multiplier,
                )
                if media_item.get("genre"):
                    self._update_preference_weight(
                        user_id,
                        "music_genre",
                        media_item["genre"],
                        value * weight_multiplier,
                    )

        except Exception as e:
            logger.error(f"更新用户偏好失败: {e}")

            # 更新分类偏好
            if media_item.get("genres"):
                for genre in media_item["genres"]:
                    self._update_preference_weight(
                        user_id, "genre", genre, value * weight_multiplier
                    )

            # 更新导演偏好
            if media_item.get("directors"):
                for director in media_item["directors"]:
                    self._update_preference_weight(
                        user_id, "director", director, value * weight_multiplier
                    )

            # 更新演员偏好
            if media_item.get("actors"):
                for actor in media_item["actors"][:3]:  # 只取前3个主要演员
                    pass  # 暂时不更新演员偏好
                if media_item.get("genre"):
                    self._update_preference_weight(
                        user_id,
                        "music_genre",
                        media_item["genre"],
                        value * weight_multiplier,
                    )

        except Exception as e:
            logger.error(f"更新用户偏好失败: {e}")

    def _update_preference_weight(
        self, user_id: str, pref_type: str, pref_value: str, weight_delta: float
    ):
        """更新偏好权重"""
        try:
            if self.conn:
                # 检查是否已存在偏好
                self.cursor.execute(
                    """
                    SELECT preference_weight FROM user_preferences 
                    WHERE user_id = ? AND preference_type = ? AND preference_value = ?
                """,
                    (user_id, pref_type, pref_value),
                )

                result = self.cursor.fetchone()
                if result:
                    # 更新现有偏好
                    new_weight = max(0.1, result[0] + weight_delta)
                    self.cursor.execute(
                        """
                        UPDATE user_preferences 
                        SET preference_weight = ?, last_updated = CURRENT_TIMESTAMP
                        WHERE user_id = ? AND preference_type = ? AND preference_value = ?
                    """,
                        (new_weight, user_id, pref_type, pref_value),
                    )
                else:
                    # 插入新偏好
                    self.cursor.execute(
                        """
                        INSERT INTO user_preferences 
                        (user_id, preference_type, preference_value, preference_weight)
                        VALUES (?, ?, ?, ?)
                    """,
                        (user_id, pref_type, pref_value, max(0.1, weight_delta)),
                    )

                self.conn.commit()

            # 更新内存中的偏好
            pref_key = f"{pref_type}:{pref_value}"
            current_weight = self.user_preferences[user_id].get(pref_key, 0.1)
            self.user_preferences[user_id][pref_key] = max(
                0.1, current_weight + weight_delta
            )

        except Exception as e:
            logger.error(f"更新偏好权重失败: {e}")

    def initialize(self):
        """初始化模型和索引"""
        try:
            logger.info(f"正在加载sentence-transformers模型: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)

            # 初始化FAISS索引
            self._init_faiss_index()

            # 添加示例媒体数据用于测试
            self._add_sample_media_data()

            self.is_initialized = True
            logger.info("AI推荐系统初始化成功")

        except Exception as e:
            logger.error(f"AI推荐系统初始化失败: {e}")
            raise

    def _init_faiss_index(self):
        """初始化FAISS索引"""
        if len(self.embeddings) > 0:
            # 如果有现有嵌入，构建索引
            embeddings_array = np.array(self.embeddings).astype("float32")
            dimension = embeddings_array.shape[1]

            # 创建IVF索引以提高搜索性能
            quantizer = faiss.IndexFlatIP(dimension)
            self.faiss_index = faiss.IndexIVFFlat(quantizer, dimension, 100)
            if self.faiss_index:
                self.faiss_index.train(embeddings_array)
                self.faiss_index.add(embeddings_array)
            self.faiss_index.nprobe = self.config["nprobe"]

            logger.info(f"FAISS索引初始化完成，包含 {len(self.embeddings)} 个向量")
        else:
            # 初始化空索引
            dimension = 384  # all-MiniLM-L6-v2的维度
            quantizer = faiss.IndexFlatIP(dimension)
            self.faiss_index = faiss.IndexIVFFlat(quantizer, dimension, 100)
            logger.info("FAISS索引初始化完成（空索引）")

    def generate_embedding(self, text: str) -> np.ndarray:
        """
        生成文本的向量嵌入（带缓存）

        Args:
            text: 输入文本

        Returns:
            向量嵌入
        """
        if not self.is_initialized:
            self.initialize()

        # 检查缓存
        if self.config["enable_cache"]:
            cache_key = hash(text)
            if cache_key in self.embedding_cache:
                return self.embedding_cache[cache_key]

        try:
            import numpy as np

            # 定义embedding变量并添加类型注解
            embedding: np.ndarray
            if self.model:
                embedding = self.model.encode([text], convert_to_numpy=True)[0]
            else:
                # 如果model为None，返回空numpy数组
                embedding = np.array([])

            # 添加到缓存
            if self.config["enable_cache"]:
                with self.cache_lock:
                    # 安全地获取和转换cache_size
                    try:
                        cache_size_value = self.config.get("cache_size", 1000)
                        # 检查值是否可以转换为整数
                        if isinstance(cache_size_value, (int, float, str)):
                            cache_size = int(cache_size_value)
                        else:
                            cache_size = 1000  # 默认值
                    except (ValueError, TypeError):
                        cache_size = 1000  # 默认值
                    if len(self.embedding_cache) >= cache_size:
                        # 清理最旧的缓存项
                        oldest_key = next(iter(self.embedding_cache))
                        del self.embedding_cache[oldest_key]
                    self.embedding_cache[cache_key] = embedding

            return embedding

        except Exception as e:
            logger.error(f"生成嵌入失败: {e}")
            raise

    def generate_media_embedding(self, media_data: Dict[str, Any]) -> np.ndarray:
        """
        为媒体内容生成综合向量嵌入

        Args:
            media_data: 媒体数据字典

        Returns:
            综合向量嵌入
        """
        # 构建综合文本描述
        text_parts = []

        # 标题和描述
        if media_data.get("title"):
            text_parts.append(media_data["title"])
        if media_data.get("description"):
            text_parts.append(media_data["description"])

        # 类型和分类
        if media_data.get("type"):
            text_parts.append(f"类型: {media_data['type']}")
        if media_data.get("genres"):
            genres = (
                ", ".join(media_data["genres"])
                if isinstance(media_data["genres"], list)
                else media_data["genres"]
            )
            text_parts.append(f"分类: {genres}")

        # 年份和评分
        if media_data.get("year"):
            text_parts.append(f"年份: {media_data['year']}")
        if media_data.get("rating"):
            text_parts.append(f"评分: {media_data['rating']}")

        # 导演和演员
        if media_data.get("directors"):
            directors = (
                ", ".join(media_data["directors"])
                if isinstance(media_data["directors"], list)
                else media_data["directors"]
            )
            text_parts.append(f"导演: {directors}")
        if media_data.get("actors"):
            actors = (
                ", ".join(media_data["actors"])
                if isinstance(media_data["actors"], list)
                else media_data["actors"]
            )
            text_parts.append(f"演员: {actors}")

        # 组合所有文本部分
        combined_text = ". ".join(text_parts)

        return self.generate_embedding(combined_text)

    def add_media_items(self, media_items: List[Dict[str, Any]]):
        """
        添加媒体内容到推荐系统

        Args:
            media_items: 媒体内容列表
        """
        if not self.is_initialized:
            self.initialize()

        try:
            # 批量生成嵌入以提高性能
            embeddings_batch = []

            for item in media_items:
                embedding = self.generate_media_embedding(item)
                embeddings_batch.append(embedding)

            # 添加到FAISS索引
            if len(embeddings_batch) > 0:
                embeddings_array = np.array(embeddings_batch).astype("float32")

                if self.faiss_index:
                    if self.faiss_index.ntotal == 0:
                        # 首次添加，需要训练索引
                        self.faiss_index.train(embeddings_array)

                    self.faiss_index.add(embeddings_array)

                # 添加到本地存储
                self.embeddings.extend(embeddings_batch)
                self.media_items.extend(media_items)

            logger.info(f"成功添加 {len(media_items)} 个媒体内容到推荐系统")

        except Exception as e:
            logger.error(f"添加媒体内容失败: {e}")
            raise

    def get_similar_items(
        self, query_text: Optional[str] = None, top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        获取相似媒体内容推荐（使用FAISS优化性能）

        Args:
            query_text: 查询文本
            top_k: 返回的推荐数量

        Returns:
            相似媒体内容列表
        """
        if not self.is_initialized or len(self.media_items) == 0:
            return []

        # 安全地获取和转换top_k
        try:
            if top_k is None:
                config_top_k = self.config.get("top_k", 10)
                # 检查值是否可以转换为整数
                if isinstance(config_top_k, (int, float, str)):
                    top_k = int(config_top_k)
                else:
                    top_k = 10  # 默认值
            else:
                # 确保传入的top_k也是整数类型
                top_k = int(top_k)
        except (ValueError, TypeError):
            top_k = 10  # 默认值

        # 检查查询缓存
        cache_key = f"query_{hash(query_text)}_{top_k}"
        if self.config["enable_cache"] and cache_key in self.query_cache:
            cached_result = self.query_cache[cache_key]
            if time.time() - cached_result["timestamp"] < self.config["cache_ttl"]:
                return cached_result["results"]

        try:
            # 确保query_text不为None
            if query_text is None:
                return []

            # 生成查询嵌入
            query_embedding = self.generate_embedding(query_text)
            query_embedding = query_embedding.astype("float32").reshape(1, -1)

            # 使用FAISS进行高效搜索
            if self.faiss_index:
                distances, indices = self.faiss_index.search(
                    query_embedding, top_k * 2
                )  # 搜索更多结果用于过滤
            else:
                # 如果faiss_index为None，返回空结果
                distances = np.array([[]])
                indices = np.array([[]])

            # 构建结果
            results: List[Dict[str, Any]] = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx < len(self.media_items):  # 确保索引有效
                    similarity = float(distance)  # FAISS返回的是距离，需要转换为相似度

                    # 安全地获取和转换similarity_threshold
                    try:
                        threshold_value = self.config.get("similarity_threshold", 0.7)
                        # 检查值是否可以转换为浮点数
                        if isinstance(threshold_value, (int, float, str)):
                            similarity_threshold = float(threshold_value)
                        else:
                            similarity_threshold = 0.7  # 默认阈值
                    except (ValueError, TypeError):
                        similarity_threshold = 0.7  # 默认阈值

                    # 过滤低相似度结果
                    if similarity >= similarity_threshold or len(results) < top_k:
                        media_item = self.media_items[idx].copy()
                        media_item["similarity_score"] = similarity
                        media_item["rank"] = len(results) + 1
                        media_item["confidence"] = (
                            "high" if similarity >= similarity_threshold else "low"
                        )
                        results.append(media_item)

                    # 达到所需数量时停止
                    # 确保top_k不为None
                    safe_top_k = top_k or 10
                    if len(results) >= safe_top_k:
                        break

            # 缓存结果
            if self.config["enable_cache"]:
                with self.cache_lock:
                    # 安全地获取和转换cache_size
                    try:
                        cache_size_value = self.config.get("cache_size", 1000)
                        # 检查值是否可以转换为整数
                        if isinstance(cache_size_value, (int, float, str)):
                            cache_size = int(cache_size_value)
                        else:
                            cache_size = 1000  # 默认值
                    except (ValueError, TypeError):
                        cache_size = 1000  # 默认值

                    if len(self.query_cache) >= cache_size:
                        # 清理最旧的缓存项
                        oldest_key = next(iter(self.query_cache))
                        del self.query_cache[oldest_key]
                    self.query_cache[cache_key] = {
                        "results": results,
                        "timestamp": time.time(),
                    }

            return results

        except Exception as e:
            logger.error(f"获取相似内容失败: {e}")
            # 回退到传统方法，确保top_k是整数且query_text不为None
            safe_top_k = top_k or 10
            if query_text is None:
                return []
            return self._fallback_similar_items(query_text, safe_top_k)

    def _fallback_similar_items(
        self, query_text: str, top_k: int
    ) -> List[Dict[str, Any]]:
        """回退到传统相似度计算方法"""
        try:
            query_embedding = self.generate_embedding(query_text)
            query_embedding = query_embedding.reshape(1, -1)

            # 计算余弦相似度
            similarities = cosine_similarity(query_embedding, self.embeddings)[0]

            # 获取相似度最高的项目
            similar_indices = np.argsort(similarities)[::-1]

            results = []
            for i, idx in enumerate(similar_indices[:top_k]):
                similarity = similarities[idx]
                media_item = self.media_items[idx].copy()
                media_item["similarity_score"] = float(similarity)
                media_item["rank"] = i + 1
                # 安全地获取和转换similarity_threshold
                try:
                    threshold_value = self.config.get("similarity_threshold", 0.7)
                    # 检查值是否可以转换为浮点数
                    if isinstance(threshold_value, (int, float, str)):
                        threshold = float(threshold_value)
                    else:
                        threshold = 0.7  # 默认阈值
                except (ValueError, TypeError):
                    threshold = 0.7  # 默认阈值
                media_item["confidence"] = "high" if similarity >= threshold else "low"
                results.append(media_item)

            return results

        except Exception as e:
            logger.error(f"回退相似度计算失败: {e}")
            return []

    def get_similar_to_media(
        self, media_id: str, top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        基于特定媒体内容获取相似推荐

        Args:
            media_id: 媒体ID
            top_k: 返回的推荐数量

        Returns:
            相似媒体内容列表
        """
        # 查找媒体内容
        target_media = None
        target_idx = -1

        for idx, item in enumerate(self.media_items):
            if item.get("id") == media_id:
                target_media = item
                target_idx = idx
                break

        if target_media is None:
            logger.warning(f"未找到媒体内容: {media_id}")
            return []

        # 构建查询文本
        query_text = self._build_query_from_media(target_media)

        # 获取相似项，排除自身
        results = self.get_similar_items(query_text, top_k + 1 if top_k else None)

        # 过滤掉自身
        filtered_results = [item for item in results if item.get("id") != media_id]

        return filtered_results[:top_k] if top_k else filtered_results

    def _build_query_from_media(self, media_data: Dict[str, Any]) -> str:
        """从媒体数据构建查询文本"""
        query_parts = []

        if media_data.get("title"):
            query_parts.append(media_data["title"])
        if media_data.get("genres"):
            genres = (
                ", ".join(media_data["genres"])
                if isinstance(media_data["genres"], list)
                else media_data["genres"]
            )
            query_parts.append(genres)
        if media_data.get("directors"):
            directors = (
                ", ".join(media_data["directors"])
                if isinstance(media_data["directors"], list)
                else media_data["directors"]
            )
            query_parts.append(directors)

        return ". ".join(query_parts)

    def batch_recommend(
        self, media_ids: List[str], top_k: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        批量推荐

        Args:
            media_ids: 媒体ID列表
            top_k: 每个媒体的推荐数量

        Returns:
            批量推荐结果
        """
        results = {}

        for media_id in media_ids:
            similar_items = self.get_similar_to_media(media_id, top_k)
            results[media_id] = similar_items

        return results

    def get_recommendation_stats(self) -> Dict[str, Any]:
        """获取推荐系统统计信息"""
        return {
            "total_media_items": len(self.media_items),
            "embeddings_count": len(self.embeddings),
            "is_initialized": self.is_initialized,
            "model_name": self.model_name,
            "config": self.config,
        }


# 示例使用
def main():
    """示例演示"""
    # 初始化推荐系统
    recommender = AIRecommendationSystem()

    # 示例媒体数据
    sample_media = [
        {
            "id": "movie_1",
            "title": "盗梦空间",
            "type": "movie",
            "genres": ["科幻", "动作", "悬疑"],
            "year": 2010,
            "directors": ["克里斯托弗·诺兰"],
            "actors": ["莱昂纳多·迪卡普里奥", "玛丽昂·歌迪亚"],
            "description": "一群盗梦者通过潜入他人梦境窃取机密的故事",
            "rating": 9.3,
        },
        {
            "id": "movie_2",
            "title": "星际穿越",
            "type": "movie",
            "genres": ["科幻", "冒险", "剧情"],
            "year": 2014,
            "directors": ["克里斯托弗·诺兰"],
            "actors": ["马修·麦康纳", "安妮·海瑟薇"],
            "description": "一群探险家穿越虫洞为人类寻找新家园的太空冒险",
            "rating": 9.2,
        },
        {
            "id": "movie_3",
            "title": "阿凡达",
            "type": "movie",
            "genres": ["科幻", "动作", "冒险"],
            "year": 2009,
            "directors": ["詹姆斯·卡梅隆"],
            "actors": ["萨姆·沃辛顿", "佐伊·索尔达娜"],
            "description": "人类在潘多拉星球上与纳美族人互动的科幻史诗",
            "rating": 8.7,
        },
        {
            "id": "movie_4",
            "title": "流浪地球",
            "type": "movie",
            "genres": ["科幻", "灾难", "冒险"],
            "year": 2019,
            "directors": ["郭帆"],
            "actors": ["吴京", "屈楚萧", "李光洁"],
            "description": "人类带着地球逃离太阳系的科幻冒险故事",
            "rating": 8.4,
        },
        {
            "id": "movie_5",
            "title": "三体",
            "type": "movie",
            "genres": ["科幻", "悬疑", "剧情"],
            "year": 2023,
            "directors": ["曾国祥"],
            "actors": ["张鲁一", "于和伟", "陈瑾"],
            "description": "人类与外星文明三体人接触的科幻故事",
            "rating": 8.8,
        },
        {
            "id": "tv_1",
            "title": "权力的游戏",
            "type": "tv",
            "genres": ["奇幻", "剧情", "冒险"],
            "year": 2011,
            "directors": ["大卫·贝尼奥夫", "D·B·威斯"],
            "actors": ["基特·哈灵顿", "艾米莉亚·克拉克", "彼特·丁拉基"],
            "description": "维斯特洛大陆上各大家族争夺铁王座的故事",
            "rating": 9.3,
        },
        {
            "id": "tv_2",
            "title": "黑镜",
            "type": "tv",
            "genres": ["科幻", "惊悚", "剧情"],
            "year": 2011,
            "directors": ["查理·布鲁克"],
            "actors": ["布莱斯·达拉斯·霍华德", "丹尼尔·卡卢亚"],
            "description": "探讨科技对人类生活影响的科幻剧集",
            "rating": 8.8,
        },
        {
            "id": "tv_3",
            "title": "西部世界",
            "type": "tv",
            "genres": ["科幻", "西部", "惊悚"],
            "year": 2016,
            "directors": ["乔纳森·诺兰", "丽莎·乔伊"],
            "actors": ["埃文·蕾切尔·伍德", "安东尼·霍普金斯", "艾德·哈里斯"],
            "description": "人工智能在西部主题公园中觉醒的故事",
            "rating": 8.6,
        },
        {
            "id": "anime_1",
            "title": "进击的巨人",
            "type": "anime",
            "genres": ["动画", "动作", "奇幻"],
            "year": 2013,
            "directors": ["荒木哲郎"],
            "actors": ["梶裕贵", "石川由依", "井上麻里奈"],
            "description": "人类与巨人之间生存斗争的史诗故事",
            "rating": 9.1,
        },
        {
            "id": "anime_2",
            "title": "命运石之门",
            "type": "anime",
            "genres": ["科幻", "悬疑", "剧情"],
            "year": 2011,
            "directors": ["佐藤卓哉", "滨崎博嗣"],
            "actors": ["宫野真守", "今井麻美", "花泽香菜"],
            "description": "时间旅行与平行世界理论的科幻故事",
            "rating": 9.0,
        },
    ]

    # 添加媒体内容
    recommender.add_media_items(sample_media)

    # 测试推荐
    print("=== AI推荐系统测试 ===")

    # 基于文本查询推荐
    query = "诺兰的科幻电影"
    results = recommender.get_similar_items(query)

    print(f"\n查询: '{query}'")
    print(f"找到 {len(results)} 个相似内容:")

    for item in results:
        print(f"  - {item['title']} (相似度: {item['similarity_score']:.3f})")

    # 基于特定媒体推荐
    print(f"\n基于 '{sample_media[0]['title']}' 的推荐:")
    similar_to_movie = recommender.get_similar_to_media("movie_1")

    for item in similar_to_movie:
        print(f"  - {item['title']} (相似度: {item['similarity_score']:.3f})")

    # 显示统计信息
    stats = recommender.get_recommendation_stats()
    print(f"\n系统统计: {stats}")

    def _add_sample_media_data(self):
        """添加示例媒体数据用于测试"""
        try:
            sample_media = [
                {
                    "id": "movie_1",
                    "title": "盗梦空间",
                    "type": "movie",
                    "genres": ["科幻", "动作", "悬疑"],
                    "year": 2010,
                    "rating": 9.3,
                    "directors": ["克里斯托弗·诺兰"],
                    "actors": ["莱昂纳多·迪卡普里奥", "汤姆·哈迪", "艾伦·佩吉"],
                    "description": "一名盗梦者带领团队进入他人梦境窃取机密的故事",
                },
                {
                    "id": "movie_2",
                    "title": "星际穿越",
                    "type": "movie",
                    "genres": ["科幻", "冒险", "剧情"],
                    "year": 2014,
                    "rating": 9.2,
                    "directors": ["克里斯托弗·诺兰"],
                    "actors": ["马修·麦康纳", "安妮·海瑟薇", "杰西卡·查斯坦"],
                    "description": "一群探险家穿越虫洞寻找人类新家园的太空冒险",
                },
                {
                    "id": "movie_3",
                    "title": "阿凡达",
                    "type": "movie",
                    "genres": ["科幻", "动作", "冒险"],
                    "year": 2009,
                    "rating": 8.7,
                    "directors": ["詹姆斯·卡梅隆"],
                    "actors": ["萨姆·沃辛顿", "佐伊·索尔达娜", "西格妮·韦弗"],
                    "description": "人类在潘多拉星球上与纳美族人的冲突与融合",
                },
                {
                    "id": "movie_4",
                    "title": "黑客帝国",
                    "type": "movie",
                    "genres": ["科幻", "动作", "惊悚"],
                    "year": 1999,
                    "rating": 9.1,
                    "directors": ["莉莉·沃卓斯基", "拉娜·沃卓斯基"],
                    "actors": ["基努·里维斯", "劳伦斯·菲什伯恩", "凯瑞-安·莫斯"],
                    "description": "程序员尼奥发现现实世界其实是虚拟矩阵的故事",
                },
                {
                    "id": "movie_5",
                    "title": "银翼杀手2049",
                    "type": "movie",
                    "genres": ["科幻", "惊悚", "剧情"],
                    "year": 2017,
                    "rating": 8.3,
                    "directors": ["丹尼斯·维伦纽瓦"],
                    "actors": ["瑞恩·高斯林", "哈里森·福特", "安娜·德·阿玛斯"],
                    "description": "新一代银翼杀手K揭开一个足以颠覆社会的秘密",
                },
                {
                    "id": "tv_1",
                    "title": "黑镜",
                    "type": "tv_series",
                    "genres": ["科幻", "剧情", "惊悚"],
                    "year": 2011,
                    "rating": 8.8,
                    "directors": ["查理·布鲁克"],
                    "actors": ["多演员阵容"],
                    "description": "探讨科技对人类生活影响的独立剧集",
                },
                {
                    "id": "tv_2",
                    "title": "西部世界",
                    "type": "tv_series",
                    "genres": ["科幻", "西部", "惊悚"],
                    "year": 2016,
                    "rating": 8.6,
                    "directors": ["乔纳森·诺兰", "丽莎·乔伊"],
                    "actors": ["埃文·蕾切尔·伍德", "安东尼·霍普金斯", "艾德·哈里斯"],
                    "description": "高科技主题公园中人工智能觉醒的故事",
                },
            ]

            # 添加示例数据
            self.add_media_items(sample_media)
            logger.info(f"添加了 {len(sample_media)} 个示例媒体数据")

        except Exception as e:
            logger.error(f"添加示例媒体数据失败: {e}")

    def _add_sample_media_data(self):
        """添加示例媒体数据用于测试"""
        try:
            sample_media = [
                {
                    "id": "movie_1",
                    "title": "盗梦空间",
                    "type": "movie",
                    "genres": ["科幻", "动作", "悬疑"],
                    "year": 2010,
                    "rating": 9.3,
                    "directors": ["克里斯托弗·诺兰"],
                    "actors": ["莱昂纳多·迪卡普里奥", "汤姆·哈迪", "艾伦·佩吉"],
                    "description": "一名盗梦者带领团队进入他人梦境窃取机密的故事",
                },
                {
                    "id": "movie_2",
                    "title": "星际穿越",
                    "type": "movie",
                    "genres": ["科幻", "冒险", "剧情"],
                    "year": 2014,
                    "rating": 9.2,
                    "directors": ["克里斯托弗·诺兰"],
                    "actors": ["马修·麦康纳", "安妮·海瑟薇", "杰西卡·查斯坦"],
                    "description": "一群探险家穿越虫洞寻找人类新家园的太空冒险",
                },
                {
                    "id": "movie_3",
                    "title": "阿凡达",
                    "type": "movie",
                    "genres": ["科幻", "动作", "冒险"],
                    "year": 2009,
                    "rating": 8.7,
                    "directors": ["詹姆斯·卡梅隆"],
                    "actors": ["萨姆·沃辛顿", "佐伊·索尔达娜", "西格妮·韦弗"],
                    "description": "人类在潘多拉星球上与纳美族人的冲突与融合",
                },
                {
                    "id": "movie_4",
                    "title": "黑客帝国",
                    "type": "movie",
                    "genres": ["科幻", "动作", "惊悚"],
                    "year": 1999,
                    "rating": 9.1,
                    "directors": ["莉莉·沃卓斯基", "拉娜·沃卓斯基"],
                    "actors": ["基努·里维斯", "劳伦斯·菲什伯恩", "凯瑞-安·莫斯"],
                    "description": "程序员尼奥发现现实世界其实是虚拟矩阵的故事",
                },
                {
                    "id": "movie_5",
                    "title": "银翼杀手2049",
                    "type": "movie",
                    "genres": ["科幻", "惊悚", "剧情"],
                    "year": 2017,
                    "rating": 8.3,
                    "directors": ["丹尼斯·维伦纽瓦"],
                    "actors": ["瑞恩·高斯林", "哈里森·福特", "安娜·德·阿玛斯"],
                    "description": "新一代银翼杀手K揭开一个足以颠覆社会的秘密",
                },
                {
                    "id": "tv_1",
                    "title": "黑镜",
                    "type": "tv_series",
                    "genres": ["科幻", "剧情", "惊悚"],
                    "year": 2011,
                    "rating": 8.8,
                    "directors": ["查理·布鲁克"],
                    "actors": ["多演员阵容"],
                    "description": "探讨科技对人类生活影响的独立剧集",
                },
                {
                    "id": "tv_2",
                    "title": "西部世界",
                    "type": "tv_series",
                    "genres": ["科幻", "西部", "惊悚"],
                    "year": 2016,
                    "rating": 8.6,
                    "directors": ["乔纳森·诺兰", "丽莎·乔伊"],
                    "actors": ["埃文·蕾切尔·伍德", "安东尼·霍普金斯", "艾德·哈里斯"],
                    "description": "高科技主题公园中人工智能觉醒的故事",
                },
            ]

            # 添加示例数据
            self.add_media_items(sample_media)
            logger.info(f"添加了 {len(sample_media)} 个示例媒体数据")

        except Exception as e:
            logger.error(f"添加示例媒体数据失败: {e}")

    def _add_sample_media_data(self):
        """添加示例媒体数据用于测试"""
        try:
            sample_media = [
                {
                    "id": "movie_1",
                    "title": "盗梦空间",
                    "type": "movie",
                    "genres": ["科幻", "动作", "悬疑"],
                    "year": 2010,
                    "rating": 9.3,
                    "directors": ["克里斯托弗·诺兰"],
                    "actors": ["莱昂纳多·迪卡普里奥", "汤姆·哈迪", "艾伦·佩吉"],
                    "description": "一名盗梦者带领团队进入他人梦境窃取机密的故事",
                },
                {
                    "id": "movie_2",
                    "title": "星际穿越",
                    "type": "movie",
                    "genres": ["科幻", "冒险", "剧情"],
                    "year": 2014,
                    "rating": 9.2,
                    "directors": ["克里斯托弗·诺兰"],
                    "actors": ["马修·麦康纳", "安妮·海瑟薇", "杰西卡·查斯坦"],
                    "description": "一群探险家穿越虫洞寻找人类新家园的太空冒险",
                },
                {
                    "id": "movie_3",
                    "title": "阿凡达",
                    "type": "movie",
                    "genres": ["科幻", "动作", "冒险"],
                    "year": 2009,
                    "rating": 8.7,
                    "directors": ["詹姆斯·卡梅隆"],
                    "actors": ["萨姆·沃辛顿", "佐伊·索尔达娜", "西格妮·韦弗"],
                    "description": "人类在潘多拉星球上与纳美族人的冲突与融合",
                },
                {
                    "id": "movie_4",
                    "title": "黑客帝国",
                    "type": "movie",
                    "genres": ["科幻", "动作", "惊悚"],
                    "year": 1999,
                    "rating": 9.1,
                    "directors": ["莉莉·沃卓斯基", "拉娜·沃卓斯基"],
                    "actors": ["基努·里维斯", "劳伦斯·菲什伯恩", "凯瑞-安·莫斯"],
                    "description": "程序员尼奥发现现实世界其实是虚拟矩阵的故事",
                },
                {
                    "id": "movie_5",
                    "title": "银翼杀手2049",
                    "type": "movie",
                    "genres": ["科幻", "惊悚", "剧情"],
                    "year": 2017,
                    "rating": 8.3,
                    "directors": ["丹尼斯·维伦纽瓦"],
                    "actors": ["瑞恩·高斯林", "哈里森·福特", "安娜·德·阿玛斯"],
                    "description": "新一代银翼杀手K揭开一个足以颠覆社会的秘密",
                },
                {
                    "id": "tv_1",
                    "title": "黑镜",
                    "type": "tv_series",
                    "genres": ["科幻", "剧情", "惊悚"],
                    "year": 2011,
                    "rating": 8.8,
                    "directors": ["查理·布鲁克"],
                    "actors": ["多演员阵容"],
                    "description": "探讨科技对人类生活影响的独立剧集",
                },
                {
                    "id": "tv_2",
                    "title": "西部世界",
                    "type": "tv_series",
                    "genres": ["科幻", "西部", "惊悚"],
                    "year": 2016,
                    "rating": 8.6,
                    "directors": ["乔纳森·诺兰", "丽莎·乔伊"],
                    "actors": ["埃文·蕾切尔·伍德", "安东尼·霍普金斯", "艾德·哈里斯"],
                    "description": "高科技主题公园中人工智能觉醒的故事",
                },
            ]

            # 添加示例数据
            self.add_media_items(sample_media)
            logger.info(f"添加了 {len(sample_media)} 个示例媒体数据")

        except Exception as e:
            logger.error(f"添加示例媒体数据失败: {e}")


if __name__ == "__main__":
    main()
