import discord
from discord.ext import commands
import pandas as pd
import numpy as np
import logging
import os
from typing import List, Tuple

# Imports of your other modules. Ensure paths are correct.
# calculator.py now contains calculate_stats, calculate_period_stats, get_player_stats
from data_processing.calculator import calculate_stats, calculate_period_stats, get_player_stats
from utils.chart_generator import create_dual_semi_circular_progress
from utils.helpers import create_progress_bar, format_number_custom, create_embed
from bot.view import PaginationView

# Configure logging
logger = logging.getLogger('discord')

# Constant for pagination
ITEMS_PER_PAGE = 5

# Dictionary to store DataFrames with processed period statistics
# This will prevent re-reading and re-processing files on each request
period_dataframes = {}

# Dictionary for mapping period names to file paths
# !!! IMPORTANT: Ensure these paths and file names match your actual structure !!!
PERIOD_CONFIG = {
    'zone5': {
        'start': 'zone 5/start_zone5.xlsx',
        'end': 'zone 5/end_zone5.xlsx'
    },
    'altars': {
        'start': 'altars/start_altars.xlsx',
        'end': 'altars/end_altars.xlsx'
    },
    'pass7': {
        'start': 'pass 7/start_pass7.xlsx',
        'end': 'pass 7/end_pass7.xlsx'
    },
    'kingsland': {
        'start': 'kingsland/start_kingsland.xlsx',
        'end': 'kingsland/end_kingsland.xlsx'
    }
}


class BotInstance:
    def __init__(self):
        self.bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
        # Remove the default help command to implement our own or allow specific overrides
        self.bot.remove_command('help')
        self.result_df = pd.DataFrame()  # For overall KVK statistics
        self.period_dataframes = {}  # For caching period data
        self._setup_events()
        self._setup_commands()

    def _setup_events(self):
        @self.bot.event
        async def on_ready():
            logger.info(f'Logged in as {self.bot.user.name} ({self.bot.user.id})')
            print(f'Logged in as {self.bot.user.name} ({self.bot.user.id})')
            await self.load_initial_data()

        @self.bot.event
        async def on_command_error(ctx, error):
            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send(f"Error: Missing arguments. Correct usage: `{ctx.command.usage}`")
            elif isinstance(error, commands.BadArgument):
                await ctx.send(
                    f"Error: Invalid argument type. Please check your input. Correct usage: `{ctx.command.usage}`")
            elif isinstance(error, commands.CommandNotFound):
                pass  # Ignore if command not found
            else:
                logger.error(f"Error in command {ctx.command}: {error}", exc_info=True)
                await ctx.send(f"An unexpected error occurred while executing the command: {error}")

    async def load_initial_data(self):
        # Load main KVK data on startup
        self.result_df = calculate_stats()
        if self.result_df.empty:
            logger.warning("Initial KVK data (results.xlsx) is empty or failed to load.")
        else:
            logger.info(f"Loaded initial KVK data with {len(self.result_df)} players.")

    async def get_period_df(self, period_name: str) -> pd.DataFrame:
        period_name = period_name.lower()

        # Check if the period name is valid based on PERIOD_CONFIG
        if period_name not in PERIOD_CONFIG:
            # Removed the raise ValueError, now handling directly
            await self.bot.get_channel(self.bot.last_command_channel_id).send(
                f"Unknown period '{period_name}'. Available periods: {', '.join(PERIOD_CONFIG.keys())}")
            return None

        # Check if data for this period is already cached
        if period_name not in self.period_dataframes or self.period_dataframes[period_name].empty:
            period_files = PERIOD_CONFIG[period_name]
            start_file_path = period_files['start']
            end_file_path = period_files['end']

            # Construct full paths relative to the script or data directory
            start_file_full_path = os.path.join(os.getcwd(), start_file_path)
            end_file_full_path = os.path.join(os.getcwd(), end_file_path)

            if not os.path.exists(start_file_full_path) or not os.path.exists(end_file_full_path):
                # Specific message if files do not exist (battle has not started or files missing)
                # Removed file paths from the user-facing message
                await self.bot.get_channel(self.bot.last_command_channel_id).send(
                    f"⚔️ The battle for period `{period_name.upper()}` has not started yet."
                )
                logger.error(
                    f"Data files for period '{period_name}' not found: start_exists={os.path.exists(start_file_full_path)}, end_exists={os.path.exists(end_file_full_path)}."
                )
                return None

            logger.info(f"Loading and processing data for period: {period_name}")
            period_df = calculate_period_stats(start_file_full_path, end_file_full_path)

            if period_df.empty:
                # Specific message if data is empty after processing (calculation in progress or no meaningful data)
                await self.bot.get_channel(self.bot.last_command_channel_id).send(
                    f"⏳ Results for period `{period_name.upper()}` are currently being calculated, or data is not yet available. Please try again later."
                )
                logger.warning(f"Processed data for period '{period_name}' is empty.")
                return None

            self.period_dataframes[period_name] = period_df  # Store for future use
            return period_df
        else:
            logger.info(f"Data for period '{period_name}' loaded from cache.")
            return self.period_dataframes[period_name]

    def _setup_commands(self):
        # Store ctx.channel.id to send messages from get_period_df
        @self.bot.before_invoke
        async def before_any_command(ctx):
            self.bot.last_command_channel_id = ctx.channel.id

        @self.bot.command(name='bot_help', help='Displays a list of all available commands and their usage.')
        async def bot_help(ctx):
            embed = create_embed(
                title="🤖 Bot Commands Help",
                description="Here are all the commands you can use:",
                color=discord.Color.blue()
            )
            # Iterate through all commands registered with the bot
            for command in self.bot.commands:
                # Exclude the help command itself if you want a custom appearance
                # and any hidden commands (e.g., ones starting with an underscore)
                if command.name != 'bot_help' and not command.hidden:
                    # command.help is the docstring or help parameter of the command
                    # command.usage would be useful if you explicitly set it, otherwise it's None
                    field_value = command.help or "No description provided."
                    if command.usage:
                        field_value += f"\nUsage: `{self.bot.command_prefix}{command.name} {command.usage}`"
                    else:
                        field_value += f"\nUsage: `{self.bot.command_prefix}{command.name} <arguments>` (if any)"

                    embed.add_field(name=f"!{command.name}", value=field_value, inline=False)

            await ctx.send(embed=embed)

        @self.bot.command(name='stats', help='Displays player statistics. Usage: !stats <Governor_ID>')
        async def stats(ctx, player_id: str):
            if self.result_df.empty:
                await ctx.send("Data not yet loaded. Please wait or ensure 'results.xlsx' exists.")
                return

            player_stats = get_player_stats(self.result_df, player_id)

            if player_stats:
                embed = create_embed(
                    title=f"📊 Player Statistics: {player_stats['governor_name']} (ID: {player_stats['governor_id']})",
                    description="",
                    color=0x00ff00
                )

                embed.add_field(name="♦️ Current Power:", value=format_number_custom(player_stats['matchmaking_power']),
                                inline=False)
                embed.add_field(name="♦️ Power Change:", value=format_number_custom(player_stats['power_change']),
                                inline=False)

                kills_value = (
                    f"KP: {format_number_custom(player_stats['kills_change'])}\n"
                    f"T4+T5 Gained: {format_number_custom(player_stats['total_t4_t5_kills_change'])}\n"
                    f"Required: {format_number_custom(player_stats['required_kills'])}\n"
                    f"Total: {format_number_custom(player_stats['total_kills'])}\n"
                    f"T4: {format_number_custom(player_stats['tier4_kills_change'])}\n"
                    f"T5: {format_number_custom(player_stats['tier5_kills_change'])}\n"
                    f"Progress: {player_stats['kills_completion']:.2f}%"
                )
                embed.add_field(name="⚔️ Kills:", value=kills_value, inline=True)

                deaths_value = (
                    f"Gained: {format_number_custom(player_stats['deads_change'])}\n"
                    f"Required: {format_number_custom(player_stats['required_deaths'])}\n"
                    f"Total: {format_number_custom(player_stats['total_deaths'])}\n"
                    f"Progress: {player_stats['deads_completion']:.2f}%"
                )
                embed.add_field(name="💀 Deaths:", value=deaths_value, inline=True)

                embed.add_field(name="🏅 DKP:", value=format_number_custom(player_stats['dkp']), inline=False)
                embed.add_field(name="🏆 DKP Rank:", value=f"#{player_stats['rank']}", inline=False)

                try:
                    logger.debug(
                        f"Chart data for {player_id}: kills_comp={player_stats['kills_completion']:.2f}, deaths_comp={player_stats['deads_completion']:.2f}, req_kills={player_stats['required_kills']}, current_kills_t4t5={player_stats['total_t4_t5_kills_change']}, req_deaths={player_stats['required_deaths']}, deads_change={player_stats['deads_change']}")

                    # Call create_dual_semi_circular_progress with all necessary arguments
                    chart_path = create_dual_semi_circular_progress(
                        player_stats['kills_completion'],
                        player_stats['deads_completion'],
                        player_stats['governor_name'],
                        player_stats['required_kills'],
                        player_stats['total_t4_t5_kills_change'],  # Using total_t4_t5_kills_change as requested
                        player_stats['required_deaths'],
                        player_stats['deads_change']
                    )

                    if chart_path:
                        logger.debug(f"Chart file path returned: {chart_path}")
                        file = discord.File(chart_path, filename="progress_chart.png")
                        embed.set_image(url=f"attachment://progress_chart.png")
                        await ctx.send(file=file, embed=embed)
                        os.remove(chart_path)
                        logger.debug(f"Chart file {chart_path} sent and removed.")
                    else:
                        logger.error(
                            f"create_dual_semi_circular_progress returned None for player {player_id}. Chart not created.")
                        await ctx.send(embed=embed)
                except Exception as e:
                    logger.error(f"Error creating or sending chart for {player_id}: {e}", exc_info=True)
                    await ctx.send(embed=embed)

            else:
                await ctx.send(f"Player with ID **{player_id}** not found.")

        @self.bot.command(name='kd_stats', help='Displays overall kingdom K/D statistics.')
        async def kd_stats(ctx):
            logging.debug("kd_stats: !kd_stats command called.")
            try:
                df = self.result_df

                if df.empty:
                    await ctx.send(
                        "Error: Data not loaded or empty. Please ensure data files are present and bot restarted.")
                    return

                required_cols_kd = ['Kills Change', 'Deads Change', 'Power_after', 'Power_at_KVK_start',
                                    'Tier 4 Kills Change', 'Tier 5 Kills Change', 'DKP']
                missing_cols_kd = [col for col in required_cols_kd if col not in df.columns]
                if missing_cols_kd:
                    error_msg = f"ERROR: Missing required columns for !kd_stats: {', '.join(missing_cols_kd)}. Please check data integrity."
                    logging.error(error_msg)
                    await ctx.send(f"An error occurred: {error_msg}")
                    return

                for col in ['Kills Change', 'Deads Change', 'Power_after', 'Power_at_KVK_start', 'Tier 4 Kills Change',
                            'Tier 5 Kills Change', 'DKP']:
                    if col in df.columns:
                        df.loc[:, col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

                total_kills_gained = df['Kills Change'].sum()
                total_deaths_gained = df['Deads Change'].sum()
                total_t4_kills_gained = df['Tier 4 Kills Change'].sum()
                total_t5_kills_gained = df['Tier 5 Kills Change'].sum()
                total_dkp = df['DKP'].sum()
                total_power_change = (df['Power_after'] - df['Power_at_KVK_start']).sum()
                current_total_power = df['Power_after'].sum()

                embed = create_embed(
                    title="📊 Kingdom Overview",
                    description="",
                    color=discord.Color.blue()
                )
                embed.add_field(name="⚔️ Total Kills Gained:", value=format_number_custom(total_kills_gained),
                                inline=False)
                embed.add_field(name="💀 Total Deaths Gained:", value=format_number_custom(total_deaths_gained),
                                inline=False)
                embed.add_field(name="💪 Change in Total Power:", value=format_number_custom(total_power_change),
                                inline=False)
                embed.add_field(name="⚡ Current Total Power:", value=format_number_custom(current_total_power),
                                inline=False)

                await ctx.send(embed=embed)
                logging.info("kd_stats: Kingdom overview information sent.")

            except Exception as e:
                logging.exception("ERROR: An unexpected error occurred in !kd_stats command.")
                await ctx.send(f"An error occurred: {str(e)}")

        @self.bot.command(name='requirements', aliases=['req'],
                          help='Displays players who have not met their kill or death requirements. Usage: !requirements [limit=20]')
        async def requirements(ctx, limit: int = 20):
            logging.debug(f"DEBUG: !req command called by {ctx.author} in channel {ctx.channel.name}.")
            print(f"DEBUG: !req command called. (Console: {ctx.author})")

            try:
                logging.debug("DEBUG: Attempting to get DataFrame for !req.")
                df = self.result_df
                logging.debug(f"DEBUG: DataFrame obtained. Is empty: {df.empty}")

                if df.empty:
                    logging.warning("WARNING: DataFrame is empty for !req. Sending error message.")
                    await ctx.send("Error: Data not loaded. Please wait or ensure 'results.xlsx' exists.")
                    return

                required_cols = ['Required Kills', 'Required Deaths', 'Kill Points_before', 'Kill Points_after',
                                 'Deads_before', 'Deads_after', 'Governor Name', 'Governor ID']
                missing_cols = [col for col in required_cols if col not in df.columns]
                if missing_cols:
                    error_msg = f"ERROR: Missing required columns in data for !req: {', '.join(missing_cols)}. Please check data integrity."
                    logging.error(error_msg)
                    await ctx.send(f"An error occurred: {error_msg}")
                    return

                for col in ['Required Kills', 'Required Deaths', 'Kill Points_before', 'Kill Points_after',
                            'Deads_before', 'Deads_after']:
                    df.loc[:, col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                    if df.loc[:, col].dtype == 'float64' and (df.loc[:, col] == df.loc[:, col].astype(int)).all():
                        df.loc[:, col] = df[col].astype(int)

                logging.debug("DEBUG: Starting processing of player data for requirements.")
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

                    if kills_needed > 0 or deaths_needed > 0:
                        not_completed_players_data.append({
                            'Governor Name': row['Governor Name'],
                            'Governor ID': row['Governor ID'],
                            'Kills Needed': kills_needed,
                            'Deaths Needed': deaths_needed,
                            'Kills Progress': kills_progress_percent,
                            'Deaths Progress': deaths_progress_percent,
                            'Kills Done': (kills_needed == 0),
                            'Deaths Done': (deaths_needed == 0)
                        })

                if not not_completed_players_data:
                    embed = discord.Embed(title="🎉 All players have met the requirements!", color=discord.Color.green())
                    await ctx.send(embed=embed)
                    logging.info("INFO: All players have met the requirements.")
                    return

                all_req_embeds = []
                for i in range(0, len(not_completed_players_data), ITEMS_PER_PAGE):
                    current_page_players = not_completed_players_data[i:i + ITEMS_PER_PAGE]

                    embed = create_embed(
                        title="⚠️ Players Not Meeting Requirements",
                        color=discord.Color.orange()
                    )

                    for player_data in current_page_players:
                        field_value_parts = []

                        if player_data['Kills Done'] and not player_data['Deaths Done']:
                            field_value_parts.append("Status: Kills requirement met, but deaths are still needed.")
                        elif not player_data['Kills Done'] and player_data['Deaths Done']:
                            field_value_parts.append("Status: Deaths requirement met, but kills are still needed.")
                        elif not player_data['Kills Done'] and not player_data['Deaths Done']:
                            field_value_parts.append("Status: Both requirements are pending.")

                        if player_data['Kills Done']:
                            field_value_parts.append("✅ Kills: **Requirements met!**")
                        else:
                            field_value_parts.append(f"⚔️ Kills: {create_progress_bar(player_data['Kills Progress'])}")
                            field_value_parts.append(
                                f"(Needs {format_number_custom(player_data['Kills Needed'])} more)")

                        if player_data['Deaths Done']:
                            field_value_parts.append("✅ Deaths: **Requirements met!**")
                        else:
                            field_value_parts.append(f"💀 Deaths: {create_progress_bar(player_data['Deaths Progress'])}")
                            field_value_parts.append(
                                f"(Needs {format_number_custom(player_data['Deaths Needed'])} more)")

                        field_value = "\n".join(field_value_parts)

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
                logging.info(f"INFO: Sent {len(all_req_embeds)} pages of player requirements.")

            except Exception as e:
                logging.exception("ERROR: An unexpected error occurred in !req command.")
                await ctx.send(f"An unexpected error occurred while processing the !req command: {str(e)}")

        @self.bot.command(name='top', help='Displays top players by DKP. Usage: !top')
        async def top(ctx):
            logging.debug("top: Викликано команду !top.")
            try:
                df = self.result_df
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

        @self.bot.command(name='pstat', help='Displays player statistics for a specific period. '
                                             'Usage: !pstat <period_name> <Governor_ID>')
        async def pstat(ctx, period_name: str, player_id: str):
            logging.debug(f"pstat: Command called for period {period_name}, ID: {player_id}")

            df_period = await self.get_period_df(period_name)  # get_period_df now handles messages
            if df_period is None:  # If get_period_df returned None, it means an error message was already sent
                return

            player_id = str(player_id).strip()
            player_data = df_period[df_period['Governor ID'] == player_id]

            if player_data.empty:
                await ctx.send(f"Player with ID: {player_id} not found for period `{period_name}`.")
                return

            player = player_data.iloc[0]

            p_stats = {
                'governor_name': player.get('Governor Name', 'N/A'),
                'current_power': player.get('Power_after', 0),
                'power_change': player.get('Power Change', 0),
                'tier4_kills_change': player.get('Tier 4 Kills Change', 0),
                'tier5_kills_change': player.get('Tier 5 Kills Change', 0),
                'total_t4_t5_kills_change': player.get('Total Kills T4+T5 Change', 0),
                'kills_change': player.get('Kills Change', 0),
                'deads_change': player.get('Deads Change', 0),
                'dkp': player.get('DKP', 0),
                'rank': int(player.get('Rank', 0)),
            }

            embed = create_embed(
                title=f"📊 Player Stats for Period: {period_name.upper()} - {p_stats['governor_name']} (ID: {player_id})",
                color=discord.Color.orange()
            )

            embed.add_field(name="💪 Power:", value=(
                f"Current: {format_number_custom(p_stats['current_power'])}\n"
                f"Change: {format_number_custom(p_stats['power_change'])}"
            ), inline=True)

            embed.add_field(name="⚔️ Kills:", value=(
                f"KP Gained: {format_number_custom(p_stats['kills_change'])}\n"
                f"Total T4+T5 Gained: {format_number_custom(p_stats['total_t4_t5_kills_change'])}\n"
                f"T4 Gained: {format_number_custom(p_stats['tier4_kills_change'])}\n"
                f"T5 Gained: {format_number_custom(p_stats['tier5_kills_change'])}"
            ), inline=True)

            embed.add_field(name="💀 Deaths:", value=(
                f"Deaths Gained: {format_number_custom(p_stats['deads_change'])}"
            ), inline=True)

            embed.add_field(name="🏅 DKP (Period):", value=(
                f"Value: {format_number_custom(p_stats['dkp'])}\n"
                f"Rank: #{p_stats['rank']}"
            ), inline=True)

            await ctx.send(embed=embed)
            logging.info(f"pstat: Sent stats for period {period_name}, ID: {player_id}")

        @self.bot.command(name='ptop', help='Displays top players by DKP for a specific period. '
                                            'Usage: !ptop <period_name>')
        async def ptop(ctx, period_name: str):
            logging.debug(f"ptop: Command called for period {period_name}.")

            df_period = await self.get_period_df(period_name)  # get_period_df now handles messages
            if df_period is None:
                return

            # Check for all required columns
            required_cols_ptop = ['DKP', 'Deads Change', 'Kills Change', 'Tier 4 Kills Change', 'Tier 5 Kills Change',
                                  'Governor Name', 'Governor ID', 'Rank']
            for col in required_cols_ptop:
                if col not in df_period.columns:
                    await ctx.send(
                        f"Error: Column '{col}' not found in data for period '{period_name}'. Ensure 'calculator.py' is updated and calculates all necessary metrics for periods.")
                    return

            df_period.loc[:, 'DKP'] = pd.to_numeric(df_period['DKP'], errors='coerce').fillna(0)

            # Sort by DKP for the period
            sorted_df = df_period.sort_values(by='DKP', ascending=False)

            messages = []

            for index, player in sorted_df.iterrows():
                # Only include players with DKP > 0 for ptop
                if player['DKP'] <= 0:
                    continue

                dkp = format_number_custom(player.get('DKP', 0))
                deads_gained = format_number_custom(player.get('Deads Change', 0))
                kills_gained = format_number_custom(player.get('Kills Change', 0))
                t4_kills_gained = format_number_custom(player.get('Tier 4 Kills Change', 0))
                t5_kills_gained = format_number_custom(player.get('Tier 5 Kills Change', 0))

                msg = (
                    f"**#{int(player['Rank'])}. {player['Governor Name']}** (ID: {player['Governor ID']})\n"
                    f"  🏅 DKP: {dkp}\n"
                    f"  💀 Deaths Gained: {deads_gained}\n"
                    f"  ⚔️ Kill Points Gained: {kills_gained}\n"
                    f"  T4 Kills Gained: {t4_kills_gained}\n"
                    f"  T5 Kills Gained: {t5_kills_gained}"
                )
                messages.append(msg)

                # Limit to top 50 entries to avoid overly long output
                #if len(messages) >= 50:
                   # break

            if not messages:
                await ctx.send(f"No significant DKP data found for period '{period_name}'.")
                return

            embeds = []
            for i in range(0, len(messages), ITEMS_PER_PAGE):
                chunk = messages[i:i + ITEMS_PER_PAGE]
                description = "\n".join(chunk)
                embed = create_embed(
                    title=f"Top Players by DKP for {period_name.capitalize()} Period",
                    description=description,
                    color=discord.Color.purple()
                )
                total_pages = (len(messages) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
                embed.set_footer(text=f"Page {len(embeds) + 1}/{total_pages}")
                embeds.append(embed)

            if embeds:
                view = PaginationView(embeds)
                message = await ctx.send(embed=embeds[0], view=view)
                view.message = message
                logging.info(f"ptop: Sent {len(embeds)} pages of top players for period {period_name}.")
            else:
                await ctx.send(f"Could not form top list for period '{period_name}'.")

        @self.bot.command(name='pkd', help='Displays kingdom K/D statistics for a specific period. '
                                           'Usage: !pkd <period_name>')
        async def pkd(ctx, period_name: str):
            logging.debug(f"pkd: Command called for period {period_name}.")

            df_period = await self.get_period_df(period_name) # get_period_df now handles messages
            if df_period is None:
                return

            required_cols_for_pkd = ['Kills Change', 'Deads Change', 'Power Change', 'Power_after']
            for col in required_cols_for_pkd:
                if col not in df_period.columns:
                    await ctx.send(f"Error: Column '{col}' not found in period data for '{period_name}'. Ensure 'calculator.py' calculates all necessary period metrics.")
                    return

            for col in required_cols_for_pkd:
                df_period.loc[:, col] = pd.to_numeric(df_period[col], errors='coerce').fillna(0)


            total_kills_change_period = df_period['Kills Change'].sum()
            total_deads_change_period = df_period['Deads Change'].sum()
            total_power_change_period = df_period['Power Change'].sum()
            current_total_power_period = df_period['Power_after'].sum()

            embed = create_embed(
                title=f"📊 Kingdom Overview (Period: {period_name.upper()})",
                description="",
                color=discord.Color.blue()
            )
            embed.add_field(name="⚔️ Total Kills Gained:", value=format_number_custom(total_kills_change_period), inline=False)
            embed.add_field(name="💀 Total Deaths Gained:", value=format_number_custom(total_deads_change_period), inline=False)
            embed.add_field(name="💪 Change in Total Power:", value=format_number_custom(total_power_change_period), inline=False)
            embed.add_field(name="⚡ Current Total Power:", value=format_number_custom(current_total_power_period), inline=False)

            await ctx.send(embed=embed)
            logging.info(f"pkd: Sent K/D statistics for period {period_name}.")


bot_instance = BotInstance()

# Helper function to run the bot
def run_bot(token):
    bot_instance.bot.run(token)
