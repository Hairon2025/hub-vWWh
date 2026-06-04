"""
Semantic Cache Module

基于语义相似度的 LLM 响应缓存。
当新查询与缓存中的某个查询足够相似时，直接返回缓存的响应，
避免重复调用大模型或嵌入模型。

使用 FAISS 进行向量相似度搜索，使用 Redis 存储查询-响应对。
"""

import hashlib
import json
import uuid
from typing import Optional, List, Dict, Any, Tuple
import numpy as np

import faiss
import redis


class SemanticCache:
    """
    语义缓存：通過向量相似度匹配缓存的响应。

    工作流程：
    1. 收到新查询 → 计算 embedding
    2. 在 FAISS 索引中搜索相似查询（距离 < 阈值）
    3. 命中 → 返回缓存响应
    4. 未命中 → 调用 LLM 获取响应 → 存入缓存
    """

    def __init__(
        self,
        name: str = "semantic_cache",
        redis_url: str = "redis://:admin123.@47.119.18.45:6379",
        ttl: int = 86400,
        prefix: str = "sem_cache",
        distance_threshold: float = 0.1,
        dimension: int = 768,
    ):
        """
        初始化语义缓存。

        Args:
            name: 缓存实例名称。
            redis_url: Redis 连接 URL。
            ttl: 缓存有效期（秒），默认 24 小时。
            prefix: Redis 键前缀。
            distance_threshold: 向量距离阈值，小于此值视为匹配（FAISS L2 或 cos similarity）。
                                 值越小要求越相似，默认 0.1。
            dimension: 嵌入向量维度，需与使用的 embedding 模型匹配。
        """
        self.name = name
        self.ttl = ttl
        self.prefix = prefix
        self.distance_threshold = distance_threshold
        self.dimension = dimension

        # 初始化 Redis 客户端
        self._redis_client = redis.from_url(redis_url, decode_responses=True)

        # 初始化 FAISS 索引（内积索引，适合余弦相似度）
        # 这里使用 IndexFlatIP（内积），需要先对向量做归一化
        self._index = faiss.IndexFlatIP(dimension)
        self._id_to_key: Dict[int, str] = {}  # FAISS ID -> Redis key
        self._key_to_id: Dict[str, int] = {}  # Redis key -> FAISS ID
        self._next_id = 0

        # 尝试从 Redis 恢复已有的索引数据
        self._load_index_from_redis()

    def _load_index_from_redis(self) -> None:
        """从 Redis 恢复 FAISS 索引和映射关系。"""
        index_key = f"{self.prefix}:{self.name}:index"
        mapping_key = f"{self.prefix}:{self.name}:mapping"

        try:
            # 恢复 FAISS 索引
            index_data = self._redis_client.get(index_key)
            if index_data:
                import pickle
                self._index = pickle.loads(bytes.fromhex(index_data))
                self._next_id = int(self._redis_client.hget(mapping_key, "_next_id") or 0)

            # 恢复 ID 映射
            id_to_key = self._redis_client.hgetall(mapping_key)
            for faiss_id, redis_key in id_to_key.items():
                if faiss_id == "_next_id":
                    continue
                self._id_to_key[int(faiss_id)] = redis_key
                self._key_to_id[redis_key] = int(faiss_id)
        except Exception as e:
            # 如果恢复失败，使用空索引（首次初始化）
            self._next_id = 0

    def _save_index_to_redis(self) -> None:
        """将 FAISS 索引和映射关系保存到 Redis。"""
        import pickle

        index_key = f"{self.prefix}:{self.name}:index"
        mapping_key = f"{self.prefix}:{self.name}:mapping"

        # 序列化 FAISS 索引
        index_bytes = pickle.dumps(self._index).hex()
        self._redis_client.set(index_key, index_bytes)

        # 保存映射和计数器
        mapping = {"_next_id": str(self._next_id)}
        mapping.update(self._id_to_key)
        self._redis_client.hset(mapping_key, mapping=mapping)

    def _normalize_vector(self, embedding: List[float]) -> np.ndarray:
        """将向量归一化，用于余弦相似度计算。"""
        vec = np.array(embedding, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def _generate_key(self, text: str) -> str:
        """基于文本内容生成缓存键。"""
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"{self.prefix}:{self.name}:{text_hash}"

    def _generate_cache_id(self) -> str:
        """生成唯一的缓存 ID。"""
        return str(uuid.uuid4())[:8]

    def get(
        self,
        query: str,
        embedding: List[float],
    ) -> Optional[str]:
        """
        根据查询文本和 embedding 查找缓存的响应。

        Args:
            query: 查询文本。
            embedding: 查询的 embedding 向量。

        Returns:
            缓存的响应文本，如果无匹配返回 None。
        """
        if self._index.ntotal == 0:
            return None

        # 归一化查询向量
        query_vec = self._normalize_vector(embedding).reshape(1, -1)

        # 在 FAISS 中搜索最相似的 1 个结果
        distances, indices = self._index.search(query_vec, 1)

        if len(indices) == 0 or indices[0][0] < 0:
            return None

        best_idx = indices[0][0]
        best_distance = distances[0][0]

        # 检查距离是否在阈值内
        if best_distance < (1.0 - self.distance_threshold):
            # 距离越大相似度越低，这里 best_distance 是余弦相似度
            return None

        # 从 Redis 获取缓存的响应
        redis_key = self._id_to_key.get(int(best_idx))
        if not redis_key:
            return None

        cached = self._redis_client.get(redis_key)
        if cached:
            return cached

        return None

    def set(
        self,
        query: str,
        embedding: List[float],
        response: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        将查询和响应存入缓存。

        Args:
            query: 查询文本。
            embedding: 查询的 embedding 向量。
            response: LLM 响应文本。
            metadata: 可选的元数据（如时间戳、模型名称等）。

        Returns:
            缓存 ID。
        """
        # 生成唯一 ID 和 Redis 键
        cache_id = self._generate_cache_id()
        redis_key = f"{self.prefix}:{self.name}:response:{cache_id}"

        # 归一化向量并添加到 FAISS 索引
        embedding_vec = self._normalize_vector(embedding).reshape(1, -1)
        faiss_id = self._next_id
        self._index.add(embedding_vec)

        # 更新映射
        self._id_to_key[faiss_id] = redis_key
        self._key_to_id[redis_key] = faiss_id
        self._next_id += 1

        # 存入 Redis（包含查询和响应）
        cache_data = {
            "query": query,
            "response": response,
            "metadata": metadata or {},
        }
        self._redis_client.setex(redis_key, self.ttl, json.dumps(cache_data, ensure_ascii=False))

        # 持久化索引到 Redis
        self._save_index_to_redis()

        return cache_id

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息。"""
        return {
            "name": self.name,
            "total_entries": self._index.ntotal,
            "distance_threshold": self.distance_threshold,
            "dimension": self.dimension,
            "ttl": self.ttl,
        }

    def clear(self) -> int:
        """
        清空所有缓存数据。

        Returns:
            删除的缓存条目数量。
        """
        if self._index.ntotal == 0:
            return 0

        # 删除所有相关的 Redis 键
        pattern = f"{self.prefix}:{self.name}:*"
        keys = self._redis_client.keys(pattern)
        deleted = 0
        if keys:
            deleted = self._redis_client.delete(*keys)

        # 重置 FAISS 索引
        self._index = faiss.IndexFlatIP(self.dimension)
        self._id_to_key.clear()
        self._key_to_id.clear()
        self._next_id = 0

        return deleted

    def ping(self) -> bool:
        """检查 Redis 连接是否正常。"""
        try:
            return self._redis_client.ping()
        except redis.ConnectionError:
            return False


class LLMCaller:
    """
    模拟 LLM 调用者（实际使用时替换为真实 LLM API）。
    """

    def __init__(self, model_name: str = "mock"):
        self.model_name = model_name

    def __call__(self, prompt: str) -> str:
        """根据提示词调用 LLM 并返回响应。"""
        # 模拟 LLM 调用延迟
        import time
        time.sleep(1)

        # 模拟返回响应
        return f"[{self.model_name}] 这是一个模拟响应，关于：{prompt[:20]}..."


class EmbeddingModel:
    """
    模拟 Embedding 模型（实际使用时替换为真实 embedding API）。
    """

    def __init__(self, dimension: int = 768):
        self.dimension = dimension

    def embed(self, text: str) -> List[float]:
        """将文本转换为 embedding 向量。"""
        # 模拟 embedding 计算
        import time
        time.sleep(0.5)

        # 生成伪随机但确定的向量
        np.random.seed(hash(text) % (2**32))
        vec = np.random.randn(self.dimension).astype(np.float32)
        # 归一化
        vec = vec / np.linalg.norm(vec)
        return vec.tolist()


# 示例用法
if __name__ == "__main__":
    """
    SemanticCache 使用示例

    本示例演示：
    1. 创建语义缓存实例
    2. 模拟 embedding 模型和 LLM 调用
    3. 展示语义缓存命中/未命中的效果
    """
    print("=" * 60)
    print("语义缓存示例")
    print("=" * 60)

    # 1. 创建语义缓存实例
    cache = SemanticCache(
        name="llm_cache",
        redis_url="redis://:admin123.@47.119.18.45:6379",
        ttl=3600,
        prefix="semantic",
        distance_threshold=0.1,
        dimension=768,
    )

    # 2. 检查 Redis 连接
    if not cache.ping():
        print("❌ Redis 连接失败")
        exit(1)
    print(f"✅ Redis 连接成功")
    print(f"📊 缓存状态: {cache.get_stats()}\n")

    # 3. 模拟组件
    embed_model = EmbeddingModel(dimension=768)
    llm_caller = LLMCaller(model_name="gpt-4")

    # 4. 测试语义缓存
    print("-" * 60)
    print("测试 1: 首次查询（未命中，需要调用 LLM）")
    print("-" * 60)
    query1 = "如何学习 Python 编程？"

    import time
    start = time.time()
    embedding1 = embed_model.embed(query1)
    cached_response1 = cache.get(query1, embedding1)

    if cached_response1:
        print(f"✅ 缓存命中: {cached_response1[:50]}...")
    else:
        print("🔄 缓存未命中，调用 LLM...")
        response1 = llm_caller(query1)
        cache_id1 = cache.set(query1, embedding1, response1)
        print(f"💾 已缓存，ID: {cache_id1}")
        print(f"📝 LLM 响应: {response1[:50]}...")
    print(f"⏱️ 耗时: {time.time() - start:.2f}s\n")

    # 5. 相似查询测试
    print("-" * 60)
    print("测试 2: 相似查询（应该命中缓存）")
    print("-" * 60)
    query2 = "怎么学习 Python 编程？"

    start = time.time()
    embedding2 = embed_model.embed(query2)
    cached_response2 = cache.get(query2, embedding2)

    if cached_response2:
        print(f"✅ 缓存命中！无需调用 LLM")
        print(f"📝 缓存响应: {cached_response2[:50]}...")
    else:
        print("🔄 缓存未命中，调用 LLM...")
        response2 = llm_caller(query2)
        cache_id2 = cache.set(query2, embedding2, response2)
        print(f"💾 已缓存，ID: {cache_id2}")
        print(f"📝 LLM 响应: {response2[:50]}...")
    print(f"⏱️ 耗时: {time.time() - start:.2f}s\n")

    # 6. 不同查询测试
    print("-" * 60)
    print("测试 3: 完全不同查询（应该未命中）")
    print("-" * 60)
    query3 = "什么是机器学习？"

    start = time.time()
    embedding3 = embed_model.embed(query3)
    cached_response3 = cache.get(query3, embedding3)

    if cached_response3:
        print(f"✅ 缓存命中: {cached_response3[:50]}...")
    else:
        print("🔄 缓存未命中，调用 LLM...")
        response3 = llm_caller(query3)
        cache_id3 = cache.set(query3, embedding3, response3)
        print(f"💾 已缓存，ID: {cache_id3}")
        print(f"📝 LLM 响应: {response3[:50]}...")
    print(f"⏱️ 耗时: {time.time() - start:.2f}s\n")

    # 7. 最终统计
    print("-" * 60)
    print("最终缓存状态")
    print("-" * 60)
    print(f"📊 {cache.get_stats()}")

    print("\n✨ 示例运行完成！")
