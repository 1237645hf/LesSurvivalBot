import logging
from aiogram import Bot

async def clear_chat(chat_id: int):
    try:
        history = await Bot.get_chat_history(chat_id, limit=30)
        for msg in history:
            if msg.from_user and msg.from_user.id == (await Bot.get_me()).id:
                if msg.message_id != message.message_id:
                    await Bot.delete_message(chat_id, msg.message_id)
    except Exception as e:
        logging.warning(f"Очистка чата не удалась: {e}")

async def self_ping_task():
    # (перенеси сюда свой код self-ping, если хочешь)
    pass