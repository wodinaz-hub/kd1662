import discord
from discord.ext import commands
import pandas as pd
import os
import numpy as np
import logging

# Імпорти інших ваших модулів. Переконайтеся, що шляхи коректні.
# Якщо get_player_stats знаходиться в data_processing/calculator.py
from data_processing.calculator import get_player_stats
# Якщо create_dual_semi_circular_progress знаходиться в utils/chart_generator.py
from utils.chart_generator import create_dual_semi_circular_progress
# Якщо create_progress_bar знаходиться в utils/helpers.py
from utils.helpers import create_progress_bar
# Якщо PaginationView знаходиться в bot/view.py
from bot.view import PaginationView
from typing import List, Tuple  # Типізація, що може бути корисною для читабельності

# Константа (можливо, краще тримати її в config.py, якщо вона глобальна)
ITEMS_PER_PAGE = 5


def format_number_custom(num_value):
    """
    Форматує число з розділювачами тисяч (крапка) і комою для десяткових.
    Обробляє стандартні int/float та numpy.int64/numpy.float64.
    """
    if not isinstance(num_value, (int, float, np.int64, np.float64)):
        logging.debug(f"format_number_custom: Received non-numeric value: {num_value} ({type(num_value)})")
        return str(num_value)  # Повертаємо як є, якщо не число

    # Для numpy типів, перетворюємо їх на стандартні Python int/float
    if isinstance(num_value, np.int64):
        num_value = int(num_value)
    elif isinstance(num_value, np.float64):
        num_value = float(num_value)

    # Визначаємо, чи число є цілим за значенням
    if float(num_value).is_integer():
        num_str = str(int(num_value))
    else:
        num_str = f"{num_value:.2f}"  # Форматуємо до двох знаків після коми

    parts = num_str.split('.')
    integer_part = parts[0]
    decimal_part = parts[1] if len(parts) > 1 else ""

    formatted_integer_part = ""
    for i, digit in enumerate(reversed(integer_part)):
        formatted_integer_part += digit
        if (i + 1) % 3 == 0 and (i + 1) != len(integer_part):
            formatted_integer_part += "."  # Використовуємо крапку як розділювач тисяч
    formatted_integer_part = formatted_integer_part[::-1]

    result = ""
    if decimal_part:
        # Якщо є десяткові, використовуємо кому як десятковий розділювач
        result = f"{formatted_integer_part},{decimal_part}"
    else:
        result = formatted_integer_part

    return result


def setup_commands(bot_instance: commands.Bot):
    """
    Ця функція реєструє всі команди на переданому інстансі бота.
    """

    # Функція get_result_df визначена тут, щоб мати доступ до bot_instance.result_df
    def get_result_df() -> pd.DataFrame:
        """
        Намагається отримати DataFrame з bot_instance,
        або прочитати його з results.xlsx, якщо не знайдено.
        """
        if hasattr(bot_instance,
                   'result_df') and bot_instance.result_df is not None and not bot_instance.result_df.empty:
            logging.debug("get_result_df: Повертаю bot_instance.result_df.")
            return bot_instance.result_df
        else:
            logging.warning(
                "get_result_df: result_df не знайдено на bot_instance або він порожній. Спроба читання з results.xlsx.")
            try:
                # Перевірте, чи коректний шлях до results.xlsx тут.
                # Якщо results.xlsx знаходиться в корені проєкту (kd1662), то просто 'results.xlsx'.
                # Якщо він, наприклад, у 'data' папці, то 'data/results.xlsx'.
                df_from_file = pd.read_excel('results.xlsx')
                if df_from_file.empty:
                    logging.warning("get_result_df: results.xlsx завантажено, але файл порожній.")
                else:
                    logging.info("get_result_df: Дані успішно завантажені з results.xlsx.")
                return df_from_file
            except FileNotFoundError:
                logging.error("get_result_df: results.xlsx не знайдено. Деякі команди можуть не функціонувати.")
                return pd.DataFrame()
            except Exception as e:
                logging.exception(f"get_result_df: Непередбачена помилка при читанні results.xlsx: {e}")
                return pd.DataFrame()

    logging.debug("setup_commands: Початок реєстрації команд.")

    # --- Команда !bot_help ---
    @bot_instance.command(name="bot_help")
    async def help_command(ctx):
        logging.debug("help_command: Викликано команду !bot_help.")
        embed = discord.Embed(title="ℹ️ Bot Help", color=discord.Color.blurple())
        embed.add_field(
            name="!stats <Governor ID>",
            value=(
                "Displays detailed statistics for a player by their ID.\n"
                "Shows current power, power change, kill count (total, T4, T5), death count, DKP, DKP rank, and a progress chart for kill and death requirements."
            ),
            inline=False,
        )
        embed.add_field(
            name="!kd_stats",
            value=(
                "Shows overall kingdom statistics.\n"
                "Displays the total kills gained and total deaths in the kingdom."
            ),
            inline=False,
        )
        embed.add_field(
            name="!req",
            value=(
                "Displays a list of players who have not met the kill or death requirements (5 per page)."
            ),
            inline=False,
        )
        embed.add_field(
            name="!top",
            value=(
                "Displays a list of the top players by DKP (5 per page).\n"
                "For each player, shows their rank, name, DKP, total deaths, total kill points, and T4 & T5 kills."
            ),
            inline=False,
        )
        embed.set_footer(text="For bot-related questions, contact Wodinaz.")
        await ctx.send(embed=embed)
        logging.debug("help_command: Довідкова інформація відправлена.")

    # --- Команда !req (оновлена логіка відображення) ---
    @bot_instance.command(name="req")
    async def requirements(ctx):
        logging.debug(f"DEBUG: Команда !req була викликана користувачем {ctx.author} в каналі {ctx.channel.name}.")
        print(f"DEBUG: Команда !req була викликана. (Консоль: {ctx.author})")

        try:
            logging.debug("DEBUG: Спроба отримати DataFrame для !req.")
            df = get_result_df()
            logging.debug(f"DEBUG: DataFrame отримано. Порожній: {df.empty}")

            if df.empty:
                logging.warning("WARNING: DataFrame порожній для !req. Надсилання повідомлення про помилку.")
                await ctx.send("Error: Data not loaded. Please ensure data files are present and bot restarted.")
                return

            required_cols = ['Required Kills', 'Required Deaths', 'Kill Points_before', 'Kill Points_after',
                             'Deads_before', 'Deads_after', 'Governor Name', 'Governor ID']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                error_msg = f"ERROR: Відсутні необхідні стовпці в даних для !req: {', '.join(missing_cols)}"
                logging.error(error_msg)
                await ctx.send(f"An error occurred: {error_msg}. Please check data integrity.")
                return

            # Перетворення колонок на числові, з обробкою NaN.
            # Це ВАЖЛИВО, щоб уникнути помилок типу 'float' object has no attribute 'fillna'
            for col in ['Required Kills', 'Required Deaths', 'Kill Points_before', 'Kill Points_after',
                        'Deads_before', 'Deads_after']:
                df.loc[:, col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                if df.loc[:, col].dtype == 'float64' and (df.loc[:, col] == df.loc[:, col].astype(int)).all():
                    df.loc[:, col] = df.loc[:, col].astype(int)

            logging.debug("DEBUG: Початок обробки даних гравців для вимог.")
            not_completed_players_data = []
            for index, row in df.iterrows():
                kills_gained = row['Kill Points_after'] - row['Kill Points_before']
                deaths_gained = row['Deads_after'] - row['Deads_before']

                kills_progress_percent = (kills_gained / row['Required Kills'] * 100) if row[
                                                                                             'Required Kills'] != 0 else (
                    100 if kills_gained >= 0 else 0)
                deaths_progress_percent = (deaths_gained / row['Required Deaths'] * 100) if row[
                                                                                                'Required Deaths'] != 0 else (
                    100 if deaths_gained >= 0 else 0)

                kills_needed = max(0, row['Required Kills'] - kills_gained)
                deaths_needed = max(0, row['Required Deaths'] - deaths_gained)

                # Перевіряємо, чи гравець не виконав хоча б одну вимогу
                if kills_needed > 0 or deaths_needed > 0:
                    not_completed_players_data.append({
                        'Governor Name': row['Governor Name'],
                        'Governor ID': row['Governor ID'],
                        'Kills Needed': kills_needed,
                        'Deaths Needed': deaths_needed,
                        'Kills Progress': kills_progress_percent,
                        'Deaths Progress': deaths_progress_percent,
                        'Kills Done': (kills_needed == 0),  # Додано прапорець: чи виконані вбивства
                        'Deaths Done': (deaths_needed == 0)  # Додано прапорець: чи виконані смерті
                    })

            if not not_completed_players_data:
                embed = discord.Embed(title="🎉 All players have met the requirements!", color=discord.Color.green())
                await ctx.send(embed=embed)
                logging.info("INFO: Усі гравці виконали вимоги.")
                return

            all_req_embeds = []
            for i in range(0, len(not_completed_players_data), ITEMS_PER_PAGE):
                current_page_players = not_completed_players_data[i:i + ITEMS_PER_PAGE]

                embed = discord.Embed(
                    title="⚠️ Players who have not met the requirements",
                    color=discord.Color.orange()
                )

                for player_data in current_page_players:
                    field_value_parts = []

                    # Повідомлення про статус на початку
                    if player_data['Kills Done'] and not player_data['Deaths Done']:
                        field_value_parts.append("Status: Kills requirement met, but deaths are still needed.")
                    elif not player_data['Kills Done'] and player_data['Deaths Done']:
                        field_value_parts.append("Status: Deaths requirement met, but kills are still needed.")
                    elif not player_data['Kills Done'] and not player_data['Deaths Done']:
                        field_value_parts.append("Status: Both requirements are pending.")
                    # Якщо обидва виконані, гравець не потрапляє в цей список взагалі, тому цей випадок не потрібен.

                    if player_data['Kills Done']:
                        field_value_parts.append("✅ Kills: **Requirements met!**")
                    else:
                        field_value_parts.append(f"⚔️ Kills: {create_progress_bar(player_data['Kills Progress'])}")
                        field_value_parts.append(f"({format_number_custom(player_data['Kills Needed'])} remaining)")

                    if player_data['Deaths Done']:
                        field_value_parts.append("✅ Deaths: **Requirements met!**")
                    else:
                        field_value_parts.append(f"💀 Deaths: {create_progress_bar(player_data['Deaths Progress'])}")
                        field_value_parts.append(f"({format_number_custom(player_data['Deaths Needed'])} remaining)")

                    field_value = "\n".join(field_value_parts)  # Об'єднуємо всі частини

                    embed.add_field(
                        name=f"{player_data['Governor Name']} (ID: {player_data['Governor ID']})",
                        value=field_value,
                        inline=False
                    )

                total_pages = (len(not_completed_players_data) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
                embed.set_footer(text=f"Page {len(all_req_embeds) + 1}/{total_pages}")
                all_req_embeds.append(embed)

            view = PaginationView(all_req_embeds)
            message = await ctx.send(embed=all_req_embeds[0], view=view)
            view.message = message
            logging.info(f"INFO: Відправлено {len(all_req_embeds)} сторінок вимог гравців.")

        except Exception as e:
            logging.exception("ERROR: Виникла непередбачена помилка в команді !req.")
            await ctx.send(f"An unexpected error occurred while processing the !req command: {str(e)}")

    # --- Команда !kd_stats ---
    @bot_instance.command()
    async def kd_stats(ctx):
        logging.debug("kd_stats: Викликано команду !kd_stats.")
        try:
            # Завантажуємо result_df, який вже має бути оброблений calculate_stats
            df = bot_instance.result_df  # Беремо df з інстансу бота

            if df.empty:
                await ctx.send(
                    "Error: Data not loaded or empty. Please ensure data files are present and bot restarted.")
                return

            # Змінений перелік необхідних стовпців для kd_stats
            # Power_at_KVK_start замість Power_before для зміни потужності за КВК
            # Power_after для поточної потужності
            required_cols_kd = ['Kills Change', 'Deads Change', 'Power_after', 'Power_at_KVK_start']
            missing_cols_kd = [col for col in required_cols_kd if col not in df.columns]
            if missing_cols_kd:
                error_msg = f"ERROR: Відсутні необхідні стовпці для !kd_stats: {', '.join(missing_cols_kd)}. Будь ласка, перевірте цілісність даних."
                logging.error(error_msg)
                await ctx.send(f"An error occurred: {error_msg}")
                return

            # Важливо: ці стовпці вже мають бути числовими завдяки calculate_stats
            # Тому ці рядки можуть бути не потрібні, або їх можна спростити до перевірки типу
            # Наприклад, pd.to_numeric(df[col], errors='coerce').fillna(0) вже було зроблено
            # у calculate_stats().
            # Залишаємо їх як запобіжник, але вони не повинні змінювати дані, якщо calculate_stats() працює коректно.
            for col in ['Kills Change', 'Deads Change', 'Power_after', 'Power_at_KVK_start']:
                if col in df.columns:  # Перевірка на всяк випадок
                    df.loc[:, col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            total_kills_gained = df['Kills Change'].sum()
            total_deaths_gained = df['Deads Change'].sum()

            # Обчислення зміни потужності за КВК: Power_after (поточна) - Power_at_KVK_start (початкова)
            total_power_change = (df['Power_after'] - df['Power_at_KVK_start']).sum()
            current_total_power = df[
                'Power_after'].sum()  # Поточна потужність - сума потужності гравців після битви

            embed = discord.Embed(title="📊 Kingdom Overview", color=discord.Color.green())
            embed.add_field(
                name="⚔️ Total Kills Gained:",
                value=f"{format_number_custom(total_kills_gained)}",
                inline=False
            )
            embed.add_field(
                name="💀 Total Deaths Gained:",
                value=f"{format_number_custom(total_deaths_gained)}",
                inline=False
            )
            embed.add_field(
                name="💪 Change in Total Power:",
                value=f"{format_number_custom(total_power_change)}",
                inline=False
            )
            embed.add_field(
                name="⚡ Current Total Power:",
                value=f"{format_number_custom(current_total_power)}",
                inline=False
            )
            await ctx.send(embed=embed)
            logging.info("kd_stats: Інформація про королівство відправлена.")

        except Exception as e:
            logging.exception("ERROR: Виникла непередбачена помилка в команді !kd_stats.")
            await ctx.send(f"An error occurred: {str(e)}")

    # --- Команда !top (повернута до попередньої версії) ---
    @bot_instance.command()
    async def top(ctx):
        logging.debug("top: Викликано команду !top.")
        try:
            df = get_result_df()
            if df.empty:
                await ctx.send("Error: Data not loaded. Please ensure data files are present and bot restarted.")
                return

            # Перевірка наявності стовпців для !top
            required_cols_top = ['DKP', 'Deads Change', 'Kills Change', 'Tier 4 Kills_after', 'Tier 4 Kills_before',
                                 'Tier 5 Kills_after', 'Tier 5 Kills_before', 'Governor Name']
            missing_cols_top = [col for col in required_cols_top if col not in df.columns]
            if missing_cols_top:
                error_msg = f"ERROR: Відсутні необхідні стовпці для !top: {', '.join(missing_cols_top)}"
                logging.error(error_msg)
                await ctx.send(f"An error occurred: {error_msg}. Please check data integrity.")
                return

            # Конвертація DKP до числового типу (як було раніше)
            df.loc[:, 'DKP'] = pd.to_numeric(df['DKP'], errors='coerce').fillna(0)

            result_sorted = df.sort_values(by='DKP', ascending=False)

            if result_sorted.empty:
                await ctx.send("No players found to display in top list.")
                logging.info("top: Не знайдено гравців для відображення у списку TOP.")
                return

            all_top_embeds = []
            for i in range(0, len(result_sorted), ITEMS_PER_PAGE):
                current_page_players = result_sorted.iloc[i:i + ITEMS_PER_PAGE]

                embed = discord.Embed(
                    title="🏆 Top Players (KVK Gains)",
                    color=discord.Color.gold()
                )

                start_rank = i

                for local_index, row in current_page_players.iterrows():
                    current_rank = start_rank + current_page_players.index.get_loc(row.name) + 1

                    field_name = f"#{current_rank}. {row['Governor Name']}"

                    # Ця частина залишена як було, щоб уникнути помилки, що виникла
                    # Якщо тут виникне помилка, ми знаємо, що потрібно буде перевірити
                    # попередню обробку цих колонок або перевірити, чи вони завжди є числами.
                    # За замовчуванням, вважаємо, що вони вже були оброблені або не містять NaN.
                    t4_kills_gained = row['Tier 4 Kills_after'] - row['Tier 4 Kills_before']
                    t5_kills_gained = row['Tier 5 Kills_after'] - row['Tier 5 Kills_before']

                    field_value = (
                        f"🏅 DKP: {format_number_custom(row['DKP'])}\n"
                        f"💀 Deaths Gained: {format_number_custom(row['Deads Change'])}\n"
                        f"⚔️ Kill Points Gained: {format_number_custom(row['Kills Change'])}\n"
                        f"T4 Kills Gained: {format_number_custom(t4_kills_gained)}\n"
                        f"T5 Kills Gained: {format_number_custom(t5_kills_gained)}"
                    )
                    embed.add_field(
                        name=field_name,
                        value=field_value,
                        inline=False
                    )

                total_pages = (len(result_sorted) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
                embed.set_footer(text=f"Page {len(all_top_embeds) + 1}/{total_pages}")
                all_top_embeds.append(embed)

            view = PaginationView(all_top_embeds)
            message = await ctx.send(embed=all_top_embeds[0], view=view)
            view.message = message
            logging.info(f"top: Відправлено {len(all_top_embeds)} сторінок топ-гравців.")
        except Exception as e:
            logging.exception("ERROR: Виникла непередбачена помилка в команді !top.")
            await ctx.send(f"An error occurred while processing the !top command: {str(e)}")

    # --- Команда !stats (повернута до попередньої версії) ---
    @bot_instance.command()
    async def stats(ctx, player_id: str):  # Вказуємо тип для player_id
        logging.debug(f"stats: Викликано команду !stats з ID: {player_id}.")
        try:
            df = get_result_df()
            if df.empty:
                await ctx.send("Error: Data not loaded. Please ensure data files are present and bot restarted.")
                return

            # Перетворюємо Governor ID в DataFrame на рядок для коректного порівняння
            df.loc[:, 'Governor ID'] = df['Governor ID'].astype(str)
            # Перевіряємо, чи player_id є в DF
            if player_id not in df['Governor ID'].values:
                await ctx.send(f"Player with ID {player_id} not found.")
                logging.info(f"stats: Гравець з ID {player_id} не знайдений.")
                return

            player_stats = get_player_stats(df, player_id)  # Передача df в get_player_stats

            if player_stats:
                embed = discord.Embed(title=f"📊 Player Statistics: {player_stats['governor_name']} (ID: {player_id})",
                                      color=discord.Color.blue())
                embed.add_field(name="🔹 Matchmaking Power:",
                                value=f"{format_number_custom(player_stats['matchmaking_power'])}", inline=False)
                embed.add_field(name="🔹 Power Change:", value=f"{format_number_custom(player_stats['power_change'])}",
                                inline=False)

                embed.add_field(name="⚔️ Kills:", value=(
                    f"**KP: {format_number_custom(player_stats['kills_change'])}**\n"
                    f"Required: {format_number_custom(player_stats['required_kills'])}\n"
                    f"Total: {format_number_custom(player_stats['tier4_kills_change'] + player_stats['tier5_kills_change'])}\n"
                    f"T4: {format_number_custom(player_stats['tier4_kills_change'])}\n"
                    f"T5: {format_number_custom(player_stats['tier5_kills_change'])}\n"
                    f"Progress: {player_stats['kills_completion']:.2f}%"
                ), inline=True)
                embed.add_field(name="💀 Deaths:", value=(
                    f"Required: {format_number_custom(player_stats['required_deaths'])}\n"
                    f"Total: {format_number_custom(player_stats['deads_change'])}\n"
                    f"Progress: {player_stats['deads_completion']:.2f}%"
                ), inline=True)

                embed.add_field(name="🏅 DKP:", value=f"{format_number_custom(player_stats['dkp'])}", inline=False)
                embed.add_field(name="🏆 DKP Rank:", value=f"#{player_stats['rank']}", inline=False)

                chart_path = create_dual_semi_circular_progress(
                    player_stats['kills_completion'],
                    player_stats['deads_completion']
                )
                if chart_path and os.path.exists(chart_path):
                    with open(chart_path, 'rb') as f:
                        picture = discord.File(f)
                        await ctx.send(embed=embed, file=picture)
                    os.remove(chart_path)
                    logging.debug(f"stats: Діаграма відправлена та тимчасовий файл {chart_path} видалено.")
                else:
                    await ctx.send(embed=embed)
                    logging.warning(
                        f"stats: Файл діаграми не створено або не знайдено за шляхом {chart_path}. Відправлено без файлу.")

            else:
                await ctx.send(
                    f"Player with ID {player_id} not found.")  # Повторно, на випадок, якщо get_player_stats повернув None
                logging.info(f"stats: Гравець з ID {player_id} не знайдений (після get_player_stats).")
        except Exception as e:
            logging.exception("ERROR: Виникла непередбачена помилка в команді !stats.")
            await ctx.send(f"An error occurred while processing the !stats command: {str(e)}")

    logging.debug("setup_commands: Усі команди в commands.py зареєстровані.")