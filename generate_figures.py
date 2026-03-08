import graphviz

def generate_figure_1():
    dot = graphviz.Digraph(comment='Figure 1', format='png')
    dot.attr(rankdir='LR', fontname='Helvetica', fontsize='14', compound='true')
    dot.attr('node', shape='box', style='rounded,filled', fillcolor='#E3F2FD', fontname='Helvetica', fontsize='12')
    dot.attr('edge', fontname='Helvetica', fontsize='10', color='#555555')

    with dot.subgraph(name='cluster_patient') as c:
        c.attr(label='Patient Ecosystem', style='rounded,filled', fillcolor='#F5F5F5', fontcolor='#333333')
        c.node('Body', 'Patient Body', shape='ellipse', fillcolor='#FFE0B2')
        c.node('Watch', 'Smartwatch')
        c.node('ECG', 'ECG Patch')
        c.node('Glucose', 'Glucose Monitor')
        c.node('Clothing', 'Smart Clothing')

        c.edge('Body', 'Watch', dir='none')
        c.edge('Body', 'ECG', dir='none')
        c.edge('Body', 'Glucose', dir='none')
        c.edge('Body', 'Clothing', dir='none')

    dot.node('Gateway', 'Smartphone /\\nGateway Device', fillcolor='#C8E6C9')
    dot.node('Comm', 'Wireless Comm\\n(Bluetooth / WiFi / 6G)', shape='hexagon', fillcolor='#FFF9C4')

    with dot.subgraph(name='cluster_cloud') as c:
        c.attr(label='Cloud & AI Ecosystem', style='rounded,filled', fillcolor='#F5F5F5')
        c.node('Cloud', 'Cloud Healthcare\\nPlatform', fillcolor='#D1C4E9')
        c.node('AI', 'AI Analytics\\nSystem', fillcolor='#D1C4E9')
        c.edge('Cloud', 'AI', label='Analyze Data', dir='both')

    with dot.subgraph(name='cluster_hospital') as c:
        c.attr(label='Healthcare Providers', style='rounded,filled', fillcolor='#F5F5F5')
        c.node('Dashboard', 'Hospital / Doctor\\nDashboard', fillcolor='#FFCCBC')
        c.node('Remote', 'Remote Monitoring\\nCenter', fillcolor='#FFCCBC')

    dot.edge('Watch', 'Gateway', label='BLE/WiFi')
    dot.edge('ECG', 'Gateway', label='BLE')
    dot.edge('Glucose', 'Gateway', label='NFC/BLE')
    dot.edge('Clothing', 'Gateway', label='BLE')

    dot.edge('Gateway', 'Comm', label='Transmit')
    dot.edge('Comm', 'Cloud', label='6G / Internet')

    dot.edge('AI', 'Dashboard', label='Insights')
    dot.edge('Cloud', 'Remote', label='Real-time Data')

    dot.render('Figure_1_Wearable_IoMT', cleanup=True)

def generate_figure_2():
    dot = graphviz.Digraph(comment='Figure 2', format='png')
    dot.attr(rankdir='BT', fontname='Helvetica', fontsize='14', compound='true')
    dot.attr('node', shape='box', style='rounded,filled', fontname='Helvetica', fontsize='12')
    dot.attr('edge', fontname='Helvetica', fontsize='10', color='#555555')

    with dot.subgraph(name='cluster_device') as c:
        c.attr(label='Device Layer', style='rounded,filled', fillcolor='#E0F7FA', fontcolor='#333333', labelloc='b')
        c.node('WS', 'Wearable Sensors', fillcolor='#B2EBF2')
        c.node('IMD', 'IoT Medical Devices', fillcolor='#B2EBF2')
        c.node('IS', 'Implantable Sensors', fillcolor='#B2EBF2')
        # Invisible edge to keep layout
        c.edge('WS', 'IMD', style='invis')
        c.edge('IMD', 'IS', style='invis')

    with dot.subgraph(name='cluster_comm') as c:
        c.attr(label='Communication Layer', style='rounded,filled', fillcolor='#FFF9C4', fontcolor='#333333', labelloc='b')
        c.node('6G', '6G Wireless\\nConnectivity', shape='hexagon', fillcolor='#FFF59D')
        c.node('IoTProto', 'IoT Protocols', fillcolor='#FFF59D')
        c.node('Secure', 'Secure Transmission', fillcolor='#FFF59D')

    with dot.subgraph(name='cluster_edge') as c:
        c.attr(label='Edge / Fog Layer', style='rounded,filled', fillcolor='#E8F5E9', fontcolor='#333333', labelloc='b')
        c.node('EdgeAI', 'Edge AI Processing', fillcolor='#C8E6C9')
        c.node('LocalAnalytics', 'Local Health Data\\nAnalytics', fillcolor='#C8E6C9')
        c.node('Anomaly', 'Real-time Anomaly\\nDetection', fillcolor='#C8E6C9')

    with dot.subgraph(name='cluster_cloud') as c:
        c.attr(label='Cloud Intelligence Layer', style='rounded,filled', fillcolor='#F3E5F5', fontcolor='#333333', labelloc='b')
        c.node('AIML', 'AI/ML Models', fillcolor='#E1BEE7')
        c.node('Storage', 'Medical Data Storage', fillcolor='#E1BEE7')
        c.node('BigData', 'Big Data Analytics', fillcolor='#E1BEE7')
        c.node('DigitalTwins', 'Digital Health Twins', fillcolor='#E1BEE7')

    with dot.subgraph(name='cluster_app') as c:
        c.attr(label='Application Layer', style='rounded,filled', fillcolor='#FBE9E7', fontcolor='#333333', labelloc='b')
        c.node('RPM', 'Remote Patient\\nMonitoring', fillcolor='#FFCCBC')
        c.node('CDS', 'Clinical Decision\\nSupport', fillcolor='#FFCCBC')
        c.node('Telemed', 'Telemedicine', fillcolor='#FFCCBC')
        c.node('Predictive', 'Predictive Healthcare\\nSystems', fillcolor='#FFCCBC')

    # Add edges between layers to represent vertical data flow
    dot.edge('WS', '6G', ltail='cluster_device', lhead='cluster_comm', minlen='2')
    dot.edge('6G', 'EdgeAI', ltail='cluster_comm', lhead='cluster_edge', minlen='2')
    dot.edge('EdgeAI', 'AIML', ltail='cluster_edge', lhead='cluster_cloud', minlen='2')
    dot.edge('AIML', 'RPM', ltail='cluster_cloud', lhead='cluster_app', minlen='2')

    dot.render('Figure_2_Architecture_6G_Healthcare', cleanup=True)

def generate_figure_3():
    dot = graphviz.Digraph(comment='Figure 3', format='png')
    dot.attr(rankdir='TB', fontname='Helvetica', fontsize='14', compound='true')
    dot.attr('node', shape='box', style='rounded,filled', fontname='Helvetica', fontsize='12')
    dot.attr('edge', fontname='Helvetica', fontsize='10', color='#555555', penwidth='2')

    # Central element
    dot.node('6GBS', '6G Base Station\\n(Ultra-low Latency & High Bandwidth)', shape='hexagon', fillcolor='#FFD54F', width='3', height='1.5')

    # Edge Computing Nodes
    with dot.subgraph(name='cluster_edge_nodes') as c:
        c.attr(label='Edge Computing Nodes', style='dashed', color='#81C784')
        c.node('Edge1', 'Edge Node 1\\n(Local AI)', fillcolor='#C8E6C9')
        c.node('Edge2', 'Edge Node 2\\n(Data Aggregation)', fillcolor='#C8E6C9')

    # End User / Devices Level
    with dot.subgraph(name='cluster_devices') as c:
        c.attr(label='Smart Healthcare Ecosystem', style='rounded', color='#90CAF9', bgcolor='#F3E5F5')
        c.node('Wearable', 'Wearable Health\\nDevices', fillcolor='#BBDEFB')
        c.node('Ambulance', 'Connected\\nAmbulance', fillcolor='#BBDEFB')
        c.node('MobileApp', 'Mobile Health\\nApplications', fillcolor='#BBDEFB')
        c.node('Hospital', 'Smart Hospital\\nInfrastructure', fillcolor='#BBDEFB')
        c.node('RemoteDoc', 'Remote Doctors /\\nTelemedicine', fillcolor='#BBDEFB')

    # Cloud Level
    with dot.subgraph(name='cluster_cloud_core') as c:
        c.attr(label='Core Network & Cloud', style='rounded,filled', fillcolor='#E1BEE7')
        c.node('AICloud', 'AI Healthcare Cloud\\n(Global Analytics)', shape='ellipse', fillcolor='#CE93D8')
        c.node('DataCenter', 'Medical Data Centers\\n(EHR & Big Data)', shape='cylinder', fillcolor='#CE93D8')

    # Connections
    dot.edge('Wearable', '6GBS', label='Health Data')
    dot.edge('Ambulance', '6GBS', label='Emergency\\nTelemetry')
    dot.edge('MobileApp', '6GBS', label='Patient Sync')

    dot.edge('6GBS', 'Hospital', label='Real-time\\nDiagnostics', dir='both')
    dot.edge('6GBS', 'RemoteDoc', label='Teleconsultation', dir='both')

    dot.edge('6GBS', 'Edge1', dir='both')
    dot.edge('6GBS', 'Edge2', dir='both')

    dot.edge('Edge1', 'AICloud', label='Aggregated Data')
    dot.edge('Edge2', 'DataCenter', label='Processed Records')

    dot.edge('AICloud', 'DataCenter', dir='both')
    dot.edge('AICloud', '6GBS', label='Global AI Insights', style='dashed')

    dot.render('Figure_3_6G_Healthcare_Ecosystem', cleanup=True)

def generate_figure_4():
    dot = graphviz.Digraph(comment='Figure 4', format='png')
    dot.attr(rankdir='LR', fontname='Helvetica', fontsize='14', compound='true')
    dot.attr('node', shape='box', style='rounded,filled', fontname='Helvetica', fontsize='12')
    dot.attr('edge', fontname='Helvetica', fontsize='10', color='#333333', penwidth='2')

    dot.node('S1', 'Data Acquisition:\\nWearable Sensors', fillcolor='#B2DFDB')
    dot.node('S2', 'Local Processing:\\nGateway / Smartphone', fillcolor='#A5D6A7')
    dot.node('S3', 'Edge Processing', fillcolor='#81C784')
    dot.node('S4', '6G Network\\nTransmission', shape='hexagon', fillcolor='#FFF59D')
    dot.node('S5', 'Cloud Storage', shape='cylinder', fillcolor='#90CAF9')
    dot.node('S6', 'AI Analytics\\nEngine', fillcolor='#CE93D8')
    dot.node('S7', 'Electronic Health\\nRecords (EHR)', shape='cylinder', fillcolor='#F48FB1')
    dot.node('S8', 'Doctor / Hospital\\nDashboard', fillcolor='#FFAB91')
    dot.node('S9', 'Patient Feedback\\nSystem', fillcolor='#FFE082')

    # Main Data Pipeline
    dot.edge('S1', 'S2')
    dot.edge('S2', 'S3')
    dot.edge('S3', 'S4')
    dot.edge('S4', 'S5')
    dot.edge('S5', 'S6')
    dot.edge('S6', 'S7')
    dot.edge('S7', 'S8')

    # Feedback loop
    dot.edge('S8', 'S9', label='Actionable Insights', style='dashed', color='#D32F2F')
    dot.edge('S9', 'S1', label='Adjust Monitoring', style='dashed', color='#D32F2F')

    dot.render('Figure_4_Data_Flow_Pipeline', cleanup=True)

if __name__ == "__main__":
    generate_figure_1()
    generate_figure_2()
    generate_figure_3()
    generate_figure_4()
