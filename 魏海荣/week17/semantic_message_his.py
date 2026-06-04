"""
Semantic Message History Module

基于 Redis 的对话历史管理器。
将多轮对话存储为 JSON 数组，支持按时间、按角色、按字符串相似度查询历史。
默认缓存 24 小时，到期自动删除。
"""

import json
import time
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Literal
from difflib import SequenceMatcher

import redis


class SemanticMessageHistory:
    """
    对话历史管理器。

    支持：
    - 多轮对话存储（JSON 数组格式）
    - 按时间范围查询
    - 按角色筛选（user/assistant/system）
    - 按字符串相似度搜索
    - 自动过期删除（默认 24 小时）
    """

    def __init__(
        self,
        name: str = "msg_history",
        redis_url: str = "redis://:admin123.@47.119.18.45:6379",
        ttl: int = 86400,
        prefix: str = "msg_history",
    ):
        """
        初始化对话历史管理器。

        Args:
            name: 会话实例名称。
            redis_url: Redis 连接 URL。
            ttl: 消息有效期（秒），默认 24 小时。
            prefix: Redis 键前缀。
        """
        self.name = name
        self.ttl = ttl
        self.prefix = prefix

        # 初始化 Redis 客户端
        self._redis_client = redis.from_url(redis_url, decode_responses=True)

    def _generate_session_id(self) -> str:
        """生成唯一的会话 ID。"""
        return str(uuid.uuid4())

    def _generate_message_id(self) -> str:
        """生成唯一的消息 ID。"""
        return str(uuid.uuid4())[:12]

    def _build_key(self, session_id: str) -> str:
        """构建 Redis 键。"""
        return f"{self.prefix}:{self.name}:session:{session_id}"

    def _build_index_key(self, session_id: str) -> str:
        """构建索引键（用于按时间排序）。"""
        return f"{self.prefix}:{self.name}:index:{session_id}"

    def create_session(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        创建新会话。

        Args:
            metadata: 可选的会话元数据（如用户信息、标题等）。

        Returns:
            会话 ID。
        """
        session_id = self._generate_session_id()
        key = self._build_key(session_id)

        session_data = {
            "session_id": session_id,
            "messages": [],
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        # 设置会话数据和过期时间
        self._redis_client.setex(key, self.ttl, json.dumps(session_data, ensure_ascii=False))

        # 添加到时间索引
        index_key = self._build_index_key(session_id)
        self._redis_client.zadd(index_key, {session_id: time.time()})

        return session_id

    def add_message(
        self,
        session_id: str,
        role: Literal["user", "assistant", "system", "function"],
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        向会话添加消息。

        Args:
            session_id: 会话 ID。
            role: 角色（user/assistant/system/function）。
            content: 消息内容。
            metadata: 可选的元数据（如函数名、token 数量等）。

        Returns:
            消息 ID，失败返回 None。
        """
        key = self._build_key(session_id)

        # 获取现有会话数据
        session_data = self._redis_client.get(key)
        if not session_data:
            return None

        session = json.loads(session_data)

        # 创建新消息
        message_id = self._generate_message_id()
        message = {
            "message_id": message_id,
            "role": role,
            "content": content,
            "created_at": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

        # 添加消息并更新时间戳
        session["messages"].append(message)
        session["updated_at"] = datetime.now().isoformat()

        # 重新存储（刷新 TTL）
        self._redis_client.setex(key, self.ttl, json.dumps(session, ensure_ascii=False))

        return message_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话完整信息。

        Args:
            session_id: 会话 ID。

        Returns:
            会话数据，失败返回 None。
        """
        key = self._build_key(session_id)
        session_data = self._redis_client.get(key)

        if not session_data:
            return None

        return json.loads(session_data)

    def get_messages(
        self,
        session_id: str,
        role: Optional[Literal["user", "assistant", "system", "function"]] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        获取会话中的消息。

        Args:
            session_id: 会话 ID。
            role: 可选，按角色筛选。
            limit: 可选，限制返回数量。
            offset: 偏移量（从最新消息开始），默认 0。

        Returns:
            消息列表。
        """
        session = self.get_session(session_id)
        if not session:
            return []

        messages = session.get("messages", [])

        # 按角色筛选
        if role:
            messages = [m for m in messages if m.get("role") == role]

        # 翻转顺序（从旧到新）
        messages = list(reversed(messages))

        # 分页
        if offset > 0:
            messages = messages[offset:]

        if limit:
            messages = messages[:limit]

        return messages

    def get_latest_messages(
        self,
        session_id: str,
        count: int = 10,
        role: Optional[Literal["user", "assistant", "system"]] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取最近的 N 条消息（从新到旧）。

        Args:
            session_id: 会话 ID。
            count: 返回消息数量。
            role: 可选，按角色筛选。

        Returns:
            消息列表。
        """
        session = self.get_session(session_id)
        if not session:
            return []

        messages = session.get("messages", [])

        # 按角色筛选
        if role:
            messages = [m for m in messages if m.get("role") == role]

        # 返回最新的 N 条（从后往前取）
        return messages[-count:] if count > 0 else messages

    def search_by_time(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        按时间范围查询消息。

        Args:
            start_time: 开始时间。
            end_time: 结束时间。
            session_id: 可选，限定会话 ID。

        Returns:
            匹配的消息列表。
        """
        results = []

        # 确定搜索范围
        if session_id:
            session_ids = [session_id]
        else:
            # 获取所有会话 ID
            index_pattern = f"{self.prefix}:{self.name}:index:*"
            index_keys = self._redis_client.keys(index_pattern)
            session_ids = [
                k.decode() if isinstance(k, bytes) else k
                for k in index_keys
            ]
            session_ids = [sid.replace(f"{self.prefix}:{self.name}:index:", "") for sid in session_ids]

        # 遍历会话查找匹配的消息
        for sid in session_ids:
            session = self.get_session(sid)
            if not session:
                continue

            for msg in session.get("messages", []):
                try:
                    msg_time = datetime.fromisoformat(msg.get("created_at", ""))
                    if start_time and msg_time < start_time:
                        continue
                    if end_time and msg_time > end_time:
                        continue

                    results.append({
                        "session_id": sid,
                        **msg
                    })
                except (ValueError, TypeError):
                    continue

        # 按时间排序
        results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return results

    def search_by_content(
        self,
        keyword: str,
        session_id: Optional[str] = None,
        similarity_threshold: float = 0.6,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        按内容相似度搜索消息。

        Args:
            keyword: 搜索关键词。
            session_id: 可选，限定会话 ID。
            similarity_threshold: 相似度阈值（0-1）。
            limit: 返回结果数量限制。

        Returns:
            匹配的消息列表（按相似度降序）。
        """
        results = []

        # 确定搜索范围
        if session_id:
            session_ids = [session_id]
        else:
            index_pattern = f"{self.prefix}:{self.name}:index:*"
            index_keys = self._redis_client.keys(index_pattern)
            session_ids = [
                k.decode() if isinstance(k, bytes) else k
                for k in index_keys
            ]
            session_ids = [sid.replace(f"{self.prefix}:{self.name}:index:", "") for sid in session_ids]

        # 遍历会话计算相似度
        for sid in session_ids:
            session = self.get_session(sid)
            if not session:
                continue

            for msg in session.get("messages", []):
                content = msg.get("content", "")
                similarity = SequenceMatcher(None, keyword, content).ratio()

                if similarity >= similarity_threshold:
                    results.append({
                        "session_id": sid,
                        "similarity": similarity,
                        **msg
                    })

        # 按相似度降序排序
        results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        return results[:limit]

    def search_by_role(
        self,
        role: Literal["user", "assistant", "system", "function"],
        session_id: Optional[str] = None,
        keyword: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        按角色筛选消息，可选附加内容关键词过滤。

        Args:
            role: 角色类型。
            session_id: 可选，限定会话 ID。
            keyword: 可选，内容关键词。
            limit: 返回结果数量限制。

        Returns:
            匹配的消息列表。
        """
        results = []

        # 确定搜索范围
        if session_id:
            session_ids = [session_id]
        else:
            index_pattern = f"{self.prefix}:{self.name}:index:*"
            index_keys = self._redis_client.keys(index_pattern)
            session_ids = [
                k.decode() if isinstance(k, bytes) else k
                for k in index_keys
            ]
            session_ids = [sid.replace(f"{self.prefix}:{self.name}:index:", "") for sid in session_ids]

        # 遍历会话查找匹配的消息
        for sid in session_ids:
            session = self.get_session(sid)
            if not session:
                continue

            for msg in session.get("messages", []):
                if msg.get("role") != role:
                    continue

                if keyword and keyword not in msg.get("content", ""):
                    continue

                results.append({
                    "session_id": sid,
                    **msg
                })

        # 按时间降序排序
        results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return results[:limit]

    def delete_message(self, session_id: str, message_id: str) -> bool:
        """
        删除指定消息。

        Args:
            session_id: 会话 ID。
            message_id: 消息 ID。

        Returns:
            是否删除成功。
        """
        key = self._build_key(session_id)
        session_data = self._redis_client.get(key)

        if not session_data:
            return False

        session = json.loads(session_data)
        original_len = len(session["messages"])

        session["messages"] = [
            m for m in session["messages"]
            if m.get("message_id") != message_id
        ]

        if len(session["messages"]) == original_len:
            return False

        session["updated_at"] = datetime.now().isoformat()
        self._redis_client.setex(key, self.ttl, json.dumps(session, ensure_ascii=False))
        return True

    def delete_session(self, session_id: str) -> bool:
        """
        删除整个会话。

        Args:
            session_id: 会话 ID。

        Returns:
            是否删除成功。
        """
        key = self._build_key(session_id)
        index_key = self._build_index_key(session_id)

        deleted = self._redis_client.delete(key)
        self._redis_client.delete(index_key)

        return deleted > 0

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        """
        获取所有会话列表（按更新时间降序）。

        Returns:
            会话列表。
        """
        index_pattern = f"{self.prefix}:{self.name}:index:*"
        index_keys = self._redis_client.keys(index_pattern)

        sessions = []
        for key in index_keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            session_id = key_str.replace(f"{self.prefix}:{self.name}:index:", "")
            session = self.get_session(session_id)
            if session:
                sessions.append(session)

        # 按更新时间降序排序
        sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return sessions

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息。"""
        sessions = self.get_all_sessions()
        total_messages = sum(len(s.get("messages", [])) for s in sessions)

        role_counts = {}
        for session in sessions:
            for msg in session.get("messages", []):
                role = msg.get("role", "unknown")
                role_counts[role] = role_counts.get(role, 0) + 1

        return {
            "name": self.name,
            "total_sessions": len(sessions),
            "total_messages": total_messages,
            "messages_by_role": role_counts,
            "ttl_seconds": self.ttl,
        }

    def ping(self) -> bool:
        """检查 Redis 连接。"""
        try:
            return self._redis_client.ping()
        except redis.ConnectionError:
            return False


# 示例用法
if __name__ == "__main__":
    """
    SemanticMessageHistory 使用示例

    演示：
    1. 创建会话和添加消息
    2. 按角色查询
    3. 按时间查询
    4. 按内容相似度搜索
    """
    print("=" * 60)
    print("对话历史管理器示例")
    print("=" * 60)

    # 1. 初始化管理器
    history = SemanticMessageHistory(
        name="demo_chat",
        redis_url="redis://:admin123.@47.119.18.45:6379",
        ttl=86400,  # 24 小时
        prefix="chat",
    )

    # 2. 检查连接
    if not history.ping():
        print("❌ Redis 连接失败")
        exit(1)
    print(f"✅ Redis 连接成功")
    print(f"📊 初始状态: {history.get_stats()}\n")

    # 3. 创建会话
    print("-" * 60)
    print("创建会话")
    print("-" * 60)
    session_id = history.create_session(metadata={"user": "demo_user", "title": "测试会话"})
    print(f"🆔 新会话 ID: {session_id}\n")

    # 4. 添加多轮对话
    print("-" * 60)
    print("添加对话消息")
    print("-" * 60)

    dialogs = [
        ("user", "你好，我想了解一下 Python 编程。"),
        ("assistant", "你好！Python 是一门简单易学的编程语言，适合初学者。我可以帮你学习 Python。"),
        ("user", "那应该怎么开始学习呢？"),
        ("assistant", "建议从基础语法开始，如变量、数据类型、条件语句和循环。推荐使用《Python编程：从入门到实践》这本书。"),
        ("user", "有没有在线教程推荐？"),
        ("assistant", "推荐慕课网、Bilibili 上的 Python 教程，以及官方文档：docs.python.org"),
        ("system", "用户正在学习 Python 编程，级别：入门"),
    ]

    for role, content in dialogs:
        msg_id = history.add_message(session_id, role, content)
        print(f"💬 [{role}] {content[:30]}... -> ID: {msg_id}")

    print()

    # 5. 获取最近消息
    print("-" * 60)
    print("获取最近 3 条消息")
    print("-" * 60)
    latest = history.get_latest_messages(session_id, count=3)
    for msg in latest:
        print(f"  [{msg['role']}] {msg['content'][:40]}...")

    print()

    # 6. 按角色查询
    print("-" * 60)
    print("查询所有 user 角色的消息")
    print("-" * 60)
    user_msgs = history.get_messages(session_id, role="user")
    for msg in user_msgs:
        print(f"  👤 {msg['content'][:40]}...")

    print()

    # 7. 按内容相似度搜索
    print("-" * 60)
    print("搜索与 'Python教程' 相关的内容")
    print("-" * 60)
    results = history.search_by_content("Python教程", similarity_threshold=0.3)
    for msg in results:
        print(f"  🔍 相似度: {msg['similarity']:.2f} | [{msg['role']}] {msg['content'][:40]}...")

    print()

    # 8. 按时间查询（最近一小时）
    print("-" * 60)
    print("查询最近 1 小时的消息")
    print("-" * 60)
    from datetime import datetime, timedelta
    recent = history.search_by_time(
        start_time=datetime.now() - timedelta(hours=1)
    )
    print(f"  找到 {len(recent)} 条消息")
    for msg in recent[:3]:
        print(f"  ⏰ {msg['created_at']} | [{msg['role']}] {msg['content'][:30]}...")

    print()

    # 9. 统计信息
    print("-" * 60)
    print("会话统计")
    print("-" * 60)
    print(f"  📊 {history.get_stats()}")

    print("\n✨ 示例运行完成！")
