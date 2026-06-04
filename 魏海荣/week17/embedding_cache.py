"""
Embedding Cache Module

Caches text-to-vector embeddings in Redis to avoid recomputation of expensive embedding generation.
Based on RedisVL design philosophy.
"""

import hashlib
import json
from typing import Optional, List, Union
import redis


class EmbeddingsCache:
    """
    Embeddings cache that stores text embeddings in Redis.

    Avoids redundant embedding computation by caching results based on text content.
    """

    def __init__(
        self,
        name: str = "embed_cache",
        redis_url: str = "redis://:admin123.@47.119.18.45:6379",
        ttl: int = 3600,
        prefix: str = "embed_cache",
    ):
        """
        Initialize the embeddings cache.

        Args:
            name: Name identifier for this cache instance.
            redis_url: Redis connection URL.
            ttl: Time-to-live for cached embeddings in seconds (default: 1 hour).
            prefix: Key prefix for Redis storage.
        """
        self.name = name
        self.ttl = ttl
        self.prefix = prefix

        # Parse redis_url and create connection
        self._redis_client = redis.from_url(redis_url, decode_responses=True)

    def _generate_key(self, text: str) -> str:
        """Generate a cache key based on text content hash."""
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"{self.prefix}:{self.name}:{text_hash}"

    def get(self, text: str) -> Optional[List[float]]:
        """
        Retrieve cached embedding for text.

        Args:
            text: Input text string.

        Returns:
            Cached embedding as list of floats, or None if not found.
        """
        key = self._generate_key(text)
        cached_data = self._redis_client.get(key)

        if cached_data is None:
            return None

        return json.loads(cached_data)

    def set(self, text: str, embedding: List[float]) -> None:
        """
        Store embedding for text in cache.

        Args:
            text: Input text string.
            embedding: Embedding vector as list of floats.
        """
        key = self._generate_key(text)
        self._redis_client.setex(
            key,
            self.ttl,
            json.dumps(embedding)
        )

    def exists(self, text: str) -> bool:
        """
        Check if embedding for text exists in cache.

        Args:
            text: Input text string.

        Returns:
            True if cached embedding exists, False otherwise.
        """
        key = self._generate_key(text)
        return self._redis_client.exists(key) > 0

    def delete(self, text: str) -> bool:
        """
        Delete cached embedding for text.

        Args:
            text: Input text string.

        Returns:
            True if deleted, False if key did not exist.
        """
        key = self._generate_key(text)
        return self._redis_client.delete(key) > 0

    def clear(self) -> int:
        """
        Clear all cached embeddings for this cache instance.

        Returns:
            Number of keys deleted.
        """
        pattern = f"{self.prefix}:{self.name}:*"
        keys = self._redis_client.keys(pattern)
        if keys:
            return self._redis_client.delete(*keys)
        return 0

    def ping(self) -> bool:
        """Check if Redis connection is alive."""
        try:
            return self._redis_client.ping()
        except redis.ConnectionError:
            return False


class CachedVectorizer:
    """
    A text vectorizer wrapper that automatically caches embeddings.

    Combines a vectorizer with an embedding cache - computes embeddings
    on cache miss and retrieves from cache on hit.
    """

    def __init__(
        self,
        vectorizer,
        cache: EmbeddingsCache,
    ):
        """
        Initialize the cached vectorizer.

        Args:
            vectorizer: An object with an `embed(text)` method that returns embeddings.
            cache: An EmbeddingsCache instance for storing/retrieving embeddings.
        """
        self.vectorizer = vectorizer
        self.cache = cache

    def embed(self, text: str) -> List[float]:
        """
        Get embedding for text, using cache when available.

        Args:
            text: Input text string.

        Returns:
            Embedding vector as list of floats.
        """
        # Try to get from cache first
        cached = self.cache.get(text)
        if cached is not None:
            return cached

        # Compute embedding on cache miss
        embedding = self.vectorizer.embed(text)

        # Store in cache for future use
        self.cache.set(text, embedding)

        return embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for multiple texts, using cache when available.

        Args:
            texts: List of input text strings.

        Returns:
            List of embedding vectors.
        """
        embeddings = []
        for text in texts:
            embeddings.append(self.embed(text))
        return embeddings


# 示例用法
if __name__ == "__main__":
    """
    EmbeddingsCache 使用示例

    本示例演示如何：
    1. 创建 EmbeddingsCache 实例
    2. 手动存储和获取 embeddings
    3. 使用 CachedVectorizer 包装自定义向量化器
    """
    import time

    # 1. 创建缓存实例（连接到本地 Redis）
    cache = EmbeddingsCache(
        name="demo_cache",
        redis_url = "redis://:admin123.@47.119.18.45:6379",
        ttl=3600,       # 缓存有效期 1 小时
        prefix="embed"
    )

    # 2. 检查 Redis 连接是否正常
    if not cache.ping():
        print("❌ Redis 连接失败，请确保 Redis 服务已启动")
        exit(1)

    print("✅ Redis 连接成功\n")

    # 3. 手动存储和获取 embeddings
    print("=== 手动缓存示例 ===")
    sample_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
    test_text = "这是一个测试文本"

    # 存入缓存
    cache.set(test_text, sample_embedding)
    print(f"📦 已缓存: {test_text}")

    # 从缓存取出
    retrieved = cache.get(test_text)
    print(f"📤 取出: {retrieved}")

    # 检查是否存在
    print(f"🔍 是否存在: {cache.exists(test_text)}\n")

    # 4. 使用 CachedVectorizer 自动缓存
    print("=== CachedVectorizer 示例 ===")

    # 模拟一个简单的向量化器（实际使用时替换为真实的 embedding 模型）
    class MockVectorizer:
        """模拟向量化器，实际项目中可替换为 OpenAI/HuggingFace 等 embedding 模型"""
        def embed(self, text: str) -> List[float]:
            # 模拟 embedding 计算延迟
            time.sleep(0.5)
            # 返回基于文本的伪随机向量
            return [hash(text) % 100 / 100 for _ in range(5)]

    # 创建向量化器
    vectorizer = MockVectorizer()

    # 用缓存包装向量化器
    cached_vectorizer = CachedVectorizer(vectorizer, cache)

    # 第一次调用（需要计算）
    start = time.time()
    result1 = cached_vectorizer.embed("你好世界")
    print(f"🔢 首次计算耗时: {time.time() - start:.2f}s, 结果: {result1}")

    # 第二次调用（从缓存读取）
    start = time.time()
    result2 = cached_vectorizer.embed("你好世界")
    print(f"⚡ 缓存命中耗时: {time.time() - start:.2f}s, 结果: {result2}")

    # 5. 清理示例
    print("\n=== 清理缓存 ===")
    deleted = cache.delete("这是一个测试文本")
    print(f"🗑️ 删除测试文本: {'成功' if deleted else '失败'}")
    cache.clear()
    print("🧹 已清空所有缓存")

    print("\n✨ 示例运行完成！")
