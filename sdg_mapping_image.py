import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.font_manager import FontProperties

plt.rcParams.update({
    'font.size': 11,
    'axes.titlesize': 13,
    'axes.labelsize': 11,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'figure.dpi': 300,
    'savefig.dpi': 300
})

# Set up the figure and axes
fig, ax = plt.subplots(figsize=(12, 16))
ax.set_xlim(0, 12)
ax.set_ylim(0, 18)
ax.axis('off')

# Define colors
color_title_bg = '#003366'
color_blue_box = '#E6F0FF'
color_light_blue_box = '#F0F8FF'
color_green_box = '#E6FFE6'
color_orange_box = '#FFF0E6'
color_dark_blue = '#003366'
color_green = '#006600'
color_orange = '#FF6600'
color_arrow = '#666666'

# Define font properties (without color)
font_title = FontProperties(family='Arial', weight='bold', size=16)
font_subtitle = FontProperties(family='Arial', weight='bold', size=14)
font_box_title = FontProperties(family='Arial', weight='bold', size=12)
font_label = FontProperties(family='Arial', size=10)

# Helper function to draw a rounded rectangle
def draw_box(x, y, width, height, color, edgecolor='none', alpha=1, corner_radius=0.5):
    rect = patches.FancyBboxPatch((x, y), width, height, boxstyle=f"round,pad=0,rounding_size={corner_radius}", facecolor=color, edgecolor=edgecolor, alpha=alpha)
    ax.add_patch(rect)

# Helper function to draw an arrow
def draw_arrow(x_start, y_start, x_end, y_end, color=color_arrow, width=0.1):
    ax.annotate("", xy=(x_end, y_end), xytext=(x_start, y_start), arrowprops=dict(arrowstyle="->", color=color, lw=2, shrinkA=0, shrinkB=0))

# --- Title Bar ---
draw_box(0, 17, 12, 1, color_title_bg, corner_radius=0)
ax.text(6, 17.5, "Mapping Indigenous Problems to SDGs:", ha='center', va='center', fontproperties=font_title, color='white')
ax.text(6, 17.2, "Solution Roadmap", ha='center', va='center', fontproperties=font_subtitle, color='white')

# --- Community Data Collection ---
draw_box(1, 14.5, 10, 2, color_blue_box)
ax.text(6, 16.2, "Community Data Collection", ha='center', va='center', fontproperties=font_box_title, color=color_dark_blue)

# Icons and labels for Community Data Collection
ax.text(2, 15.5, "🏠", ha='center', va='center', size=20, color=color_dark_blue)
ax.text(2, 14.8, "Local NGOs & Reports", ha='center', va='center', fontproperties=font_label, color=color_dark_blue)

ax.text(6, 15.5, "👥", ha='center', va='center', size=20, color=color_dark_blue)
ax.text(6, 14.8, "Community Surveys", ha='center', va='center', fontproperties=font_label, color=color_dark_blue)

ax.text(10, 15.5, "📜", ha='center', va='center', size=20, color=color_dark_blue)
ax.text(10, 14.8, "Traditional Knowledge", ha='center', va='center', fontproperties=font_label, color=color_dark_blue)

# Arrow 1
draw_arrow(6, 14.5, 6, 13.5)

# --- Data Preprocessing & Normalization ---
draw_box(1, 11.5, 10, 2, color_light_blue_box)
ax.text(6, 13.2, "Data Preprocessing & Normalization", ha='center', va='center', fontproperties=font_box_title, color=color_dark_blue)

# Icons and labels for Data Preprocessing
ax.text(3, 12.5, "📄", ha='center', va='center', size=20, color=color_dark_blue)
ax.text(3, 11.8, "Text Cleaning & Parsing", ha='center', va='center', fontproperties=font_label, color=color_dark_blue)

draw_arrow(5, 12.2, 7, 12.2, width=0.05)

ax.text(9, 12.5, "🗣️", ha='center', va='center', size=20, color=color_dark_blue)
ax.text(9, 11.8, "Language Processing", ha='center', va='center', fontproperties=font_label, color=color_dark_blue)

# Arrow 2
draw_arrow(6, 11.5, 6, 10.5)

# --- RoBERTa-Large SDG Classification ---
draw_box(2, 9, 8, 1.5, color_blue_box)
ax.text(6, 10.1, "RoBERTa-Large SDG Classification", ha='center', va='center', fontproperties=font_box_title, color=color_dark_blue)
ax.text(6, 9.5, "Multi-Label AI Model", ha='center', va='center', fontproperties=font_label, color=color_dark_blue)
ax.text(3.5, 9.8, "🧠", ha='center', va='center', size=25, color=color_dark_blue) # Placeholder for brain icon

# Arrow 3
draw_arrow(6, 9, 6, 8)

# --- Parallel Processes ---
# Automated SDG Mapping
draw_box(0.5, 5.5, 3.5, 2.5, color_green_box)
ax.text(2.25, 7.7, "Automated SDG Mapping", ha='center', va='center', fontproperties=font_box_title, color=color_green)
ax.text(2.25, 7.0, "🎯 SDG Tagging", ha='center', va='center', fontproperties=font_label, color=color_green)
ax.text(2.25, 6.3, "⚠️ Conflict Detection", ha='center', va='center', fontproperties=font_label, color=color_orange)

# Coherence & Gap Analysis
draw_box(4.5, 5.5, 3, 2.5, color_orange_box)
ax.text(6, 7.7, "Coherence & Gap Analysis", ha='center', va='center', fontproperties=font_box_title, color=color_orange)
ax.text(6, 7.0, "⚖️ Pillar Balance Score", ha='center', va='center', fontproperties=font_label, color=color_orange)
ax.text(6, 6.3, "🔍 Gap Identification", ha='center', va='center', fontproperties=font_label, color=color_orange)

# Solution Framework Generation
draw_box(8, 5.5, 3.5, 2.5, color_green_box)
ax.text(9.75, 7.7, "Solution Framework Generation", ha='center', va='center', fontproperties=font_box_title, color=color_green)
ax.text(9.75, 7.0, "🤖 AI Recommender Systems", ha='center', va='center', fontproperties=font_label, color=color_green)
ax.text(9.75, 6.3, "💡 Solution & Action Plans", ha='center', va='center', fontproperties=font_label, color=color_green)
ax.text(9.75, 5.8, "⚙️ Custom Scenarios", ha='center', va='center', fontproperties=font_label, color=color_green)

# Horizontal Arrows between parallel boxes
draw_arrow(3.5, 6.75, 4.5, 6.75)
draw_arrow(7.5, 6.75, 8, 6.75)

# Arrows down to Policy Recommendations
draw_arrow(2.25, 5.5, 2.25, 4.5)
draw_arrow(6, 5.5, 6, 4.5)
draw_arrow(9.75, 5.5, 9.75, 4.5)

# --- Policy Recommendations ---
draw_box(1, 1.5, 10, 3, color_blue_box)
ax.text(6, 4.1, "Policy Recommendations", ha='center', va='center', fontproperties=font_box_title, color=color_dark_blue)

# Icons and labels for Policy Recommendations
ax.text(3, 3.3, "📊", ha='center', va='center', size=20, color=color_dark_blue)
ax.text(3, 2.6, "Interactive Dashboard", ha='center', va='center', fontproperties=font_label, color=color_dark_blue)
draw_box(2, 1.7, 2, 0.5, color_dark_blue, corner_radius=0.1)
ax.text(3, 1.95, "SDG Insights & Maps", ha='center', va='center', fontproperties=font_label, color='white', size=8)

ax.text(6, 3.3, "📝", ha='center', va='center', size=20, color=color_dark_blue)
ax.text(6, 2.6, "Policy Briefs", ha='center', va='center', fontproperties=font_label, color=color_dark_blue)
draw_box(5, 1.7, 2, 0.5, color_dark_blue, corner_radius=0.1)
ax.text(6, 1.95, "Actionable Solutions", ha='center', va='center', fontproperties=font_label, color='white', size=8)

ax.text(9, 3.3, "🗣️", ha='center', va='center', size=20, color=color_dark_blue)
ax.text(9, 2.6, "Engage Communities", ha='center', va='center', fontproperties=font_label, color=color_dark_blue)
draw_box(8, 1.7, 2, 0.5, color_dark_blue, corner_radius=0.1)
ax.text(9, 1.95, "Local Feedback", ha='center', va='center', fontproperties=font_label, color='white', size=8)

plt.savefig('sdg_mapping_chart.png', bbox_inches='tight', dpi=300)
