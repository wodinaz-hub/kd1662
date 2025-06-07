import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
import logging # Додаємо логування
import pandas as pd # Для ініціалізації pd.DataFrame()

# Налаштування логування (дуже важливо для налагодження!)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(name)s:%(message)s',
                    handlers=[
                        logging.FileHandler("bot.log", encoding='utf-8'),
                        logging.StreamHandler()
                    ])
logging.getLogger('discord').setLevel(logging.WARNING)
logging.getLogger('discord.http').setLevel(logging.WARNING)
logging.getLogger('matplotlib').setLevel(logging.WARNING) # Якщо використовуєте matplotlib, це може зменшити шум

# Імпортуємо інстанс бота з bot.core
from bot.core import bot

# Імпортуємо calculate_stats з data_processing/calculator
# calculator.py вже містить get_player_stats, тому окремий імпорт не потрібен
from data_processing.calculator import calculate_stats

# Імпортуємо setup_commands з bot.commands
from bot.commands import setup_commands

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Перевірка наявності токену
if TOKEN is None:
    logging.critical("DISCORD_TOKEN not found in .env file. Exiting.")
    exit(1)


# Ця функція буде викликана, коли бот буде готовий
@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})') # Для виводу в консоль

    logging.info("Starting initial data loading and calculation...")
    try:
        # !!! КЛЮЧОВА ЗМІНА: Викликаємо calculate_stats БЕЗ АРГУМЕНТІВ !!!
        # Вона сама завантажує всі потрібні файли і зберігає results.xlsx
        bot.result_df = calculate_stats()

        if bot.result_df.empty:
            logging.error("Failed to load or process data. Some commands may not work correctly.")
            print("ERROR: Failed to load or process data. Check logs for details.") # Для консолі
        else:
            logging.info("Data successfully loaded and processed.")
            print("Data loaded and processed successfully.") # Для консолі

    except Exception as e:
        logging.exception(f"Error during initial data loading: {e}")
        print(f"CRITICAL ERROR: Initial data loading failed: {e}. Check bot.log for details.") # Для консолі
        bot.result_df = pd.DataFrame() # Забезпечуємо, що result_df завжди DataFrame, навіть якщо порожній

    # Налаштовуємо команди після завантаження даних
    # Цей виклик має бути тут, щоб команди мали доступ до bot.result_df
    setup_commands(bot)
    logging.info(f'{bot.user.name} is ready!')
    print(f'{bot.user.name} is ready!') # Для консолі


# Функція для запуску бота
def run_bot_instance():
    logging.info("Attempting to run bot...")
    try:
        bot.run(TOKEN)
    except discord.errors.LoginFailure:
        logging.critical("Improper token has been passed. Please check your DISCORD_TOKEN in .env file.")
        print("CRITICAL ERROR: Improper token. Check DISCORD_TOKEN in .env file.")
    except Exception as e:
        logging.exception(f"An unexpected error occurred during bot run: {e}")
        print(f"CRITICAL ERROR: An unexpected error occurred: {e}. Check bot.log for details.")

if __name__ == "__main__":
    run_bot_instance()