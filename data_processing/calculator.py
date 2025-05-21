import pandas as pd
import numpy as np # Для fillna

def calculate_stats(before, after, requirements):
    result = before.merge(after, on='Governor ID', suffixes=('_before', '_after'), how='left')
    result = result.merge(requirements, on='Governor ID', how='left')

    numeric_columns_to_fill = [
        'Kill Points_before', 'Kill Points_after',
        'Deads_before', 'Deads_after',
        'Tier 5 Kills_before', 'Tier 5 Kills_after',
        'Tier 4 Kills_before', 'Tier 4 Kills_after',
        'Power_before', 'Power_after',
        'Required Kills', 'Required Deaths'
    ]

    for col in numeric_columns_to_fill:
        if col in result.columns:
            result[col] = pd.to_numeric(result[col], errors='coerce').fillna(0)

    result['Kills Change'] = result['Kill Points_after'] - result['Kill Points_before']
    result['Deads Change'] = result['Deads_after'] - result['Deads_before']

    result['Kills Completion (%)'] = result.apply(lambda row: (row['Kill Points_after'] / row['Required Kills']) * 100 if row['Required Kills'] != 0 else 0, axis=1)
    result['Deaths Completion (%)'] = result.apply(lambda row: (row['Deads_after'] / row['Required Deaths']) * 100 if row['Required Deaths'] != 0 else 0, axis=1)

    result['DKP'] = (
        (result['Deads_after'] - result['Deads_before']) * 15 +
        (result['Tier 5 Kills_after'] - result['Tier 5 Kills_before']) * 10 +
        (result['Tier 4 Kills_after'] - result['Tier 4 Kills_before']) * 4
    )

    result['DKP'] = result['DKP'].fillna(0)
    result['Rank'] = result['DKP'].rank(ascending=False, method='min')

    # Зберігання результатів в Excel. Ця логіка тепер в цьому файлі.
    result.to_excel('results.xlsx', index=False)
    print("Results saved to 'results.xlsx'")
    return result

def get_player_stats(result_df, player_id): # Приймає result_df як аргумент
    result_df['Governor ID'] = result_df['Governor ID'].astype(str).str.strip()
    player_id = str(player_id).strip()

    player_data = result_df[result_df['Governor ID'] == player_id]

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