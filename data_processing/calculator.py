import pandas as pd
import numpy as np
import logging
import os

# Configure logging for the calculator module
logger = logging.getLogger('data_processing.calculator')


def calculate_stats():
    """
    Calculates overall KVK statistics based on initial, intermediate, and final metrics.
    The list of players is strictly filtered by the 'kvk_start_power.xlsx' file.
    Input files for overall KVK stats are expected in the project root directory.
    The output file is saved in the 'results' subfolder within the project root.
    """
    # Get the absolute path to the directory of the current script (calculator.py)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Determine the project root directory: assuming 'data_processing' is one level below
    # For example, if script_dir is /path/to/project_root/data_processing, then project_root is /path/to/project_root
    project_root = os.path.abspath(os.path.join(script_dir, os.pardir))

    # --- DEBUG OUTPUTS ---
    print(f"DEBUG (calculate_stats): Script directory: {script_dir}")
    print(f"DEBUG (calculate_stats): Project root directory: {project_root}")
    # --- END DEBUG OUTPUTS ---

    # Define paths to input files, which are located in the project root directory
    start_power_file = os.path.join(project_root, 'kvk_start_power.xlsx')
    before_metrics_file = os.path.join(project_root, 'kvk_before_metrics.xlsx')
    after_metrics_file = os.path.join(project_root, 'kvk_after_metrics.xlsx')
    requirements_file = os.path.join(project_root, 'kvk_requirements.xlsx')  # Optional file

    # Define the path for the output file, which will be saved in the 'results' folder
    output_file = os.path.join(project_root, 'results/results.xlsx')
    output_dir = os.path.dirname(output_file)

    # --- DEBUG OUTPUTS ---
    print(f"DEBUG (calculate_stats): Looking for KVK start power file at: {start_power_file}")
    print(f"DEBUG (calculate_stats): Looking for 'before' metrics file at: {before_metrics_file}")
    print(f"DEBUG (calculate_stats): Looking for 'after' metrics file at: {after_metrics_file}")
    print(f"DEBUG (calculate_stats): Looking for requirements file (optional) at: {requirements_file}")
    # --- END DEBUG OUTPUTS ---

    # Check for the existence of critical input files. If missing, log an error and return an empty DataFrame.
    if not os.path.exists(start_power_file):
        logger.error(
            f"Critical error: KVK start power file '{start_power_file}' not found. Cannot calculate overall KVK statistics.")
        return pd.DataFrame()
    if not os.path.exists(before_metrics_file):
        logger.error(
            f"Critical error: KVK 'before' metrics file '{before_metrics_file}' not found. Cannot calculate overall KVK statistics.")
        return pd.DataFrame()
    if not os.path.exists(after_metrics_file):
        logger.error(
            f"Critical error: KVK 'after' metrics file '{after_metrics_file}' not found. Cannot calculate overall KVK statistics.")
        return pd.DataFrame()

    try:
        # Load required Excel files
        df_start_kvk = pd.read_excel(start_power_file)
        logger.info(f"File '{os.path.basename(start_power_file)}' successfully loaded. Shape: {df_start_kvk.shape}")
        df_before_metrics = pd.read_excel(before_metrics_file)
        logger.info(
            f"File '{os.path.basename(before_metrics_file)}' successfully loaded. Shape: {df_before_metrics.shape}")
        df_after_metrics = pd.read_excel(after_metrics_file)
        logger.info(
            f"File '{os.path.basename(after_metrics_file)}' successfully loaded. Shape: {df_after_metrics.shape}")

        df_req = pd.DataFrame()  # Initialize requirements DataFrame as empty
        if os.path.exists(requirements_file):
            df_req = pd.read_excel(requirements_file)
            logger.info(
                f"Optional requirements file '{os.path.basename(requirements_file)}' successfully loaded. Shape: {df_req.shape}")
        else:
            logger.warning(
                f"Optional requirements file '{os.path.basename(requirements_file)}' not found. Player requirements will be considered zero.")

    except Exception as e:
        logger.error(f"Error loading one or more Excel files for overall KVK statistics: {e}")
        return pd.DataFrame()

    # Standardize column names by stripping leading/trailing whitespace
    for df_item in [df_start_kvk, df_before_metrics, df_after_metrics, df_req]:
        if not df_item.empty:
            df_item.columns = [col.strip() for col in df_item.columns]

    # Ensure 'Governor ID' column is of string type in all DataFrames for accurate merging
    df_start_kvk['Governor ID'] = df_start_kvk['Governor ID'].astype(str)
    df_before_metrics['Governor ID'] = df_before_metrics['Governor ID'].astype(str)
    df_after_metrics['Governor ID'] = df_after_metrics['Governor ID'].astype(str)
    if not df_req.empty:
        df_req['Governor ID'] = df_req['Governor ID'].astype(str)

    logger.debug(
        f"Governor IDs after type conversion: df_start_kvk examples: {df_start_kvk['Governor ID'].head().tolist()}")

    # Rename columns for clarity and to avoid conflicts during merging
    # Include Russian column names and exact names provided by the user
    df_start_kvk_renamed_cols = {
        'Power': 'Power_at_KVK_start',
        'Мощь': 'Power_at_KVK_start'
    }
    df_before_metrics_renamed_cols = {
        'Kill Points': 'Kill Points_before', 'Очки Убийств': 'Kill Points_before',
        'Dead Troops': 'Deads_before', 'Deaths': 'Deads_before',
        'Погибшие войска': 'Deads_before', 'Смерти': 'Deads_before',
        'Deads': 'Deads_before',  # Exact name from user
        'T4 Kills': 'Tier 4 Kills_before', 'Убийства Т4': 'Tier 4 Kills_before',
        'Tier 4 Kills': 'Tier 4 Kills_before',  # Exact name from user
        'T5 Kills': 'Tier 5 Kills_before', 'Убийства Т5': 'Tier 5 Kills_before',
        'Tier 5 Kills': 'Tier 5 Kills_before',  # Exact name from user
        'Power': 'Power_before', 'Мощь': 'Power_before'
    }
    df_after_metrics_renamed_cols = {
        'Kill Points': 'Kill Points_after', 'Очки Убийств': 'Kill Points_after',
        'Dead Troops': 'Deads_after', 'Deaths': 'Deads_after',
        'Погибшие войска': 'Deads_after', 'Смерти': 'Deads_after',
        'Deads': 'Deads_after',  # Exact name from user
        'T4 Kills': 'Tier 4 Kills_after', 'Убийства Т4': 'Tier 4 Kills_after',
        'Tier 4 Kills': 'Tier 4 Kills_after',  # Exact name from user
        'T5 Kills': 'Tier 5 Kills_after', 'Убийства Т5': 'Tier 5 Kills_after',
        'Tier 5 Kills': 'Tier 5 Kills_after',  # Exact name from user
        'Power': 'Power_after', 'Мощь': 'Power_after',
        'Governor Name': 'Governor Name_after', 'Имя Губернатора': 'Governor Name_after'
    }

    # Create mappings, keeping only keys that exist in the DataFrame
    def create_valid_rename_map(df, rename_dict):
        return {k: v for k, v in rename_dict.items() if k in df.columns}

    df_start_kvk = df_start_kvk.rename(columns=create_valid_rename_map(df_start_kvk, df_start_kvk_renamed_cols))
    df_before_metrics = df_before_metrics.rename(
        columns=create_valid_rename_map(df_before_metrics, df_before_metrics_renamed_cols))
    df_after_metrics = df_after_metrics.rename(
        columns=create_valid_rename_map(df_after_metrics, df_after_metrics_renamed_cols))

    # Select only the necessary columns from each DataFrame before merging
    # Important: use the new, renamed column names
    df_start_kvk = df_start_kvk[['Governor ID', 'Power_at_KVK_start']]
    df_before_metrics = df_before_metrics[
        ['Governor ID', 'Kill Points_before', 'Deads_before', 'Tier 4 Kills_before', 'Tier 5 Kills_before',
         'Power_before']]
    df_after_metrics = df_after_metrics[
        ['Governor ID', 'Governor Name_after', 'Kill Points_after', 'Deads_after', 'Tier 4 Kills_after',
         'Tier 5 Kills_after', 'Power_after']]
    if not df_req.empty:
        df_req = df_req[['Governor ID', 'Required Kills', 'Required Deaths']]

    # --- Main Player Filtering Logic for Overall KVK Stats ---
    # Start with kvk_start_power.xlsx as the defining list of players for KVK.
    df_final = df_start_kvk.copy()
    logger.info(f"Initial number of players from '{os.path.basename(start_power_file)}': {len(df_final)}")

    # Inner merge with 'before' metrics: keeps only players present in BOTH 'kvk_start_power' AND 'kvk_before_metrics'.
    # Players present in 'kvk_start_power' but missing from 'kvk_before_metrics' are excluded.
    df_final = pd.merge(df_final, df_before_metrics, on='Governor ID', how='inner')
    logger.info(f"After inner merge with '{os.path.basename(before_metrics_file)}': {len(df_final)} players remaining.")
    if df_final.empty:
        logger.warning(
            "DataFrame is empty after merging with 'before' metrics. Check 'Governor ID' column for matches in both files.")
        return pd.DataFrame()

    # Inner merge with 'after' metrics: further keeps only players present in the current 'df_final' AND in 'kvk_after_metrics'.
    # Players who were present in previous stages but disappeared by the 'after metrics' snapshot are now excluded.
    df_final = pd.merge(df_final, df_after_metrics, on='Governor ID', how='inner')
    logger.info(f"After inner merge with '{os.path.basename(after_metrics_file)}': {len(df_final)} players remaining.")
    if df_final.empty:
        logger.warning(
            "DataFrame is empty after merging with 'after' metrics. Check 'Governor ID' column for matches in all three core files.")
        return pd.DataFrame()

    # Left merge with requirements: adds requirement data without excluding players.
    # Players without requirement data will have NaN/0 for requirement columns.
    if not df_req.empty:
        df_final = pd.merge(df_final, df_req, on='Governor ID', how='left')
        logger.info(f"Left merged with '{os.path.basename(requirements_file)}'.")
    else:
        # If requirements file not found, set requirements to 0 for all players
        df_final['Required Kills'] = 0
        df_final['Required Deaths'] = 0
        logger.warning(
            f"File '{os.path.basename(requirements_file)}' was not used, 'Required Kills' and 'Required Deaths' columns set to 0.")

    # Fill NaN values in numeric columns (which may appear due to left merges or missing data) with zeros.
    numeric_cols_to_fill = [
        'Power_at_KVK_start', 'Power_before', 'Power_after',
        'Kill Points_before', 'Kill Points_after',
        'Deads_before', 'Deads_after',
        'Tier 4 Kills_before', 'Tier 4 Kills_after',
        'Tier 5 Kills_before', 'Tier 5 Kills_after',
        'Required Kills', 'Required Deaths'
    ]
    for col in numeric_cols_to_fill:
        if col in df_final.columns:
            # Convert to numeric type (errors coerce to NaN), then fill NaN with zeros
            df_final[col] = pd.to_numeric(df_final[col], errors='coerce').fillna(0)

    # Calculate metric changes during the KVK period
    df_final['Power Change'] = df_final['Power_after'] - df_final['Power_at_KVK_start']
    df_final['Kills Change'] = df_final['Kill Points_after'] - df_final['Kill Points_before']
    df_final['Deads Change'] = df_final['Deads_after'] - df_final['Deads_before']
    df_final['Tier 4 Kills Change'] = df_final['Tier 4 Kills_after'] - df_final['Tier 4 Kills_before']
    df_final['Tier 5 Kills Change'] = df_final['Tier 5 Kills_after'] - df_final['Tier 5 Kills_before']
    df_final['Total Kills T4+T5 Change'] = df_final['Tier 4 Kills Change'] + df_final['Tier 5 Kills Change']

    # Calculate DKP (Disciplinary Kill Points) using the specified formula
    df_final['DKP'] = (
            (df_final['Deads Change'] * 15) +  # Зміна смертей
            (df_final['Tier 5 Kills Change'] * 10) +  # Зміна T5 вбивств
            (df_final['Tier 4 Kills Change'] * 4)  # Зміна T4 вбивств
    )

    # Calculate completion percentages for kill and death requirements
    # Handle division by zero (Required Kills/Deaths = 0) and infinite values
    df_final['Kills Completion'] = (df_final['Total Kills T4+T5 Change'] / df_final['Required Kills'] * 100).replace(
        [np.inf, -np.inf], 0).fillna(0)
    # If Required Kills is 0, consider kill completion as 100%
    df_final.loc[df_final['Required Kills'] == 0, 'Kills Completion'] = 100

    df_final['Deads Completion'] = (df_final['Deads Change'] / df_final['Required Deaths'] * 100).replace(
        [np.inf, -np.inf], 0).fillna(0)
    # If Required Deaths is 0, consider death completion as 100%
    df_final.loc[df_final['Required Deaths'] == 0, 'Deads Completion'] = 100

    # Rank players by DKP in descending order (highest DKP = Rank 1)
    df_final['Rank'] = df_final['DKP'].rank(ascending=False, method='min').astype(int)

    # Use governor name from 'after' snapshot, fill missing names with 'Unknown Governor'
    df_final['Governor Name'] = df_final['Governor Name_after'].fillna('Unknown Governor')

    # Set matchmaking_power to the power from the 'after' snapshot
    df_final['matchmaking_power'] = df_final['Power_after']

    # Define the final set of columns for the output DataFrame
    final_cols = [
        'Governor ID', 'Governor Name', 'matchmaking_power', 'Power_at_KVK_start',
        'Kill Points_before', 'Kill Points_after', 'Kills Change',
        'Deads_before', 'Deads_after', 'Deads Change',
        'Power_before', 'Power_after', 'Power Change',
        'Tier 4 Kills_before', 'Tier 4 Kills_after', 'Tier 4 Kills Change',
        'Tier 5 Kills_before', 'Tier 5 Kills_after', 'Tier 5 Kills Change',
        'Total Kills T4+T5 Change', 'Required Kills', 'Required Deaths',
        'DKP', 'Kills Completion', 'Deads Completion', 'Rank'
    ]
    # Filter 'final_cols' to include only columns that actually exist in 'df_final'
    final_cols = [col for col in final_cols if col in df_final.columns]
    df_final = df_final[final_cols]

    # Convert float columns to integer type if all values are whole numbers
    for col in df_final.columns:
        if pd.api.types.is_float_dtype(df_final[col]):
            # Check that all non-NaN values are equal to their integer conversion
            if (df_final[col].dropna() == df_final[col].dropna().astype(int)).all():
                df_final.loc[:, col] = df_final[col].astype(int)

    # Ensure Governor ID is of string type for consistent display/usage
    df_final['Governor ID'] = df_final['Governor ID'].astype(str)

    logger.info(f"Final DataFrame shape before saving: {df_final.shape}")
    if df_final.empty:
        logger.warning("Final DataFrame is empty. No data to save to 'results.xlsx'.")
        return pd.DataFrame()

    # Save the processed data to the specified output file
    try:
        # Create the 'results' directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Ensured output directory '{output_dir}' exists.")
        df_final.to_excel(output_file, index=False)
        logger.info(f"Processed data successfully saved to {output_file}")
    except Exception as e:
        logger.error(f"Error saving processed data to {output_file}: {e}")
        return pd.DataFrame()

    logger.info("Overall KVK statistics successfully processed.")
    return df_final


def calculate_period_stats(start_file_path: str, end_file_path: str):
    """
    Calculates statistics for a specific period (e.g., zone, altar) between two snapshot files.
    The main player list is strictly determined by 'kvk_start_power.xlsx' from the project root directory.
    Only players present in 'kvk_start_power.xlsx' AND in BOTH start_file_path and end_file_path are included.
    'start_file_path' and 'end_file_path' must be full paths, including the period folder.
    """
    logger.info(
        f"Starting data processing for period: {os.path.basename(start_file_path)} -> {os.path.basename(end_file_path)}")

    # Get the absolute path to the directory of the current script (calculator.py)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Determine the project root directory where 'kvk_start_power.xlsx' is located
    project_root = os.path.abspath(os.path.join(script_dir, os.pardir))

    # --- DEBUG OUTPUTS ---
    print(f"DEBUG (calculate_period_stats): Script directory: {script_dir}")
    print(f"DEBUG (calculate_period_stats): Project root directory: {project_root}")
    print(f"DEBUG (calculate_period_stats): Received start_file_path: {start_file_path}")
    print(f"DEBUG (calculate_period_stats): Received end_file_path: {end_file_path}")
    # --- END DEBUG OUTPUTS ---

    # Path to the main KVK start power file (located in the project root directory)
    start_kvk_power_file = os.path.join(project_root, 'kvk_start_power.xlsx')

    # --- DEBUG OUTPUTS ---
    print(f"DEBUG (calculate_period_stats): Looking for main KVK power file at: {start_kvk_power_file}")
    # --- END DEBUG OUTPUTS ---

    # Check for the existence of critical input files for period calculation
    if not os.path.exists(start_kvk_power_file):
        logger.error(
            f"Critical error: KVK start power file '{os.path.basename(start_kvk_power_file)}' not found. Cannot calculate period statistics based on the main player list.")
        return pd.DataFrame()
    if not os.path.exists(start_file_path):
        logger.error(
            f"Critical error: Period start file '{os.path.basename(start_file_path)}' not found. Cannot calculate period statistics.")
        return pd.DataFrame()
    if not os.path.exists(end_file_path):
        logger.error(
            f"Critical error: Period end file '{os.path.basename(end_file_path)}' not found. Cannot calculate period statistics.")
        return pd.DataFrame()

    try:
        # Load the main player list from kvk_start_power.xlsx
        df_master_players = pd.read_excel(start_kvk_power_file)
        logger.info(
            f"File '{os.path.basename(start_kvk_power_file)}' (main player list) successfully loaded for period statistics. Shape: {df_master_players.shape}")
        # Load period start and end snapshot files
        df_start = pd.read_excel(start_file_path)
        logger.info(f"File '{os.path.basename(start_file_path)}' successfully loaded. Shape: {df_start.shape}")
        df_end = pd.read_excel(end_file_path)
        logger.info(f"File '{os.path.basename(end_file_path)}' successfully loaded. Shape: {df_end.shape}")
    except Exception as e:
        logger.error(f"Error loading Excel files for period statistics or main player list: {e}")
        return pd.DataFrame()

    # Standardize column names in all loaded DataFrames
    for df_item in [df_master_players, df_start, df_end]:
        if not df_item.empty:
            df_item.columns = [col.strip() for col in df_item.columns]

    # Ensure 'Governor ID' column is of string type in all relevant DataFrames for reliable merging
    df_master_players['Governor ID'] = df_master_players['Governor ID'].astype(str)
    df_start['Governor ID'] = df_start['Governor ID'].astype(str)
    df_end['Governor ID'] = df_end['Governor ID'].astype(str)

    # Get unique Governor IDs from the main player list (kvk_start_power.xlsx)
    master_player_ids = df_master_players['Governor ID'].unique()
    logger.info(
        f"Main player list from '{os.path.basename(start_kvk_power_file)}' contains {len(master_player_ids)} players.")

    # Filter period start and end DataFrames to include ONLY players present in the master list.
    df_start_filtered = df_start[df_start['Governor ID'].isin(master_player_ids)].copy()
    df_end_filtered = df_end[df_end['Governor ID'].isin(master_player_ids)].copy()
    logger.info(
        f"File '{os.path.basename(start_file_path)}' filtered (based on master list): {len(df_start_filtered)} players (from original {len(df_start)})")
    logger.info(
        f"File '{os.path.basename(end_file_path)}' filtered (based on master list): {len(df_end_filtered)} players (from original {len(df_end)})")

    # Define column renames for period files
    period_renamed_cols = {
        'Kill Points': 'Kill Points', 'Очки Убийств': 'Kill Points',
        'Dead Troops': 'Deads', 'Deaths': 'Deads',
        'Погибшие войска': 'Deads', 'Смерти': 'Deads',
        'Deads': 'Deads',  # Exact name from user
        'T4 Kills': 'Tier 4 Kills', 'Убийства Т4': 'Tier 4 Kills',
        'Tier 4 Kills': 'Tier 4 Kills',  # Exact name from user
        'T5 Kills': 'Tier 5 Kills', 'Убийства Т5': 'Tier 5 Kills',
        'Tier 5 Kills': 'Tier 5 Kills',  # Exact name from user
        'Power': 'Power', 'Мощь': 'Power',
        'Governor Name': 'Governor Name', 'Имя Губернатора': 'Governor Name'
    }

    # Rename columns in filtered start and end period DataFrames
    def create_valid_rename_map(df, rename_dict):
        return {k: v for k, v in rename_dict.items() if k in df.columns}

    df_start_filtered = df_start_filtered.rename(
        columns=create_valid_rename_map(df_start_filtered, period_renamed_cols))
    df_end_filtered = df_end_filtered.rename(columns=create_valid_rename_map(df_end_filtered, period_renamed_cols))

    # Now perform an INNER merge between the filtered start and end snapshots.
    # This ensures that only players present in the master list AND in BOTH period snapshots are included.
    df_merged = pd.merge(df_end_filtered, df_start_filtered, on='Governor ID', suffixes=('_end', '_start'), how='inner')
    logger.info(
        f"Inner merge for period after master list filtering. Common players (present in master, '{os.path.basename(start_file_path)}' AND '{os.path.basename(end_file_path)}'): {len(df_merged)}")

    if df_merged.empty:
        logger.warning(
            f"No common players found for period statistics after applying '{os.path.basename(start_kvk_power_file)}' filter and inner merge. Check 'Governor ID' column for matches across all relevant files.")
        return pd.DataFrame()

    # Fill NaN values in numeric columns (e.g., if a metric was missing for a player in a snapshot) with zeros.
    numeric_cols = ['Power', 'Kill Points', 'Deads', 'Tier 4 Kills', 'Tier 5 Kills']
    for col in numeric_cols:
        if f'{col}_start' in df_merged.columns:
            df_merged[f'{col}_start'] = pd.to_numeric(df_merged[f'{col}_start'], errors='coerce').fillna(0)
        if f'{col}_end' in df_merged.columns:
            df_merged[f'{col}_end'] = pd.to_numeric(df_merged[f'{col}_end'], errors='coerce').fillna(0)

    # Determine Governor Name: prefer name from '_end' snapshot, if missing use '_start', then 'Unknown Governor'.
    df_merged['Governor Name'] = df_merged['Governor Name_end'].fillna(df_merged['Governor Name_start']).fillna(
        'Unknown Governor')

    # Calculate metric changes for this period
    df_merged['Kills Change'] = df_merged['Kill Points_end'] - df_merged['Kill Points_start']
    df_merged['Deads Change'] = df_merged['Deads_end'] - df_merged['Deads_start']

    df_merged['Power Change'] = df_merged['Power_end'] - df_merged['Power_start']
    df_merged['Tier 4 Kills Change'] = df_merged['Tier 4 Kills_end'] - df_merged['Tier 4 Kills_start']
    df_merged['Tier 5 Kills Change'] = df_merged['Tier 5 Kills_end'] - df_merged['Tier 5 Kills_start']
    df_merged['Total Kills T4+T5 Change'] = df_merged['Tier 4 Kills Change'] + df_merged['Tier 5 Kills Change']

    # Calculate DKP (consistent with overall KVK statistics)
    df_merged['DKP'] = (
            (df_merged['Deads Change'] * 15) +  # Зміна смертей
            (df_merged['Tier 5 Kills Change'] * 10) +  # Зміна T5 вбивств
            (df_merged['Tier 4 Kills Change'] * 4)  # Зміна T4 вбивств
    )

    # Rank players by DKP for the period
    df_merged['Rank'] = df_merged['DKP'].rank(ascending=False, method='min').astype(int)

    # Select and rename columns for the final period DataFrame output
    period_df = df_merged[[
        'Governor ID', 'Governor Name',
        'Power_start', 'Power_end', 'Power Change',
        'Kill Points_start', 'Kill Points_end', 'Kills Change',
        'Deads_start', 'Deads_end', 'Deads Change',
        'Tier 4 Kills_start', 'Tier 4 Kills_end', 'Tier 4 Kills Change',
        'Tier 5 Kills_start', 'Tier 5 Kills_end', 'Tier 5 Kills Change',
        'Total Kills T4+T5 Change', 'DKP', 'Rank'
    ]].copy()

    # Rename 'Power_end' to 'Power_after' for consistency in output naming
    period_df.rename(columns={'Power_end': 'Power_after'}, inplace=True)

    # Debug log for a sample player to verify period calculations
    if not period_df.empty:
        if 'Governor ID' in period_df.columns and not period_df['Governor ID'].empty:
            sample_player_id = period_df['Governor ID'].iloc[0]
            sample_player = period_df[period_df['Governor ID'] == sample_player_id].iloc[0]
            logger.debug(f"DEBUGGING {sample_player_id} (Period Stats Raw Data):")
            logger.debug(
                f"   Period: {os.path.basename(start_file_path).split('.')[0]} -> {os.path.basename(end_file_path).split('.')[0]}")
            logger.debug(
                f"   Power_start: {sample_player['Power_start']:.1f}, Power_end: {sample_player['Power_after']:.1f}, Power Change: {sample_player['Power Change']:.1f}")
            logger.debug(
                f"   KP_start: {sample_player['Kill Points_start']:.1f}, KP_end: {sample_player['Kill Points_end']:.1f}, Kills Change: {sample_player['Kills Change']:.1f}")
            logger.debug(
                f"   Deads_start: {sample_player['Deads_start']:.1f}, Deads_end: {sample_player['Deads_end']:.1f}, Deads Change: {sample_player['Deads Change']:.1f}")
            logger.debug(
                f"   T4_start: {sample_player['Tier 4 Kills_start']:.1f}, T4_end: {sample_player['Tier 4 Kills_end']:.1f}, T4 Change: {sample_player['Tier 4 Kills Change']:.1f}")
            logger.debug(
                f"   T5_start: {sample_player['Tier 5 Kills_start']:.1f}, T5_end: {sample_player['Tier 5 Kills_end']:.1f}, T5 Change: {sample_player['Tier 5 Kills Change']:.1f}")
            logger.debug(f"   Total T4+T5 Change: {sample_player['Total Kills T4+T5 Change']:.1f}")
        else:
            logger.warning(
                "Period DataFrame is not empty but 'Governor ID' column is missing or empty. Skipping debug log.")

    logger.info("Period data processing completed.")
    return period_df


def get_player_stats(df: pd.DataFrame, player_id: str):
    """
    Extracts statistics for a specific player from a DataFrame.
    """
    player_id = str(player_id).strip()  # Ensure ID is a string and stripped of whitespace
    player_data = df[df['Governor ID'] == player_id]

    if player_data.empty:
        logger.warning(f"Player with ID {player_id} not found in the main DataFrame.")
        return None

    player = player_data.iloc[0]  # Get the first (and only) row for the player

    # Return player statistics as a dictionary
    return {
        'governor_id': player.get('Governor ID'),
        'governor_name': player.get('Governor Name'),
        'matchmaking_power': player.get('matchmaking_power'),
        'power_change': player.get('Power Change'),
        'kills_change': player.get('Kills Change'),
        'deads_change': player.get('Deads Change'),
        'total_t4_t5_kills_change': player.get('Total Kills T4+T5 Change'),
        'tier4_kills_change': player.get('Tier 4 Kills Change'),
        'tier5_kills_change': player.get('Tier 5 Kills Change'),
        'required_kills': player.get('Required Kills'),
        'required_deaths': player.get('Required Deaths'),
        'total_kills': player.get('Kill Points_after'),  # Total kills at the end of KVK/period
        'total_deaths': player.get('Deads_after'),  # Total deaths at the end of KVK/period
        'dkp': player.get('DKP'),
        'kills_completion': player.get('Kills Completion'),
        'deads_completion': player.get('Deads Completion'),
        'rank': player.get('Rank')
    }
