import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os
import io
import logging
import pandas as pd  # Needed for pd.isna
from utils.helpers import format_number_custom  # Import the helper for number formatting

# Configure logging for this module
logger = logging.getLogger(__name__)


def create_dual_semi_circular_progress(kills_completion_pct: float, deaths_completion_pct: float,
                                       player_name: str, required_kills: float, current_kills: float,
                                       required_deaths: float, current_deaths: float) -> str:
    """
    Creates a dual semi-circular progress chart for Kills and Deaths completion.
    This version uses overlapping arcs on a single subplot and displays detailed stats.
    """
    fig, ax = plt.subplots(figsize=(6, 3), facecolor='#222222')
    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-0.6, 1.1)
    ax.axis('off')

    center = (0, 0)
    theta1 = 0
    theta2 = 180

    # Background arc (outermost)
    radius_outer = 1.0
    background = patches.Arc(center, radius_outer * 2, radius_outer * 2, angle=0, theta1=theta1, theta2=theta2,
                             linewidth=12, color='#555555', alpha=0.7)
    ax.add_patch(background)

    # Deaths progress arc (middle)
    radius_middle_deaths = 0.9
    angle_deaths = theta1 + (theta2 - theta1) * (min(deaths_completion_pct, 100) / 100)
    deaths_progress = patches.Arc(center, radius_middle_deaths * 2, radius_middle_deaths * 2, angle=0, theta1=theta1,
                                  theta2=angle_deaths,
                                  linewidth=12, color='#E879F9', alpha=0.8)  # Purple for deaths
    ax.add_patch(deaths_progress)

    # Kills progress arc (innermost)
    radius_inner_kills = 0.8
    angle_kills = theta1 + (theta2 - theta1) * (min(kills_completion_pct, 100) / 100)
    kills_progress = patches.Arc(center, radius_inner_kills * 2, radius_inner_kills * 2, angle=0, theta1=theta1,
                                 theta2=angle_kills,
                                 linewidth=12, color='#D4AF37', alpha=0.8)  # Gold for kills
    ax.add_patch(kills_progress)

    # Text labels
    # Use current_kills and required_kills directly from function arguments
    ax.text(-0.5, -0.2,
            f'Kills:\n Cur: {format_number_custom(current_kills)}\n Req:{format_number_custom(required_kills)}\n({kills_completion_pct:.0f}%)',
            ha='center', va='center', fontsize=10, color='#D4AF37')
    # Use current_deaths and required_deaths directly from function arguments
    ax.text(0.5, -0.2,
            f'Deaths:\n Cur: {format_number_custom(current_deaths)}\n Req: {format_number_custom(required_deaths)}\n({deaths_completion_pct:.0f}%)',
            ha='center', va='center', fontsize=10, color='#E879F9')

    ax.text(0, 0.3, f'{player_name}\nProgress', ha='center', va='center', fontsize=14, color='#AAAAAA')

    plt.gca().set_aspect('equal', adjustable='box')

    buf = io.BytesIO()
    try:
        plt.savefig(buf, format='png', transparent=True, bbox_inches='tight', dpi=100)
        buf.seek(0)
        plt.close(fig)  # Close the figure to free memory

        unique_filename = f"progress_chart_{os.urandom(4).hex()}.png"
        file_path = os.path.join(os.getcwd(), unique_filename)
        with open(file_path, 'wb') as f:
            f.write(buf.getvalue())
        logger.debug(f"Chart saved to {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Error creating or saving chart: {e}", exc_info=True)
        plt.close(fig)
        return None

