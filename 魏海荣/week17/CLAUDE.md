# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a vector search and intelligent caching service platform for LLM applications, built on Redis and RedisVL. The project provides a unified "capability middle platform" for AI application development within an organization.

Core components:
- **SemanticCache** - caches LLM responses based on semantic similarity of prompts (uses `distance_threshold` to determine cache hits)
- **EmbeddingsCache** - caches text-to-vector embeddings to avoid recomputation
- **SemanticMessageHistory** - stores conversation history with session-based retrieval
- **SemanticRouter** - intent recognition via semantic similarity routing

## Key Dependencies

- `redisvl` - Redis Vector Library for vector search and caching
- `redis` - Redis Python client

## Architecture Notes

The service leverages Redis for:
1. Vector similarity search (via Redis search module)
2. Semantic caching of LLM responses
3. Embedding result caching
4. Session-based conversation history management

## Redis Connection

Default connection: `redis://localhost:6379`

## Reference Implementation

RedisVL Python library: https://github.com/redis/redis-vl-python
