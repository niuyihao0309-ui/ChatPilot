# itwwy/infrastructure/http_client.py

import asyncio

from httpx import AsyncClient

# 全局变量
http_client: AsyncClient | None = None


def init_http_client():
    global http_client
    # trust_env=False: 不读 HTTP_PROXY/HTTPS_PROXY 环境变量，强制直连本机服务。
    # 否则 Clash 等代理会拦截 localhost 请求，导致拿到非 JSON 内容报 JSONDecodeError。
    http_client = AsyncClient(timeout=10.0, trust_env=False)
    # http_client = AsyncClient(timeout=10.0)


async def close_http_client():
    if http_client is not None:
        await http_client.aclose()


if __name__ == '__main__':
    async def test():
        init_http_client()
        result = await http_client.get('http://localhost:18081/users/u1001/orders')
        if result.status_code != 200 or not result.text:
            print(f"异常响应: {result.status_code} | body: {result.text!r}")
        else:
            print(result.json()['data']['orders'])

        await close_http_client()


    asyncio.run(test())
