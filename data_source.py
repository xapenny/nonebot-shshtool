import aiohttp
from nonebot import Driver
import nonebot

headers = {
    'User-Agent': r'%E8%AE%BE%E7%BD%AE/1053 CFNetwork/1209 Darwin/20.2.0',
    'Content-Type': 'application/x-www-form-urlencoded',
    'X-CPU-STATE': '3c5830a2ced49192e80986df2c26d310ea285496'
    }

driver: Driver = nonebot.get_driver()

async def get_payload(operation, payload) -> dict:
    return_list = []
    async with aiohttp.ClientSession(headers=headers) as session:
        url = f'https://api.arx8x.net/{operation}'
        try:
            async with session.post(url, timeout=10, data=payload) as response:
                response = await response.text()
                return response
        except Exception as ex:
            print(f'请求超时！{ex}')
            return -1
