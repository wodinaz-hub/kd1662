import pandas as pd

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