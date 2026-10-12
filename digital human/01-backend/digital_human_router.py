# api/routers/digital_human_router.py
"""数字人（魔珐星云）凭证接口。

密钥只存在后端 .env，绝不下发到前端源码（安全红线）。
前端初始化魔珐 SDK 前，先 GET 本接口拿 app_id / app_secret / gateway_server。
Vite 会把 /api/* 代理到后端 18082，前端可直接 fetch 相对路径。
"""
from fastapi import APIRouter

from conf.config import settings

router = APIRouter()


@router.get("/api/digital-human/credentials")
async def get_digital_human_credentials() -> dict:
    """返回数字人 SDK 初始化所需凭证。

    未配置时 app_id / app_secret 为空串，前端据此提示「后端未配置数字人凭证」。
    """
    return {
        "app_id": settings.digital_human_app_id,
        "app_secret": settings.digital_human_app_secret,
        "gateway_server": settings.digital_human_gateway_server,
    }
