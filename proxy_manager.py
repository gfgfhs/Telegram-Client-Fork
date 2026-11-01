"""
Поиск и проверка бесплатных SOCKS5 прокси.
Бесплатные прокси часто мёртвые/медленные — это лучшее, что можно сделать без денег.
"""

import asyncio
import random
from typing import Optional

import aiohttp

# Публичные списки SOCKS5 (обновляются часто)
PROXY_SOURCES = [
    "https://raw.githubusercontent.com/proxio-io/proxy-list/main/socks5.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/ProxyScrape/free-proxy-list/main/proxies/socks5.txt",
    "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/socks5/data.txt",
]


async def fetch_proxies(session: aiohttp.ClientSession, url: str) -> list[str]:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return []
            text = await resp.text()
            proxies = []
            for line in text.strip().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # формат ip:port или protocol://ip:port
                if "://" in line:
                    line = line.split("://", 1)[1]
                if ":" in line and line.count(":") == 1:
                    proxies.append(line)
            return proxies
    except Exception:
        return []


async def get_free_socks5_list(limit: int = 80) -> list[str]:
    """Скачивает бесплатные SOCKS5 прокси из нескольких источников."""
    all_proxies = set()
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_proxies(session, url) for url in PROXY_SOURCES]
        results = await asyncio.gather(*tasks)
        for lst in results:
            all_proxies.update(lst)

    proxies = list(all_proxies)
    random.shuffle(proxies)
    return proxies[:limit]


async def test_proxy(proxy: str, timeout: float = 6.0) -> bool:
    """
    Быстрая проверка, что прокси вообще отвечает.
    Не гарантирует работу с Telegram, но отсеивает мёртвые.
    """
    try:
        # Проверяем через httpbin или просто TCP-соединение через прокси сложно без python-socks
        # Простая проверка: пытаемся открыть сокет (грубо, но быстро)
        host, port = proxy.split(":")
        port = int(port)
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout,
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False
    except Exception:
        return False


async def find_working_proxy(max_try: int = 25) -> Optional[str]:
    """
    Ищет живой SOCKS5 прокси.
    Возвращает строку "ip:port" или None.
    """
    print("[*] Скачиваю списки бесплатных SOCKS5 прокси...")
    proxies = await get_free_socks5_list(limit=120)
    if not proxies:
        print("[!] Не удалось скачать списки прокси")
        return None

    print(f"[*] Получено {len(proxies)} прокси. Проверяю первые {max_try}...")

    for i, proxy in enumerate(proxies[:max_try], 1):
        print(f"    [{i}/{max_try}] {proxy} ...", end=" ", flush=True)
        ok = await test_proxy(proxy, timeout=5.0)
        if ok:
            print("OK")
            return proxy
        print("dead")

    print("[!] Не нашёл живой прокси из бесплатных списков")
    return None


def proxy_to_telethon(proxy: str) -> tuple:
    """
    Преобразует ip:port в формат, который принимает Telethon.
    Telethon: (socks.SOCKS5, host, port)
    """
    import socks  # PySocks

    host, port = proxy.split(":")
    return (socks.SOCKS5, host, int(port))
