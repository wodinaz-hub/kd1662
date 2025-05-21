import discord
from discord.ext import commands
import pandas as pd
import os # Для os.remove, який використовується в `stats`

# Імпортуємо функції з інших модулів
from data_processing.calculator import get_player_stats # Функція для отримання статистики гравця
from utils.chart_generator import create_dual_semi_circular_progress # Функція для графіків
from utils.helpers import create_progress_bar # Допоміжні функції
from bot.view import PaginationView # Клас для пагінації


def setup_commands(bot_instance):
    # result_df буде доступний через bot_instance.result_df, встановлений в main.py
    def get_result_df():
        if hasattr(bot_instance, 'result_df') and not bot_instance.result_df.empty:
            return bot_instance.result_df
        else:
            print("Warning: result_df not found on bot_instance. Attempting to read from results.xlsx.")
            try:
                # Ця гілка має спрацьовувати лише як запасний варіант
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
                "Displays a list of players who have not met the kill or death requirements.\n"
                "For each player, shows the progress towards the requirements as a progress bar and the remaining kills and deaths needed."
            ),
            inline=False,
        )
        embed.add_field(
            name="!top [limit=5]",
            value=(
                "Displays a list of the top players by DKP (default limit is 5).\n"
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

            not_completed = []
            for index, row in df.iterrows():
                kills_progress_percent = (row['Kill Points_after'] - row['Kill Points_before']) / row['Required Kills'] * 100 if row['Required Kills'] != 0 else 0
                deaths_progress_percent = (row['Deads_after'] - row['Deads_before']) / row['Required Deaths'] * 100 if row['Required Deaths'] != 0 else 0

                kills_needed = max(0, row['Required Kills'] - (row['Kill Points_after'] - row['Kill Points_before']))
                deaths_needed = max(0, row['Required Deaths'] - (row['Deads_after'] - row['Deads_before']))

                if kills_needed > 0 or deaths_needed > 0:
                    not_completed.append({
                        'Governor Name': row['Governor Name'],
                        'Governor ID': row['Governor ID'],
                        'Kills Needed': kills_needed,
                        'Deaths Needed': deaths_needed,
                        'Kills Progress': kills_progress_percent,
                        'Deaths Progress': deaths_progress_percent
                    })

            if not not_completed:
                embed = discord.Embed(title="🎉 All players have met the requirements!", color=discord.Color.green())
                await ctx.send(embed=embed)
            else:
                all_embeds = []
                current_embed = None
                fields_count = 0
                part_number = 1

                for player in not_completed:
                    if current_embed is None or fields_count >= 25:
                        if current_embed is not None:
                            all_embeds.append(current_embed)
                        current_embed = discord.Embed(
                            title=f"⚠️ Players who have not met the requirements (Part {part_number}):",
                            color=discord.Color.orange())
                        fields_count = 0
                        part_number += 1

                    field_value = (
                        f"⚔️ Kills: {create_progress_bar(player['Kills Progress'])}\n"
                        f"({player['Kills Needed']:.0f} remaining)\n"
                        f"🤕 Deaths: {create_progress_bar(player['Deaths Progress'])}\n"
                        f"({player['Deaths Needed']:.0f} remaining)"
                    )

                    current_embed.add_field(
                        name=f"{player['Governor Name']} (ID: {player['Governor ID']})",
                        value=field_value,
                        inline=False
                    )
                    fields_count += 1

                if current_embed is not None and fields_count > 0:
                    all_embeds.append(current_embed)

                if len(all_embeds) == 0:
                    embed = discord.Embed(title="🎉 All players have met the requirements!", color=discord.Color.green())
                    await ctx.send(embed=embed)
                elif len(all_embeds) == 1:
                    await ctx.send(embed=all_embeds[0])
                else:
                    view = PaginationView(all_embeds)
                    message = await ctx.send(embed=all_embeds[0], view=view)
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
                value=f"{total_kills_gained:,.0f}",
                inline=False
            )
            embed.add_field(
                name="🤕 Total Deaths Gained:",
                value=f"{total_deaths_gained:,.0f}",
                inline=False
            )
            embed.add_field(
                name="💪 Change in Total Power:",
                value=f"{total_power_change:,.0f}",
                inline=False
            )
            embed.add_field(
                name="⚡ Current Total Power:",
                value=f"{current_total_power:,.0f}",
                inline=False
            )
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @bot_instance.command()
    async def top(ctx, limit: int = 5):
        try:
            df = get_result_df()
            if df.empty:
                await ctx.send("Error: Data not loaded. Please ensure data files are present and bot restarted.")
                return

            result_sorted = df.sort_values(by='DKP', ascending=False).head(limit)
            embed = discord.Embed(title=f"🏆 Top {limit} Players (KVK Gains)", color=discord.Color.gold())
            for index, row in result_sorted.iterrows():
                embed.add_field(
                    name=f"{index + 1}. {row['Governor Name']}",
                    value=(
                        f"🏅 DKP: {round(row['DKP']):,}\n"
                        f"🤕 Deaths Gained: {round(row['Deads Change']):,}\n"
                        f"⚔️ Kill Points Gained: {round(row['Kills Change']):,}\n"
                        f"T4 Kills Gained: {round(row['Tier 4 Kills_after'] - row['Tier 4 Kills_before']):,}\n"
                        f"T5 Kills Gained: {round(row['Tier 5 Kills_after'] - row['Tier 5 Kills_before']):,}"
                    ),
                    inline=False
                )
            await ctx.send(embed=embed)
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
                embed = discord.Embed(title=f"📊 Player Statistics: {player_stats['governor_name']} (ID: {player_id})", color=discord.Color.blue())
                embed.add_field(name="🔹 Matchmaking Power:", value=f"{round(player_stats['matchmaking_power']):,}", inline=False)
                embed.add_field(name="🔹 Power Change:", value=f"{round(player_stats['power_change']):,}", inline=False)

                embed.add_field(name="⚔️ Kills:", value=(
                    f"Required: {round(player_stats['required_kills']):,}\n"
                    f"Total: {round(player_stats['kills_change']):,}\n"
                    f"T4: {round(player_stats['tier4_kills_change']):,}\n"
                    f"T5: {round(player_stats['tier5_kills_change']):,}\n"
                    f"Progress: {player_stats['kills_completion']:.2f}%"
                ), inline=True)
                embed.add_field(name="🤕 Deaths:", value=(
                    f"Required: {round(player_stats['required_deaths']):,}\n"
                    f"Total: {round(player_stats['deads_change']):,}\n"
                    f"Progress: {player_stats['deads_completion']:.2f}%"
                ), inline=True)

                embed.add_field(name="🏅 DKP:", value=f"{round(player_stats['dkp']):,}", inline=False)
                embed.add_field(name="🏆 DKP Rank:", value=f"#{player_stats['rank']}", inline=False)

                chart_path = create_dual_semi_circular_progress(
                    player_stats['kills_completion'],
                    player_stats['deads_completion']
                )
                with open(chart_path, 'rb') as f:
                    picture = discord.File(f)
                    await ctx.send(embed=embed, file=picture)
                os.remove(chart_path)

            else:
                await ctx.send(f"Player with ID {player_id} not found.")
        except Exception as e:
            await ctx.send(f"An error occurred while processing the !stats command: {str(e)}")