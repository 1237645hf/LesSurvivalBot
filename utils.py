from aiogram import types, bot
import random

async def clear_chat(chat_id):
    try:
        history = await bot.get_chat_history(chat_id, limit=30)
        for msg in history:
            if msg.from_user and msg.from_user.id == (await bot.get_me()).id:
                if msg.message_id != message.message_id:  # не удаляем /start
                    await bot.delete_message(chat_id, msg.message_id)
    except Exception as e:
        logging.warning(f"Очистка чата не удалась: {e}")

def get_pogoda():
    return random.choices(["Ясно", "Пасмурно", "Дождь"], weights=[70, 20, 10])[0]