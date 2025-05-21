import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os

def create_dual_semi_circular_progress(kill_progress_percent, death_progress_percent, filename='dual_progress_chart.png'):
    fig, ax = plt.subplots(figsize=(6, 3), facecolor='#222222')
    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-0.6, 1.1)
    ax.axis('off')

    center = (0, 0)
    theta1 = 0
    theta2 = 180

    radius_outer = 1.0
    background = patches.Arc(center, radius_outer * 2, radius_outer * 2, angle=0, theta1=theta1, theta2=theta2,
                             linewidth=12, color='#555555', alpha=0.7)
    ax.add_patch(background)

    radius_inner_kills = 0.8
    angle_kills = theta1 + (theta2 - theta1) * (min(kill_progress_percent, 100) / 100)
    kills_progress = patches.Arc(center, radius_inner_kills * 2, radius_inner_kills * 2, angle=0, theta1=theta1, theta2=angle_kills,
                                  linewidth=12, color='#D4AF37', alpha=0.8)
    ax.add_patch(kills_progress)

    radius_middle_deaths = 0.9
    angle_deaths = theta1 + (theta2 - theta1) * (min(death_progress_percent, 100) / 100)
    deaths_progress = patches.Arc(center, radius_middle_deaths * 2, radius_middle_deaths * 2, angle=0, theta1=theta1, theta2=angle_deaths,
                                   linewidth=12, color='#E879F9', alpha=0.8)
    ax.add_patch(deaths_progress)

    ax.text(-0.5, -0.2, f'Kills: {kill_progress_percent:.0f}%', ha='center', va='center', fontsize=12, color='#D4AF37')
    ax.text(0.5, -0.2, f'Deaths: {death_progress_percent:.0f}%', ha='center', va='center', fontsize=12, color='#E879F9')
    ax.text(0, 0.3, 'Progress', ha='center', va='center', fontsize=14, color='#AAAAAA')

    plt.gca().set_aspect('equal', adjustable='box')
    plt.savefig(filename, transparent=True)
    plt.close(fig) # Закриваємо фігуру, щоб уникнути витоків пам'яті
    return filename