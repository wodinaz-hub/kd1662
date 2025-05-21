import pandas as pd
import discord
from discord.ext import commands
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os
from dotenv import load_dotenv
import discord.ui

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

class PaginationView(discord.ui.View):
    def __init__(self, embeds: list[discord.Embed], timeout=180):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.current_page = 0
        self.message = None # Буде встановлено після відправки повідомлення
        self.update_buttons() # Викликаємо після того, як кнопки будуть додані декораторами

    def update_buttons(self):
        # Отримуємо доступ до кнопок через їх custom_id або перевіряємо, що children не порожній
        # Якщо ви використовуєте декоратори, кнопки будуть додані автоматично.
        # Тому нам потрібно знайти кнопки за їх custom_id або переконатися, що вони вже існують.
        # Простий спосіб - перевірити, чи є діти у View.
        if len(self.children) >= 2: # Перевіряємо, чи є кнопки
            self.children[0].disabled = (self.current_page == 0) # Кнопка "Previous"
            self.children[1].disabled = (self.current_page == len(self.embeds) - 1) # Кнопка "Next"

    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.blurple, custom_id="prev_page")
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
        else:
            # Якщо кнопка вимкнена, і хтось її натиснув (через затримку або швидке натискання),
            # просто defer, щоб уникнути помилки "interaction already acknowledged"
            await interaction.response.defer()

    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.blurple, custom_id="next_page")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.embeds) - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
        else:
            await interaction.response.defer()

    async def on_timeout(self):
        # Вимкнути всі кнопки після таймауту
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass # Повідомлення могло бути видалене

# === Data Loading and Preparation ===
def load_and_prepare_data(before_file, after_file, requirements_file):
    try:
        before = pd.read_excel(before_file, header=0)
    except FileNotFoundError:
        raise FileNotFoundError(f"Error: File '{before_file}' not found.")
    if before.empty:
        raise ValueError(f"Error: File '{before_file}' is empty or has no data.")

    try:
        after = pd.read_excel(after_file, header=0)
    except FileNotFoundError:
        raise FileNotFoundError(f"Error: File '{after_file}' not found.")
    if after.empty:
        raise ValueError(f"Error: File '{after_file}' is empty or has no data.")

    try:
        requirements = pd.read_excel(requirements_file, header=0)
    except FileNotFoundError:
        raise FileNotFoundError(f"Error: File '{requirements_file}' not found.")
    if requirements.empty:
        raise ValueError(f"Error: File '{requirements_file}' is empty or has no data.")

    before.columns = before.columns.str.strip()
    after.columns = after.columns.str.strip()
    requirements.columns = requirements.columns.str.strip()

    if 'Governor ID' not in before.columns:
        raise ValueError(f"Error: The file '{before_file}' does not contain the 'Governor ID' column.")

    before['Governor ID'] = before['Governor ID'].fillna('').astype(str).str.strip()
    after['Governor ID'] = after['Governor ID'].fillna('').astype(str).str.strip()
    requirements['Governor ID'] = requirements['Governor ID'].fillna('').astype(str).str.strip()

    return before, after, requirements


# === Statistics Calculation ===
def calculate_stats(before, after, requirements):
    # Змінено на left merge, щоб зберегти всі записи з 'before' навіть якщо їх немає в 'after' або 'requirements'
    result = before.merge(after, on='Governor ID', suffixes=('_before', '_after'), how='left')
    result = result.merge(requirements, on='Governor ID', how='left')

    # Визначте стовпці, які мають бути числовими і можуть містити NaN після злиття
    numeric_columns_to_fill = [
        'Kill Points_before', 'Kill Points_after',
        'Deads_before', 'Deads_after',
        'Tier 5 Kills_before', 'Tier 5 Kills_after',
        'Tier 4 Kills_before', 'Tier 4 Kills_after',
        'Power_before', 'Power_after',
        'Required Kills', 'Required Deaths'
    ]

    # Заповніть NaN значеннями 0 для цих стовпців та переконайтеся, що вони числові
    for col in numeric_columns_to_fill:
        if col in result.columns:
            result[col] = pd.to_numeric(result[col], errors='coerce').fillna(0) # Перетворюємо на число, 'coerce' замінить нечисла на NaN, а потім fillna(0) замінить NaN на 0

    result['Kills Change'] = result['Kill Points_after'] - result['Kill Points_before']
    result['Deads Change'] = result['Deads_after'] - result['Deads_before']

    # Переконайтеся, що Required Kills/Deaths не є нулем перед діленням
    result['Kills Completion (%)'] = result.apply(lambda row: (row['Kill Points_after'] / row['Required Kills']) * 100 if row['Required Kills'] != 0 else 0, axis=1)
    result['Deaths Completion (%)'] = result.apply(lambda row: (row['Deads_after'] / row['Required Deaths']) * 100 if row['Required Deaths'] != 0 else 0, axis=1)

    result['DKP'] = (
        (result['Deads_after'] - result['Deads_before']) * 15 +
        (result['Tier 5 Kills_after'] - result['Tier 5 Kills_before']) * 10 +
        (result['Tier 4 Kills_after'] - result['Tier 4 Kills_before']) * 4
    )

    # Заповніть DKP значеннями 0, якщо воно могло стати NaN
    result['DKP'] = result['DKP'].fillna(0)
    result['Rank'] = result['DKP'].rank(ascending=False, method='min')

    result.to_excel('results.xlsx', index=False)
    print("Results saved to 'results.xlsx'")
    return result

def get_player_stats(result, player_id):
    result['Governor ID'] = result['Governor ID'].astype(str).str.strip()
    player_id = str(player_id).strip()

    player_data = result[result['Governor ID'] == player_id]

    if player_data.empty:
        return None

    player = player_data.iloc[0]

    matchmaking_power = player['Power_before']
    power_change = player['Power_after'] - player['Power_before']
    tier4_kills_change = player['Tier 4 Kills_after'] - player['Tier 4 Kills_before']
    tier5_kills_change = player['Tier 5 Kills_after'] - player['Tier 5 Kills_before']
    kills_change = tier4_kills_change + tier5_kills_change
    kill_points_change = player['Kill Points_after'] - player['Kill Points_before']
    deads_change = player['Deads_after'] - player['Deads_before']

    kills_completion = (kills_change / player['Required Kills']) * 100 if player['Required Kills'] != 0 else 0
    deads_completion = (deads_change / player['Required Deaths']) * 100 if player['Required Deaths'] != 0 else 0
    dkp = player['DKP']
    rank = int(player['Rank'])
    governor_name = player['Governor Name']
    required_kills = player['Required Kills']
    required_deaths = player['Required Deaths']

    return {
        'governor_name': governor_name,
        'matchmaking_power': matchmaking_power,
        'power_change': power_change,
        'tier4_kills_change': tier4_kills_change,
        'tier5_kills_change': tier5_kills_change,
        'kills_change': kills_change,
        'kill_points_change': kill_points_change,
        'deads_change': deads_change,
        'kills_completion': kills_completion,
        'deads_completion': deads_completion,
        'dkp': dkp,
        'rank': rank,
        'required_kills': required_kills,
        'required_deaths': required_deaths,
    }

# === Discord Bot ===
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

def create_dual_semi_circular_progress(kill_progress_percent, death_progress_percent, filename='dual_progress_chart.png'):
    """Creates and saves a dual semi-circular progress chart for Kills and Deaths with percentage display."""
    fig, ax = plt.subplots(figsize=(6, 3), facecolor='#222222')
    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-0.6, 1.1)
    ax.axis('off')

    center = (0, 0)
    theta1 = 0
    theta2 = 180

    # --- Outer layer (background) ---
    radius_outer = 1.0
    background = patches.Arc(center, radius_outer * 2, radius_outer * 2, angle=0, theta1=theta1, theta2=theta2,
                             linewidth=12, color='#555555', alpha=0.7)
    ax.add_patch(background)

    # --- Inner layer (Kills progress) ---
    radius_inner_kills = 0.8
    angle_kills = theta1 + (theta2 - theta1) * (min(kill_progress_percent, 100) / 100)  # Limit for the arc
    kills_progress = patches.Arc(center, radius_inner_kills * 2, radius_inner_kills * 2, angle=0, theta1=theta1, theta2=angle_kills,
                                  linewidth=12, color='#D4AF37', alpha=0.8)
    ax.add_patch(kills_progress)

    # --- Middle layer (Deaths progress) ---
    radius_middle_deaths = 0.9
    angle_deaths = theta1 + (theta2 - theta1) * (min(death_progress_percent, 100) / 100)  # Limit for the arc
    deaths_progress = patches.Arc(center, radius_middle_deaths * 2, radius_middle_deaths * 2, angle=0, theta1=theta1, theta2=angle_deaths,
                                   linewidth=12, color='#E879F9', alpha=0.8)
    ax.add_patch(deaths_progress)

    # --- Text ---
    ax.text(-0.5, -0.2, f'Kills: {kill_progress_percent:.0f}%', ha='center', va='center', fontsize=12, color='#D4AF37')
    ax.text(0.5, -0.2, f'Deaths: {death_progress_percent:.0f}%', ha='center', va='center', fontsize=12, color='#E879F9')
    ax.text(0, 0.3, 'Progress', ha='center', va='center', fontsize=14, color='#AAAAAA')

    plt.gca().set_aspect('equal', adjustable='box')
    plt.savefig(filename, transparent=True)
    return filename

@bot.event
async def on_ready():
    print(f'Bot {bot.user} has started!')

@bot.command(name="bot_help")
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

def create_progress_bar(percent, length=20):
    filled_length = int(length * percent // 100)
    bar = '█' * filled_length + '-' * (length - filled_length)
    return f'[{bar}] {percent:.0f}%'


@bot.command(name="req")
async def requirements(ctx):
    try:
        result = pd.read_excel('results.xlsx')
        not_completed = []
        for index, row in result.iterrows():
            # Важливо: here we calculate percentages directly.
            # No min(100, ...) here, as we want actual percentages for display
            kills_progress_percent = (row['Kill Points_after'] - row['Kill Points_before']) / row[
                'Required Kills'] * 100 if row['Required Kills'] != 0 else 0
            deaths_progress_percent = (row['Deads_after'] - row['Deads_before']) / row['Required Deaths'] * 100 if row[
                                                                                                                       'Required Deaths'] != 0 else 0

            # Calculate kills/deaths needed
            # Use max(0, ...) to ensure 'needed' is not negative if over-completed
            kills_needed = max(0, row['Required Kills'] - (row['Kill Points_after'] - row['Kill Points_before']))
            deaths_needed = max(0, row['Required Deaths'] - (row['Deads_after'] - row['Deads_before']))

            if kills_needed > 0 or deaths_needed > 0:  # Only add players who haven't met ALL requirements
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
                # Якщо поточний embed не існує або досягнуто ліміту полів (25 полів на embed)
                # або якщо embed'у загрожує перевищення ліміту символів (можна додати більш складну перевірку)
                if current_embed is None or fields_count >= 25:
                    if current_embed is not None:  # Якщо це не перший embed, додаємо його до списку
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

            # Додаємо останній embed, якщо він не порожній
            if current_embed is not None and fields_count > 0:
                all_embeds.append(current_embed)

            # Відправка пагінованого повідомлення або просто одного embed
            if len(all_embeds) == 0:  # Це може статися, якщо not_completed був порожнім, але ми обробили його вище
                embed = discord.Embed(title="🎉 All players have met the requirements!", color=discord.Color.green())
                await ctx.send(embed=embed)
            elif len(all_embeds) == 1:
                await ctx.send(embed=all_embeds[0])
            else:
                view = PaginationView(all_embeds)
                # Відправляємо перше повідомлення, view прикріплюється до нього
                message = await ctx.send(embed=all_embeds[0], view=view)
                view.message = message  # Передаємо посилання на відправлене повідомлення у View
    except Exception as e:
        await ctx.send(f"An error occurred while processing the !req command: {str(e)}")

@bot.command()
async def kd_stats(ctx):
    try:
        result = pd.read_excel('results.xlsx')
        total_kills_gained = result['Kills Change'].sum()
        total_deaths_gained = result['Deads Change'].sum()

        # Розрахунок зміни загальної потужності королівства
        total_power_change = (result['Power_after'] - result['Power_before']).sum()

        # Розрахунок поточної загальної потужності королівства
        current_total_power = result['Power_after'].sum()

        embed = discord.Embed(title="📊 Kingdom Overview", color=discord.Color.green())
        embed.add_field(
            name="⚔️ Total Kills Gained:",
            value=f"{total_kills_gained:,.0f}",  # Додано роздільник тисяч
            inline=False
        )
        embed.add_field(
            name="🤕 Total Deaths Gained:",
            value=f"{total_deaths_gained:,.0f}",  # Додано роздільник тисяч
            inline=False
        )
        embed.add_field(
            name="💪 Change in Total Power:",
            value=f"{total_power_change:,.0f}",  # Додано роздільник тисяч
            inline=False
        )
        embed.add_field(
            name="⚡ Current Total Power:",
            value=f"{current_total_power:,.0f}",  # Додано роздільник тисяч
            inline=False
        )

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")

@bot.command()
async def top(ctx, limit: int = 5):
    try:
        result = pd.read_excel('results.xlsx')
        result_sorted = result.sort_values(by='DKP', ascending=False).head(limit)
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

@bot.command()
async def stats(ctx, player_id):
    """Displays the statistics of a specific player with a dual semi-circular progress chart for Kills and Deaths."""
    try:
        result_df = pd.read_excel('results.xlsx')
        player_stats = get_player_stats(result_df, player_id)

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
                player_stats['kills_completion'],  # Передаємо фактичний відсоток
                player_stats['deads_completion']   # Передаємо фактичний відсоток
            )
            with open(chart_path, 'rb') as f:
                picture = discord.File(f)
                await ctx.send(embed=embed, file=picture)
            os.remove(chart_path)

        else:
            await ctx.send(f"Player with ID {player_id} not found.")
    except Exception as e:
        await ctx.send(f"An error occurred while processing the !stats command: {str(e)}")

# === Main Execution ===
def main():
    before_file = 'start_kvk.xlsx'
    after_file = 'pass4.xlsx'
    requirements_file = 'required.xlsx'

    try:
        before, after, requirements = load_and_prepare_data(before_file, after_file, requirements_file)
        result_df = calculate_stats(before, after, requirements)
        bot.run(TOKEN)

    except (FileNotFoundError, ValueError) as e:
        print(f"Critical error during data loading: {e}")
        exit(1)

if __name__ == "__main__":
    main()