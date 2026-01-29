import aiohttp
import asyncio

BASE_URL = "https://example.com/collector"  # replace with URL
TIMEOUT = aiohttp.ClientTimeout(total=15)


async def _post(path: str, payload: dict):
    url = f"{BASE_URL}/{path}"
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        try:
            async with session.post(url, json=payload) as resp:
                text = await resp.text()
                if resp.status >= 200 and resp.status < 300:
                    print(f"[OK] POST {url} status={resp.status}")
                    return True, resp.status, text
                else:
                    print(f"[ERROR] POST {url} status={resp.status} body={text}")
                    return False, resp.status, text
        except Exception as e:
            print(f"[EXCEPTION] POST {url} error={e}")
            return False, None, str(e)


async def send_system(data: dict):
    return await _post("system", data)


async def send_planet(data: dict):
    return await _post("planet", data)


async def send_flora(data: dict):
    return await _post("flora", data)


async def send_fauna(data: dict):
    return await _post("fauna", data)


async def send_archaeology(data: dict):
    return await _post("archaeology", data)


async def send_mineral(data: dict):
    return await _post("mineral", data)