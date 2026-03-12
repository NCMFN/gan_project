import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

plt.rcParams.update({
    'font.size': 11,
    'axes.titlesize': 13,
    'axes.labelsize': 11,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'figure.dpi': 300,
    'savefig.dpi': 300
})

def draw_box(ax, text, xy, width, height, facecolor='#fffcdb', edgecolor='#d4c27b'):
    box = mpatches.FancyBboxPatch(xy, width, height,
                                  boxstyle="round,pad=0.1",
                                  fc=facecolor, ec=edgecolor, lw=2.0)
    ax.add_patch(box)
    ax.text(xy[0] + width / 2., xy[1] + height / 2., text,
            ha='center', va='center', color='black', fontsize=12, fontweight='bold', wrap=True)
    return box

def draw_arrow(ax, start, end, shrink=0):
    # Adjust start and end to shrink the arrow slightly
    dx = end[0] - start[0]
    dy = end[1] - start[1]

    arrow = mpatches.FancyArrowPatch(posA=start, posB=end,
                                     arrowstyle='-|>', mutation_scale=20,
                                     color='#666666', lw=2.0, shrinkA=shrink, shrinkB=shrink)
    ax.add_patch(arrow)

def create_diagram():
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_xlim(0, 100)
    ax.set_ylim(-5, 100)
    ax.axis('off')

    # Dimensions for boxes
    bw, bh = 40, 8

    # Box coordinates (bottom-left xy)
    nodes = {
        'A': {'text': 'Data Sources\n(Google Drive)', 'xy': (30, 90)},
        'B': {'text': 'Data Ingestion &\nTimestamp Normalization', 'xy': (30, 79)},
        'C': {'text': 'Data Integration', 'xy': (30, 68)},
        'D': {'text': 'Feature Engineering', 'xy': (30, 57)},

        'E': {'text': 'EDA Visualizations', 'xy': (5, 46)},
        'F': {'text': 'Train/Test Split\n(80/20, time-ordered)', 'xy': (55, 46)},

        'G': {'text': 'Model Training', 'xy': (55, 35)},

        'I': {'text': 'Evaluation &\nDiagnostics', 'xy': (5, 24)},
        'H': {'text': 'Inference Pipeline', 'xy': (55, 24)},
    }

    # Draw nodes
    for k, v in nodes.items():
        draw_box(ax, v['text'], v['xy'], bw, bh)

    # Function to get center top, bottom, left, right of a box
    def get_center(node, side='bottom'):
        x, y = nodes[node]['xy']
        if side == 'bottom':
            return (x + bw / 2, y)
        elif side == 'top':
            return (x + bw / 2, y + bh)
        elif side == 'left':
            return (x, y + bh / 2)
        elif side == 'right':
            return (x + bw, y + bh / 2)

    # Edges
    # A -> B
    draw_arrow(ax, get_center('A', 'bottom'), get_center('B', 'top'), shrink=2)
    # B -> C
    draw_arrow(ax, get_center('B', 'bottom'), get_center('C', 'top'), shrink=2)
    # C -> D
    draw_arrow(ax, get_center('C', 'bottom'), get_center('D', 'top'), shrink=2)

    # D -> E
    start_D_bottom = get_center('D', 'bottom')
    end_E_top = get_center('E', 'top')
    # Use a custom start point offset for branching
    draw_arrow(ax, (start_D_bottom[0]-5, start_D_bottom[1]), end_E_top, shrink=2)

    # D -> F
    end_F_top = get_center('F', 'top')
    draw_arrow(ax, (start_D_bottom[0]+5, start_D_bottom[1]), end_F_top, shrink=2)

    # F -> G
    draw_arrow(ax, get_center('F', 'bottom'), get_center('G', 'top'), shrink=2)

    # F -> I (Evaluation)
    start_F_left = get_center('F', 'left')
    end_I_top = get_center('I', 'top')
    draw_arrow(ax, start_F_left, (end_I_top[0]+5, end_I_top[1]), shrink=2)

    # G -> I
    start_G_left = get_center('G', 'left')
    end_I_right = get_center('I', 'right')
    draw_arrow(ax, start_G_left, end_I_right, shrink=2)

    # G -> H
    draw_arrow(ax, get_center('G', 'bottom'), get_center('H', 'top'), shrink=2)

    # C -> H (Data Integration -> Inference Pipeline)
    start_C_right = get_center('C', 'right')
    end_H_right = get_center('H', 'right')
    # Path with waypoints
    # We can fake it with an arrow that goes right, down, then left
    # But FancyArrowPatch is straight. Let's use matplotlib plot for the elbow and an arrow at the end
    ax.plot([start_C_right[0], 98], [start_C_right[1], start_C_right[1]], color='#666666', lw=2.0)
    ax.plot([98, 98], [start_C_right[1], end_H_right[1]], color='#666666', lw=2.0)
    draw_arrow(ax, (98, end_H_right[1]), (end_H_right[0] + 0.5, end_H_right[1]), shrink=2)

    plt.tight_layout()
    plt.savefig('ml_pipeline_architecture.png', bbox_inches='tight')

if __name__ == '__main__':
    create_diagram()
