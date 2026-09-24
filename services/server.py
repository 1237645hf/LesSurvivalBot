"""
services/server.py — Keep-alive пингер и health-check HTTP-сервер.

Экспортирует:
    keep_alive_pinger(interval_seconds)  — корутина периодического пинга Render
    start_health_check_server()          — запуск HTTP-сервера для /health check
    PING_URLS                            — список URL для пинга
"""

import asyncio
import logging
import os

from aiohttp import web, ClientSession


# ЖЁСТКО ЗАФИКСИРОВАННЫЕ ССЫЛКИ ДЛЯ ПИНГА (НЕ УДАЛЯТЬ И НЕ СОКРАЩАТЬ)
PING_URLS = [
    "https://lessurvivalbot-5u4p.onrender.com",
    "https://lessurvivalbot.onrender.com",
]


async def keep_alive_pinger(interval_seconds: int = 300):
    """
    КРИТИЧЕСКАЯ ФУНКЦИЯ: Отправляет HTTP GET запросы каждые 5 минут на оба сервиса Render,
    чтобы предотвратить их уход в спящий режим.
    """
    await asyncio.sleep(15)  # Пауза перед первым запуском после старта бота
    async with ClientSession() as session:
        while True:
            for url in PING_URLS:
                try:
                    async with session.get(url, timeout=10) as response:
                        logging.info(f"[Keep-Alive] Пинг {url} -> Статус: {response.status}")
                except Exception as e:
                    logging.warning(f"[Keep-Alive] Ошибка при пинге {url}: {e}")
            await asyncio.sleep(interval_seconds)


async def handle_health_check(request):
    """Простой HTTP-эндпоинт для проверки работоспособности (Render health check)."""
    return web.Response(text="OK")


async def start_health_check_server():
    """Запустить aiohttp HTTP-сервер на PORT (по умолчанию 8080)."""
    app = web.Application()
    app.router.add_get("/", handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Health check сервер запущен на порту {port}")
