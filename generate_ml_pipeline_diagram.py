import graphviz

def create_diagram():
    dot = graphviz.Digraph(comment='High-Level ML Pipeline', format='png')
    dot.attr(rankdir='TB', splines='ortho', nodesep='1.2', ranksep='1.0', dpi='600')
    dot.attr('node', shape='box', style='filled,rounded', fillcolor='#fffcdb',
             color='#d4c27b', fontname='Helvetica', fontsize='18', fontcolor='#333333',
             margin='0.5,0.4', penwidth='3.0')
    dot.attr('edge', color='#666666', penwidth='3.0', arrowsize='1.2')

    # Nodes
    dot.node('A', 'Data Sources (Google Drive)')
    dot.node('B', 'Data Ingestion & Timestamp Normalization')
    dot.node('C', 'Data Integration')
    dot.node('D', 'Feature Engineering')
    dot.node('E', 'EDA Visualizations')
    dot.node('F', 'Train/Test Split (80/20, time-ordered)')
    dot.node('G', 'Model Training')
    dot.node('H', 'Inference Pipeline')
    dot.node('I', 'Evaluation & Diagnostics')

    # Grouping to prevent messy line crossings using rank='same' and invisible edges
    with dot.subgraph() as s:
        s.attr(rank='same')
        s.node('E')
        s.node('F')
        s.edge('E', 'F', style='invis')

    with dot.subgraph() as s:
        s.attr(rank='same')
        s.node('I')
        s.node('H')
        s.edge('I', 'H', style='invis')

    # Edges
    dot.edge('A', 'B')
    dot.edge('B', 'C')
    dot.edge('C', 'D')
    dot.edge('D', 'E')
    dot.edge('D', 'F')

    dot.edge('F', 'G')
    dot.edge('F', 'I')

    dot.edge('G', 'I')
    dot.edge('G', 'H')

    dot.edge('C', 'H')

    dot.render('ml_pipeline_architecture', cleanup=True)

if __name__ == '__main__':
    create_diagram()
