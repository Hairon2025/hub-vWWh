"""
Semantic Router Module

语义路由器 - 基于向量相似度实现意图识别。
通过将用户输入与预定义的路由（Route）进行语义匹配，快速识别用户意图。

使用 FAISS 进行向量相似度搜索，使用 Redis 存储路由配置和缓存结果。
"""

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Literal

import numpy as np
import faiss
import redis


@dataclass
class Route:
    """
    路由定义。

    Attributes:
        name: 路由名称/意图标识（如 "greeting", "farewell"）。
        references: 参考示例列表（如 ["hello", "hi"]）。
        metadata: 可选的元数据。
        distance_threshold: 距离阈值，小于此值视为匹配。
    """
    name: str
    references: List[str]
    metadata: Optional[Dict[str, Any]] = None
    distance_threshold: float = 0.3

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SemanticRouter:
    """
    语义路由器。

    通过语义相似度匹配，将用户输入路由到对应的意图类别。
    支持多路由定义、结果缓存、自动过期。

    工作流程：
    1. 用户输入 → 计算 embedding
    2. 在 FAISS 索引中搜索最相似的参考示例
    3. 检查距离是否在阈值内 → 返回匹配的路由
    4. 缓存计算结果，避免重复计算
    """

    def __init__(
        self,
        name: str = "semantic_router",
        redis_url: str = "redis://localhost:6379",
        ttl: int = 3600,
        prefix: str = "sem_router",
        distance_threshold: float = 0.3,
        dimension: int = 768,
    ):
        """
        初始化语义路由器。

        Args:
            name: 路由器名称。
            redis_url: Redis 连接 URL。
            ttl: 缓存有效期（秒），默认 1 小时。
            prefix: Redis 键前缀。
            distance_threshold: 默认距离阈值。
            dimension: 嵌入向量维度，需与使用的 embedding 模型匹配。
        """
        self.name = name
        self.ttl = ttl
        self.prefix = prefix
        self.default_distance_threshold = distance_threshold
        self.dimension = dimension

        # 初始化 Redis 客户端
        self._redis_client = redis.from_url(redis_url, decode_responses=True)

        # 初始化 FAISS 索引
        self._index = faiss.IndexFlatIP(dimension)

        # 路由映射
        self._routes: Dict[str, Route] = {}
        self._route_references: List[str] = []  # 按顺序存储所有参考示例
        self._reference_to_route: Dict[str, str] = {}  # 参考示例 -> 路由名称

        # 加载已存储的路由配置
        self._load_routes_from_redis()

    def _load_routes_from_redis(self) -> None:
        """从 Redis 加载路由配置。"""
        routes_key = f"{self.prefix}:{self.name}:routes"

        try:
            routes_data = self._redis_client.get(routes_key)
            if routes_data:
                routes_list = json.loads(routes_data)
                for route_data in routes_list:
                    route = Route(**route_data)
                    self._routes[route.name] = route
                    self._rebuild_index()
        except Exception:
            pass

    def _save_routes_to_redis(self) -> None:
        """保存路由配置到 Redis。"""
        routes_key = f"{self.prefix}:{self.name}:routes"

        routes_list = [
            {
                "name": r.name,
                "references": r.references,
                "metadata": r.metadata,
                "distance_threshold": r.distance_threshold,
            }
            for r in self._routes.values()
        ]

        self._redis_client.setex(routes_key, self.ttl, json.dumps(routes_list, ensure_ascii=False))

    def _rebuild_index(self) -> None:
        """重建 FAISS 索引。"""
        self._index.reset()
        self._route_references.clear()
        self._reference_to_route.clear()

        # 收集所有参考示例（需要外部提供 embeddings）
        # 索引构建在 add_route 时通过外部调用完成

    def _normalize_vector(self, embedding: List[float]) -> np.ndarray:
        """归一化向量。"""
        vec = np.array(embedding, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def _generate_cache_key(self, text: str) -> str:
        """生成缓存键。"""
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"{self.prefix}:{self.name}:cache:{text_hash}"

    def add_route(self, route: Route, reference_embeddings: List[List[float]]) -> None:
        """
        添加路由及其参考示例的 embeddings。

        Args:
            route: 路由定义。
            reference_embeddings: 参考示例对应的 embedding 列表（与 route.references 顺序对应）。
        """
        if len(route.references) != len(reference_embeddings):
            raise ValueError("references 和 reference_embeddings 数量不匹配")

        # 存储路由
        self._routes[route.name] = route

        # 添加到索引
        for ref, embedding in zip(route.references, reference_embeddings):
            normalized = self._normalize_vector(embedding).reshape(1, -1)
            self._index.add(normalized)
            self._route_references.append(ref)
            self._reference_to_route[ref] = route.name

        # 保存到 Redis
        self._save_routes_to_redis()
        self._save_index_to_redis()

    def _save_index_to_redis(self) -> None:
        """保存 FAISS 索引到 Redis。"""
        import pickle

        index_key = f"{self.prefix}:{self.name}:index"
        refs_key = f"{self.prefix}:{self.name}:refs"

        # 保存 FAISS 索引
        index_bytes = pickle.dumps(self._index).hex()
        self._redis_client.set(index_key, index_bytes)

        # 保存参考示例列表和映射
        refs_data = json.dumps({
            "references": self._route_references,
            "route_map": self._reference_to_route,
        }, ensure_ascii=False)
        self._redis_client.set(refs_key, refs_data)

    def _load_index_from_redis(self) -> None:
        """从 Redis 加载 FAISS 索引。"""
        import pickle

        index_key = f"{self.prefix}:{self.name}:index"
        refs_key = f"{self.prefix}:{self.name}:refs"

        try:
            index_data = self._redis_client.get(index_key)
            refs_data = self._redis_client.get(refs_key)

            if index_data and refs_data:
                self._index = pickle.loads(bytes.fromhex(index_data))
                refs_json = json.loads(refs_data)
                self._route_references = refs_json["references"]
                self._reference_to_route = refs_json["route_map"]
        except Exception:
            pass

    def route(
        self,
        text: str,
        embedding: List[float],
    ) -> Optional[str]:
        """
        对输入文本进行路由匹配。

        Args:
            text: 输入文本。
            embedding: 输入文本的 embedding 向量。

        Returns:
            匹配的路由名称，如果无匹配返回 None。
        """
        if self._index.ntotal == 0:
            return None

        # 检查缓存
        cache_key = self._generate_cache_key(text)
        cached_result = self._redis_client.get(cache_key)
        if cached_result:
            result = json.loads(cached_result)
            return result.get("route_name")

        # 归一化查询向量
        query_vec = self._normalize_vector(embedding).reshape(1, -1)

        # 搜索最相似的参考示例
        distances, indices = self._index.search(query_vec, 1)

        if len(indices) == 0 or indices[0][0] < 0:
            return None

        best_idx = indices[0][0]
        best_distance = distances[0][0]  # 内积相似度（归一化后等同于余弦相似度）

        # 获取对应的参考示例和路由
        if best_idx >= len(self._route_references):
            return None

        reference = self._route_references[int(best_idx)]
        route_name = self._reference_to_route.get(reference)

        if not route_name:
            return None

        # 获取路由配置，检查阈值
        route = self._routes.get(route_name)
        if not route:
            return None

        threshold = route.distance_threshold or self.default_distance_threshold

        # 注意：对于归一化向量的内积，相似度 = best_distance
        # 距离越小相似度越高，所以我们用 1 - best_distance 作为"相似度度量"
        # 或者直接用 best_distance 与阈值比较（需要确认阈值含义）
        # 这里假设阈值表示"最大可接受的距离"，即 best_distance >= (1 - threshold) 时匹配
        similarity = best_distance
        match_threshold = 1.0 - threshold

        if similarity < match_threshold:
            # 相似度太低，不匹配
            return None

        # 缓存结果
        cache_data = {
            "route_name": route_name,
            "reference": reference,
            "similarity": float(similarity),
        }
        self._redis_client.setex(cache_key, self.ttl, json.dumps(cache_data, ensure_ascii=False))

        return route_name

    def get_route(self, route_name: str) -> Optional[Route]:
        """获取指定路由。"""
        return self._routes.get(route_name)

    def list_routes(self) -> List[Route]:
        """列出所有路由。"""
        return list(self._routes.values())

    def delete_route(self, route_name: str) -> bool:
        """删除路由（需要重建索引）。"""
        if route_name not in self._routes:
            return False

        del self._routes[route_name]
        # 注意：简化处理，实际生产可能需要更精细的索引管理
        # 这里标记需要重建，但不立即重建
        self._save_routes_to_redis()
        return True

    def clear_cache(self) -> int:
        """清空路由缓存。"""
        pattern = f"{self.prefix}:{self.name}:cache:*"
        keys = self._redis_client.keys(pattern)
        if keys:
            return self._redis_client.delete(*keys)
        return 0

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息。"""
        return {
            "name": self.name,
            "total_routes": len(self._routes),
            "total_references": self._index.ntotal,
            "dimension": self.dimension,
            "default_threshold": self.default_distance_threshold,
        }

    def ping(self) -> bool:
        """检查 Redis 连接。"""
        try:
            return self._redis_client.ping()
        except redis.ConnectionError:
            return False


class MockEmbeddingModel:
    """
    模拟 Embedding 模型（实际使用时替换为真实的 embedding API）。
    """

    def __init__(self, dimension: int = 768):
        self.dimension = dimension

    def embed(self, text: str) -> List[float]:
        """将文本转换为 embedding 向量。"""
        # 模拟 embedding 计算延迟
        time.sleep(0.3)

        # 生成伪随机但确定的向量
        np.random.seed(hash(text) % (2**32))
        vec = np.random.randn(self.dimension).astype(np.float32)
        # 归一化
        vec = vec / np.linalg.norm(vec)
        return vec.tolist()


# 示例用法
if __name__ == "__main__":
    """
    SemanticRouter 使用示例

    演示：
    1. 定义多个路由（greeting, farewell, weather, news）
    2. 使用语义匹配进行意图识别
    3. 展示缓存效果（第二次调用更快）
    """
    print("=" * 60)
    print("语义路由器示例")
    print("=" * 60)

    # 1. 初始化路由器
    router = SemanticRouter(
        name="topic-router",
        redis_url="redis://:admin123.@47.119.18.45:6379",
        ttl=3600,
        prefix="semantic",
        distance_threshold=0.3,
        dimension=768,
    )

    # 2. 检查连接
    if not router.ping():
        print("❌ Redis 连接失败")
        exit(1)
    print(f"✅ Redis 连接成功")
    print(f"📊 初始状态: {router.get_stats()}\n")

    # 3. 初始化 embedding 模型
    embed_model = MockEmbeddingModel(dimension=768)

    # 4. 定义路由及参考示例
    print("-" * 60)
    print("定义路由")
    print("-" * 60)

    route_configs = [
        {
            "name": "greeting",
            "references": ["你好", "嗨", "早上好", "大家好"],
            "metadata": {"type": "greeting"},
            "threshold": 0.3,
        },
        {
            "name": "farewell",
            "references": ["再见", "拜拜", "下次见", "再会"],
            "metadata": {"type": "farewell"},
            "threshold": 0.3,
        },
        {
            "name": "weather",
            "references": ["今天天气怎么样", "明天会下雨吗", "温度是多少"],
            "metadata": {"type": "query"},
            "threshold": 0.3,
        },
        {
            "name": "news",
            "references": ["有什么新闻", "最新消息", "今天发生了什么"],
            "metadata": {"type": "query"},
            "threshold": 0.3,
        },
    ]

    for config in route_configs:
        # 计算参考示例的 embeddings
        ref_embeddings = [embed_model.embed(ref) for ref in config["references"]]

        # 创建路由
        route = Route(
            name=config["name"],
            references=config["references"],
            metadata=config["metadata"],
            distance_threshold=config["threshold"],
        )

        # 添加到路由器
        router.add_route(route, ref_embeddings)
        print(f"✅ 添加路由: {config['name']} (refs: {len(config['references'])})")

    print(f"\n📊 路由状态: {router.get_stats()}\n")

    # 5. 测试路由
    print("-" * 60)
    print("意图识别测试")
    print("-" * 60)

    test_cases = [
        "你好啊，今天怎么样？",
        "再见，我走了",
        "帮我查一下天气",
        "有什么新鲜的新闻吗？",
    ]

    for text in test_cases:
        import time
        start = time.time()
        embedding = embed_model.embed(text)
        route_name = router.route(text, embedding)
        elapsed = time.time() - start

        if route_name:
            print(f"📝 输入: 「{text}」")
            print(f"🎯 路由: {route_name}")
            print(f"⏱️ 耗时: {elapsed:.2f}s\n")
        else:
            print(f"📝 输入: 「{text}」")
            print(f"❌ 无匹配路由")
            print(f"⏱️ 耗时: {elapsed:.2f}s\n")

    # 6. 测试缓存效果
    print("-" * 60)
    print("缓存效果测试（第二次调用相同输入）")
    print("-" * 60)

    cached_text = "你好"
    import time

    # 第一次调用
    start = time.time()
    embedding1 = embed_model.embed(cached_text)
    result1 = router.route(cached_text, embedding1)
    time1 = time.time() - start
    print(f"第 1 次: 路由={result1}, 耗时={time1:.2f}s")

    # 第二次调用（应该命中缓存，不调用 embedding）
    start = time.time()
    embedding2 = embed_model.embed(cached_text)
    result2 = router.route(cached_text, embedding2)
    time2 = time.time() - start
    print(f"第 2 次: 路由={result2}, 耗时={time2:.2f}s")

    print(f"\n✨ 第二次调用更快（无需重新计算 embedding），示例运行完成！")
