import os
import logging
import sys
from dotenv import load_dotenv

# ИМПОРТИРУЕМ ТОЛЬКО КЛАСС BotInstance
from bot.commands import BotInstance

print(f"STARTED: PID={os.getpid()}")

# --- НАЧАЛО БЛОКА КОНФИГУРАЦИИ ЛОГИРОВАНИЯ ---
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)
    handler.close()

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
handler.setFormatter(formatter)
handler.setLevel(logging.DEBUG)
root_logger.addHandler(handler)

logging.getLogger('discord').setLevel(logging.INFO)
logging.getLogger('discord.http').setLevel(logging.INFO)
logging.getLogger('data_processing.calculator').setLevel(logging.DEBUG)
logging.getLogger('utils.chart_generator').setLevel(logging.DEBUG)
logging.getLogger('utils.helpers').setLevel(logging.DEBUG)
# --- КОНЕЦ БЛОКА КОНФИГУРАЦИИ ЛОГИРОВАНИЯ ---


logger = logging.getLogger('main')

# Load environment variables from .env file (e.g., DISCORD_BOT_TOKEN)
load_dotenv()

# Get the bot token from environment variables
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

if BOT_TOKEN is None:
    logger.error("Error: DISCORD_BOT_TOKEN not found in environment variables. Please set it in your .env file.")
else:
    try:
        logger.info("Starting Discord bot...")

        # --- ИСПРАВЛЕНИЕ: Создаем ОДИН экземпляр класса BotInstance и запускаем его ---
        bot_instance = BotInstance()
        bot_instance.bot.run(BOT_TOKEN)
        # --- КОНЕЦ ИСПРАВЛЕНИЯ ---

    except Exception as e:
        logger.exception("An error occurred while running the bot:")