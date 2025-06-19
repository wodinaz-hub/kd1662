import discord
import math
import os
import logging
import pandas as pd
import numpy as np

# Configure logging for this module
logger = logging.getLogger(__name__)


def format_number_custom(num_value):
    """
    Formats a number with a dot as the thousand separator and a comma for decimals.
    Handles standard int/float and numpy.int64/numpy.float64.
    If the number is an integer, it returns it without decimal places.
    """
    if pd.isna(num_value):
        return "N/A"

    if not isinstance(num_value, (int, float, np.int64, np.float64)):
        logger.debug(f"format_number_custom: Received non-numeric value: {num_value} ({type(num_value)})")
        return str(num_value)

    # Convert numpy types to standard Python int/float
    if isinstance(num_value, np.int64):
        num_value = int(num_value)
    elif isinstance(num_value, np.float64):
        num_value = float(num_value)

    # Check if the number is an integer by value
    if float(num_value).is_integer():
        # Format as integer with comma thousands separator, then replace comma with dot
        num_str = f"{int(num_value):,}".replace(",", ".")
    else:
        # Format as float with comma thousands separator and dot decimal separator (default behavior)
        # Then swap them using a temporary placeholder to get dot for thousands, comma for decimals
        formatted_default = f"{num_value:,.2f}"  # Example: 12345.67 -> "12,345.67"
        num_str = formatted_default.replace(",", "TEMP_THOUSAND_SEP").replace(".", ",").replace("TEMP_THOUSAND_SEP",
                                                                                                ".")
    return num_str


def create_embed(title: str, description: str = "", color: int = 0x000000) -> discord.Embed:
    """Creates a Discord Embed object."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    # embed.set_footer(text="RoK Bot by YourName") # Optional footer
    return embed


def create_progress_bar(percent: float, length: int = 20) -> str:
    """
    Creates a Unicode progress bar string using the user's preferred format.
    Args:
        percent (float): The percentage to display.
        length (int): The total length of the progress bar.
    Returns:
        str: The formatted progress bar string.
    """
    filled_length = int(length * percent // 100)
    bar = '█' * filled_length + '-' * (length - filled_length)
    return f'[{bar}] {percent:.0f}%'

