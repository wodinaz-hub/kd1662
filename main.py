import os
import logging
import sys # Import sys for StreamHandler
from dotenv import load_dotenv

# Import bot_instance and run_bot directly from bot.commands
from bot.commands import bot_instance, run_bot

# --- НАЧАЛО БЛОКА КОНФИГУРАЦИИ ЛОГИРОВАНИЯ (ОБНОВЛЕНО) ---
# Создаем корневой логгер
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG) # Устанавливаем уровень DEBUG для корневого логгера

# Очищаем существующие обработчики, чтобы избежать дублирования
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)
    handler.close()

# Создаем хэндлер для вывода в консоль
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
handler.setFormatter(formatter)
handler.setLevel(logging.DEBUG) # Устанавливаем уровень DEBUG для хэндлера
root_logger.addHandler(handler)

# Настройка логирования для Discord.py
logging.getLogger('discord').setLevel(logging.INFO) # Discord.py можно оставить на INFO
logging.getLogger('discord.http').setLevel(logging.INFO) # Http запросы Discord.py тоже на INFO

# Настройка логирования для ваших модулей
# Теперь логгер в calculator.py использует __name__, т.е. 'data_processing.calculator'
logging.getLogger('data_processing.calculator').setLevel(logging.DEBUG)
# Теперь логгер в chart_generator.py использует __name__, т.е. 'utils.chart_generator'
logging.getLogger('utils.chart_generator').setLevel(logging.DEBUG)
# Логгер в helpers.py также использует __name__, т.е. 'utils.helpers'
logging.getLogger('utils.helpers').setLevel(logging.DEBUG)
# --- КОНЕЦ БЛОКА КОНФИГУРАЦИИ ЛОГИРОВАНИЯ ---


logger = logging.getLogger('main') # Этот логгер теперь будет использовать настроенный выше root_logger

# Load environment variables from .env file (e.g., DISCORD_BOT_TOKEN)
load_dotenv()

# Get the bot token from environment variables
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

if BOT_TOKEN is None:
    logger.error("Error: DISCORD_BOT_TOKEN not found in environment variables. Please set it in your .env file.")
else:
    try:
        logger.info("Starting Discord bot...")
        run_bot(BOT_TOKEN)
    except Exception as e:
        logger.exception("An error occurred while running the bot:")

