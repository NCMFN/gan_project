import graphviz

def create_diagram():
    # Initialize the Graphviz directed graph with standard high-res settings
    dot = graphviz.Digraph(
        name='ML_Pipeline',
        format='png',
        engine='dot',
        filename='ml_pipeline_architecture'
    )

    # Global graph settings for a modern, left-to-right layout
    dot.attr(
        rankdir='LR',
        dpi='300',
        splines='ortho',
        nodesep='0.6',
        ranksep='0.6',
        pad='0.2'
    )

    # Global node settings (professional, modern flat design)
    # Using light blue fill with dark blue border as the default theme
    dot.attr('node',
        shape='box',
        style='filled,rounded',
        fillcolor='#EAF2F8',  # Light blue
        color='#2874A6',      # Dark blue border
        fontname='Helvetica',
        fontsize='12',
        fontcolor='#1B4F72',  # Dark text
        penwidth='1.5',
        margin='0.25,0.15'
    )

    # Global edge settings
    dot.attr('edge',
        color='#5D6D7E',
        penwidth='1.5',
        arrowsize='0.8'
    )

    # Database / Data Source Node (Cylinder shape)
    dot.node('A', 'Data Sources\n(Google Drive)', shape='cylinder', fillcolor='#D4E6F1', color='#1F618D', margin='0.15,0.15')

    # Data Preprocessing Section (Logical grouping via dashed subgraph)
    with dot.subgraph(name='cluster_data_prep') as c:
        c.attr(style='dashed,rounded', color='#85929E', penwidth='1.5', fontname='Helvetica-Bold', fontsize='14', fontcolor='#34495E', label='Data Loading & Preprocessing', margin='20')
        c.node('B', 'Data Ingestion &\nTimestamp Normalization')
        c.node('C', 'Data Integration')
        c.node('D', 'Feature Engineering')

        # Internal edges within data prep
        c.edge('B', 'C')
        c.edge('C', 'D')

    # EDA Visualizations (Side node)
    dot.node('E', 'EDA Visualizations', shape='note', fillcolor='#FCF3CF', color='#F1C40F', fontcolor='#7D6608')

    # Modeling Section (Logical grouping)
    with dot.subgraph(name='cluster_modeling') as c:
        c.attr(style='dashed,rounded', color='#85929E', penwidth='1.5', fontname='Helvetica-Bold', fontsize='14', fontcolor='#34495E', label='Model Development', margin='20')

        # Split data node (database symbol style or folder)
        c.node('F', 'Train/Test Split\n(80/20, time-ordered)', shape='folder', fillcolor='#D5F5E3', color='#239B56', fontcolor='#145A32')

        # Modeling nodes
        c.node('G', 'Model Training', fillcolor='#E8F8F5', color='#17A589', fontcolor='#0E6251')
        c.node('I', 'Evaluation &\nDiagnostics', fillcolor='#E8F8F5', color='#17A589', fontcolor='#0E6251')

        c.edge('F', 'G')
        c.edge('F', 'I', style='dashed', constraint='false', color='#A9DFBF') # Test set conceptually flows to evaluation
        c.edge('G', 'I')

    # Inference Section
    with dot.subgraph(name='cluster_inference') as c:
        c.attr(style='dashed,rounded', color='#85929E', penwidth='1.5', fontname='Helvetica-Bold', fontsize='14', fontcolor='#34495E', label='Deployment', margin='15')
        dot.node('H', 'Inference Pipeline', shape='component', fillcolor='#F5EEF8', color='#8E44AD', fontcolor='#512E5F')

    # Main structural edges connecting the clusters/nodes
    dot.edge('A', 'B')

    # Feature engineering branching
    dot.edge('D', 'E') # To EDA
    dot.edge('D', 'F') # To Train/Test split

    # Inference flow
    dot.edge('G', 'H')

    # Conceptual flow of integrated data to the inference pipeline (optional dashed line for completeness)
    dot.edge('C', 'H', style='dashed', color='#BDC3C7', constraint='false')

    # Render the graph
    dot.render(cleanup=True)

if __name__ == '__main__':
    create_diagram()
