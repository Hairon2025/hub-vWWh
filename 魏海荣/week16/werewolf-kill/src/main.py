"""
狼人杀游戏 - 主入口

运行方式:
    python src/main.py                    # 启动 API 服务器
    python src/main.py --help            # 显示帮助
"""

import argparse
import os
import sys

# 添加 src 到 path（支持相对导入）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用"""
    app = FastAPI(
        title="狼人杀 API",
        description="狼人杀游戏 API，支持创建游戏、逐回合执行、自动运行",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    return app


# 创建应用实例
app = create_app()


def run_api():
    """启动 API 服务器"""
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0")

    print(f"启动狼人杀 API 服务器: http://{host}:{port}")
    print(f"API 文档: http://{host}:{port}/docs")
    print(f"健康检查: http://{host}:{port}/health")

    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=True,
    )


def main():
    parser = argparse.ArgumentParser(description="狼人杀游戏")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    subparsers.add_parser("api", help="启动 API 服务器")

    args = parser.parse_args()

    if args.command == "api" or args.command is None:
        run_api()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
