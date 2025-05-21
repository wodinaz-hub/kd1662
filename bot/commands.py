import discord
from discord.ext import commands
import pandas as pd
import os

from data_processing.calculator import get_player_stats
from utils.chart_generator import create_dual_semi_circular_progress
from utils.helpers import create_progress_bar
from bot.view import PaginationView
from typing import List, Tuple

ITEMS_PER_PAGE = 5


def format_number_custom(num_value):
    print(f"DEBUG: format_number_custom received: {num_value} (type: {type(num_value)})")  # Лог

    if not isinstance(num_value, (int, float)):
        print(f"DEBUG: Not a number, returning: {str(num_value)}")  # Лог
        return str(num_value)  # Повертаємо як є, якщо не число

    if float(num_value).is_integer():
        num_str = str(int(num_value))
    else:
        num_str = f"{num_value:.2f}"

    print(f"DEBUG: num_str after initial formatting: {num_str}")  # Лог

    parts = num_str.split('.')
    integer_part = parts[0]
    decimal_part = parts[1] if len(parts) > 1 else ""

    formatted_integer_part = ""
    for i, digit in enumerate(reversed(integer_part)):
        formatted_integer_part += digit
        if (i + 1) % 3 == 0 and (i + 1) != len(integer_part):
            formatted_integer_part += "."
    formatted_integer_part = formatted_integer_part[::-1]

    result = ""
    if decimal_part:
        result = f"{formatted_integer_part},{decimal_part}"
    else:
        result = formatted_integer_part

    print(f"DEBUG: format_number_custom returning: {result}")  # Лог
    return result


def setup_commands(bot_instance):
    def get_result_df():
        if hasattr(bot_instance, 'result_df') and not bot_instance.result_df.empty:
            return bot_instance.result_df
        else:
            print("Warning: result_df not found on bot_instance. Attempting to read from results.xlsx.")
            try:
                return pd.read_excel('results.xlsx')
            except FileNotFoundError:
                print("Error: results.xlsx not found. Some commands may not function.")
                return pd.DataFrame()

    @bot_instance.command(name="bot_help")
    async def help_command(ctx):
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

    @bot_instance.command(name="req")
    async def requirements(ctx):
        try:
            df = get_result_df()
            if df.empty:
                await ctx.send("Error: Data not loaded. Please ensure data files are present and bot restarted.")
                return

            not_completed_players_data = []
            for index, row in df.iterrows():
                kills_progress_percent = (row['Kill Points_after'] - row['Kill Points_before']) / row[
                    'Required Kills'] * 100 if row['Required Kills'] != 0 else (
                    100 if (row['Kill Points_after'] - row['Kill Points_before']) >= 0 else 0)
                deaths_progress_percent = (row['Deads_after'] - row['Deads_before']) / row['Required Deaths'] * 100 if \
                    row['Required Deaths'] != 0 else (100 if (row['Deads_after'] - row['Deads_before']) >= 0 else 0)

                kills_needed = max(0, row['Required Kills'] - (row['Kill Points_after'] - row['Kill Points_before']))
                deaths_needed = max(0, row['Required Deaths'] - (row['Deads_after'] - row['Deads_before']))

                if kills_needed > 0 or deaths_needed > 0:
                    not_completed_players_data.append({
                        'Governor Name': row['Governor Name'],
                        'Governor ID': row['Governor ID'],
                        'Kills Needed': kills_needed,
                        'Deaths Needed': deaths_needed,
                        'Kills Progress': kills_progress_percent,
                        'Deaths Progress': deaths_progress_percent
                    })

            if not not_completed_players_data:
                embed = discord.Embed(title="🎉 All players have met the requirements!", color=discord.Color.green())
                await ctx.send(embed=embed)
                return

            all_req_embeds = []
            for i in range(0, len(not_completed_players_data), ITEMS_PER_PAGE):
                current_page_players = not_completed_players_data[i:i + ITEMS_PER_PAGE]

                embed = discord.Embed(
                    title="⚠️ Players who have not met the requirements",
                    color=discord.Color.orange()
                )

                for player_data in current_page_players:
                    field_value = (
                        f"⚔️ Kills: {create_progress_bar(player_data['Kills Progress'])}\n"
                        f"({format_number_custom(player_data['Kills Needed'])} remaining)\n"
                        f"💀 Deaths: {create_progress_bar(player_data['Deaths Progress'])}\n"
                        f"({format_number_custom(player_data['Deaths Needed'])} remaining)"
                    )
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
        except Exception as e:
            await ctx.send(f"An error occurred while processing the !req command: {str(e)}")

    @bot_instance.command()
    async def kd_stats(ctx):
        try:
            df = get_result_df()
            if df.empty:
                await ctx.send("Error: Data not loaded. Please ensure data files are present and bot restarted.")
                return

            total_kills_gained = df['Kills Change'].sum()
            total_deaths_gained = df['Deads Change'].sum()

            total_power_change = (df['Power_after'] - df['Power_before']).sum()
            current_total_power = df['Power_after'].sum()

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

        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @bot_instance.command()
    async def top(ctx):
        try:
            df = get_result_df()
            if df.empty:
                await ctx.send("Error: Data not loaded. Please ensure data files are present and bot restarted.")
                return

            df['DKP'] = pd.to_numeric(df['DKP'], errors='coerce').fillna(0)

            result_sorted = df.sort_values(by='DKP', ascending=False)

            if result_sorted.empty:
                await ctx.send("No players found to display in top list.")
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
                    field_value = (
                        f"🏅 DKP: {format_number_custom(row['DKP'])}\n"
                        f"💀 Deaths Gained: {format_number_custom(row['Deads Change'])}\n"
                        f"⚔️ Kill Points Gained: {format_number_custom(row['Kills Change'])}\n"
                        f"T4 Kills Gained: {format_number_custom(row['Tier 4 Kills_after'] - row['Tier 4 Kills_before'])}\n"
                        f"T5 Kills Gained: {format_number_custom(row['Tier 5 Kills_after'] - row['Tier 5 Kills_before'])}"
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
        except Exception as e:
            await ctx.send(f"An error occurred while processing the !top command: {str(e)}")

    @bot_instance.command()
    async def stats(ctx, player_id):
        try:
            df = get_result_df()
            if df.empty:
                await ctx.send("Error: Data not loaded. Please ensure data files are present and bot restarted.")
                return

            player_stats = get_player_stats(df, player_id)

            if player_stats:
                embed = discord.Embed(title=f"📊 Player Statistics: {player_stats['governor_name']} (ID: {player_id})",
                                      color=discord.Color.blue())
                embed.add_field(name="🔹 Matchmaking Power:",
                                value=f"{format_number_custom(player_stats['matchmaking_power'])}", inline=False)
                embed.add_field(name="🔹 Power Change:", value=f"{format_number_custom(player_stats['power_change'])}",
                                inline=False)

                embed.add_field(name="⚔️ Kills:", value=(
                    f"Required: {format_number_custom(player_stats['required_kills'])}\n"
                    f"Total: {format_number_custom(player_stats['kills_change'])}\n"
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
                else:
                    await ctx.send(embed=embed)
                    print(f"Warning: Chart file not created at {chart_path}. Sending embed without file.")

            else:
                await ctx.send(f"Player with ID {player_id} not found.")
        except Exception as e:
            await ctx.send(f"An error occurred while processing the !stats command: {str(e)}")