import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
import pandas as pd # Потрібен, якщо ви зберігаєте results.xlsx тут

# Імпортуємо логіку з інших модулів
from data_processing.loader import load_and_prepare_data
from data_processing.calculator import calculate_stats
from bot.core import bot # Імпортуємо інстанс бота
from bot.commands import setup_commands # Функція, яка додає команди до бота

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

def run_bot():
    before_file = 'start_kvk.xlsx'
    after_file = 'pass4.xlsx'
    requirements_file = 'required.xlsx'

    try:
        # Завантаження та підготовка даних
        print("Loading and preparing data...")
        before, after, requirements = load_and_prepare_data(before_file, after_file, requirements_file)
        result_df = calculate_stats(before, after, requirements)

        # Зберігаємо result_df в атрибуті об'єкта bot, щоб команди могли до нього звертатися
        bot.result_df = result_df
        print("Data loaded and calculated successfully.")

        # Якщо потрібно зберегти результати в файл results.xlsx після розрахунку:
        # У вашому старому коді calculate_stats сам зберігав.
        # Залиште цю логіку в calculate_stats, якщо вам потрібно, щоб він сам зберігав
        # Або перенесіть сюди, якщо main.py має контролювати збереження.
        # Для зручності, поки що, нехай calculate_stats зберігає.
        # result_df.to_excel('results.xlsx', index=False)
        # print("Results saved to 'results.xlsx'")

        # Додаємо команди до бота
        setup_commands(bot)

        print(f'Starting bot {bot.user}...')
        bot.run(TOKEN)

    except (FileNotFoundError, ValueError) as e:
        print(f"Critical error during data loading or setup: {e}")
        exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        exit(1)


if __name__ == "__main__":
    run_bot()