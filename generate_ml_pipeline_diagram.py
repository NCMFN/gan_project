import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.path as mpath

from PIL import Image

# Apply requested matplotlib configuration
plt.rcParams.update({
    'font.size': 11,
    'axes.titlesize': 13,
    'axes.labelsize': 11,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'figure.dpi': 300,
    'savefig.dpi': 300,
    'font.family': 'sans-serif',
    'font.sans-serif': ['DejaVu Sans', 'Helvetica', 'Arial'], # Fallback
    'pdf.fonttype': 42, # Embed TrueType fonts in PDF for Overleaf clarity
    'ps.fonttype': 42
})

def create_ml_pipeline_diagram():
    fig, ax = plt.subplots(figsize=(16, 6))
    ax.set_axis_off()

    # Define minimal, professional colors
    colors = {
        'bg_data': '#EAF2F8',
        'border_data': '#2874A6',
        'bg_prep': '#EAF2F8',
        'border_prep': '#2874A6',
        'bg_eda': '#FCF3CF',
        'border_eda': '#F1C40F',
        'bg_split': '#D5F5E3',
        'border_split': '#239B56',
        'bg_model': '#E8F8F5',
        'border_model': '#17A589',
        'bg_deploy': '#F5EEF8',
        'border_deploy': '#8E44AD',
        'cluster_border': '#85929E',
        'arrow': '#5D6D7E',
        'text': '#1C2833'
    }

    # Define node positions (X, Y) centers
    nodes = {
        'A': {'pos': (1.5, 3), 'text': 'Data Sources\n(Google Drive)', 'type': 'data', 'w': 2.5, 'h': 1.0},
        'B': {'pos': (5.0, 3), 'text': 'Data Ingestion &\nTimestamp Normalization', 'type': 'prep', 'w': 3.0, 'h': 1.0},
        'C': {'pos': (8.5, 3), 'text': 'Data Integration', 'type': 'prep', 'w': 2.5, 'h': 1.0},
        'D': {'pos': (11.5, 3), 'text': 'Feature Engineering', 'type': 'prep', 'w': 2.5, 'h': 1.0},
        'E': {'pos': (11.5, 5.0), 'text': 'EDA Visualizations', 'type': 'eda', 'w': 2.5, 'h': 1.0},
        'F': {'pos': (5.0, 1), 'text': 'Train/Test Split\n(80/20, time-ordered)', 'type': 'split', 'w': 2.5, 'h': 1.0},
        'G': {'pos': (8.5, 1), 'text': 'Model Training', 'type': 'model', 'w': 2.5, 'h': 1.0},
        'I': {'pos': (11.5, 1), 'text': 'Evaluation &\nDiagnostics', 'type': 'model', 'w': 2.5, 'h': 1.0},
        'H': {'pos': (14.5, 1), 'text': 'Inference Pipeline', 'type': 'deploy', 'w': 2.5, 'h': 1.0}
    }

    def draw_node(key, node):
        x, y = node['pos']
        w, h = node['w'], node['h']

        if node['type'] == 'data': bg, border = colors['bg_data'], colors['border_data']
        elif node['type'] == 'prep': bg, border = colors['bg_prep'], colors['border_prep']
        elif node['type'] == 'eda': bg, border = colors['bg_eda'], colors['border_eda']
        elif node['type'] == 'split': bg, border = colors['bg_split'], colors['border_split']
        elif node['type'] == 'model': bg, border = colors['bg_model'], colors['border_model']
        elif node['type'] == 'deploy': bg, border = colors['bg_deploy'], colors['border_deploy']
        else: bg, border = 'white', 'black'

        box = patches.FancyBboxPatch(
            (x - w/2, y - h/2), w, h,
            boxstyle="round,pad=0.1,rounding_size=0.15",
            ec=border, fc=bg, lw=1.5, zorder=3
        )
        ax.add_patch(box)

        ax.text(x, y, node['text'], ha='center', va='center',
                color=colors['text'], fontsize=11, zorder=4, weight='normal')

    for key, node in nodes.items():
        draw_node(key, node)

    def draw_arrow(start_key, end_key, style='solid'):
        start_pos = nodes[start_key]['pos']
        end_pos = nodes[end_key]['pos']

        sx, sy = start_pos
        ex, ey = end_pos

        if sy == ey:
            if ex > sx:
                sx += nodes[start_key]['w']/2 + 0.1
                ex -= nodes[end_key]['w']/2 + 0.1
            else:
                sx -= nodes[start_key]['w']/2 + 0.1
                ex += nodes[end_key]['w']/2 + 0.1
            ax.annotate('', xy=(ex, ey), xytext=(sx, sy),
                        arrowprops=dict(arrowstyle="->", color=colors['arrow'], lw=1.5, ls=style), zorder=2)
        elif sx == ex:
            if ey > sy:
                sy += nodes[start_key]['h']/2 + 0.1
                ey -= nodes[end_key]['h']/2 + 0.1
            else:
                sy -= nodes[start_key]['h']/2 + 0.1
                ey += nodes[end_key]['h']/2 + 0.1
            ax.annotate('', xy=(ex, ey), xytext=(sx, sy),
                        arrowprops=dict(arrowstyle="->", color=colors['arrow'], lw=1.5, ls=style), zorder=2)

    draw_arrow('A', 'B')
    draw_arrow('B', 'C')
    draw_arrow('C', 'D')

    draw_arrow('F', 'G')
    draw_arrow('G', 'I')
    draw_arrow('I', 'H')  # Fixed from G->H

    draw_arrow('D', 'E')

    # Custom routing for D -> F
    cx1, cy1 = nodes['D']['pos'][0], nodes['D']['pos'][1] - nodes['D']['h']/2 - 0.1
    cx2, cy2 = nodes['F']['pos'][0], nodes['F']['pos'][1] + nodes['F']['h']/2 + 0.1

    path_data = [
        (mpath.Path.MOVETO, (cx1, cy1)),
        (mpath.Path.LINETO, (cx1, 2.0)),
        (mpath.Path.LINETO, (cx2, 2.0)),
        (mpath.Path.LINETO, (cx2, cy2))
    ]
    codes, verts = zip(*path_data)
    path = mpath.Path(verts, codes)
    patch = patches.PathPatch(path, facecolor='none', edgecolor=colors['arrow'], lw=1.5, zorder=2)
    ax.add_patch(patch)
    ax.annotate('', xy=(cx2, cy2), xytext=(cx2, cy2+0.01),
                arrowprops=dict(arrowstyle="->", color=colors['arrow'], lw=1.5), zorder=2)

    # Dashed line for eval flow: F -> I
    cx1, cy1 = nodes['F']['pos'][0], nodes['F']['pos'][1] - nodes['F']['h']/2 - 0.1
    cx2, cy2 = nodes['I']['pos'][0], nodes['I']['pos'][1] - nodes['I']['h']/2 - 0.1

    path_data = [
        (mpath.Path.MOVETO, (cx1, cy1)),
        (mpath.Path.LINETO, (cx1, 0.2)),
        (mpath.Path.LINETO, (cx2, 0.2)),
        (mpath.Path.LINETO, (cx2, cy2))
    ]
    codes, verts = zip(*path_data)
    path = mpath.Path(verts, codes)
    patch = patches.PathPatch(path, facecolor='none', edgecolor='#A9DFBF', lw=1.5, ls='dashed', zorder=2)
    ax.add_patch(patch)
    ax.annotate('', xy=(cx2, cy2), xytext=(cx2, cy2-0.01),
                arrowprops=dict(arrowstyle="->", color='#A9DFBF', lw=1.5), zorder=2)


    def draw_cluster(x, y, w, h, label):
        rect = patches.Rectangle(
            (x, y), w, h, fill=False, edgecolor=colors['cluster_border'],
            lw=1.5, ls='dashed', zorder=1
        )
        ax.add_patch(rect)
        # Position label just above the top-left corner
        ax.text(x, y + h + 0.08, label, ha='left', va='bottom',
                color='#34495E', fontsize=12, weight='bold', zorder=2)

    # Data Prep Cluster
    draw_cluster(3.0, 2.2, 10.25, 1.8, 'Data Loading & Preprocessing')

    # Modeling Cluster
    draw_cluster(3.25, 0.05, 10.0, 1.8, 'Model Development')

    # Deployment Cluster
    draw_cluster(13.0, 0.05, 3.0, 1.8, 'Deployment')

    ax.set_xlim(0, 16.5)
    ax.set_ylim(-0.5, 6)
    # Remove aspect='equal' as it distorts exact positioning in inches/figure units
    # ax.set_aspect('equal', adjustable='box')

    plt.tight_layout()

    # Save PDF
    plt.savefig('DDHPC110.pdf', format='pdf', dpi=300, bbox_inches='tight', pad_inches=0.1)

    # Save PNG
    plt.savefig('DDHPC110_temp.png', format='png', dpi=300, bbox_inches='tight', pad_inches=0.1)
    plt.close()

    # Overleaf pdflatex often fails with RGBA (transparent) PNGs. Convert to RGB.
    try:
        img = Image.open('DDHPC110_temp.png')
        # Preserve original DPI info, defaulting to 300 if missing
        original_dpi = img.info.get('dpi', (300, 300))

        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            bg = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                bg.paste(img, mask=img.split()[3]) # 3 is the alpha channel
            else:
                bg.paste(img)
            bg.save('DDHPC110.png', format='png', dpi=original_dpi)
        else:
            img.save('DDHPC110.png', format='png', dpi=original_dpi)

        import os
        os.remove('DDHPC110_temp.png')
    except Exception as e:
        print(f"Error converting image format: {e}")

if __name__ == "__main__":
    create_ml_pipeline_diagram()
