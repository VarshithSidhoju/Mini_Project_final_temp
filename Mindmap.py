import streamlit as st
from model1 import get_mindmap_output
import networkx as nx
import json
import plotly.graph_objects as go
import numpy as np
from firebase_auth import is_authenticated
from datetime import datetime
import os
def generate_mindmap():
    """Generate and display a static mind map using Plotly with important topics and subheadings from user content"""
    st.title("🧠 Knowledge Mind Map")
    
    # Check if user input exists
    if not st.session_state.get("file_content") and not st.session_state.get("custom_topic"):
        st.warning("No input provided. Please:")
        st.markdown("""
        1. Go to **Home**
        2. Upload a file or enter a topic
        3. Return here
        """)
        if st.button("⏩ Go to Home Page Now"):
            st.session_state.page = "upload"
            st.rerun()
        return
    
    # Get user input
    user_input = st.session_state.get("file_content", "") or st.session_state.get("custom_topic", "")
    if isinstance(user_input, bytes):
        user_input = user_input.decode("utf-8", errors="ignore")
    
    if not user_input or user_input.strip() == "":
        st.error("No valid input provided. Please upload a file or enter a topic.")
        return
    
    # Customization options
    with st.expander("⚙️ Mind Map Settings", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            layout_style = st.selectbox(
                "Layout Style",
                ["Radial", "Tree"],
                index=0
            )
            node_size = st.slider("Node Size", 10, 50, st.session_state.flowchart_settings.get("node_size", 30))
        with col2:
            central_color = st.color_picker("Central Topic Color", st.session_state.flowchart_settings.get("main_topic_color", "#FF5722"))
            subtopic_color = st.color_picker("Subtopic Color", st.session_state.flowchart_settings.get("subtopic_color", "#4CAF50"))
            starred_color = st.color_picker("Starred Topic Color", st.session_state.flowchart_settings.get("starred_color", "#FF9800"))
    
    st.session_state.flowchart_settings.update({
        "layout": layout_style,
        "node_size": node_size,
        "main_topic_color": central_color,
        "subtopic_color": subtopic_color,
        "starred_color": starred_color
    })
    
    # Craft prompt
    prompt = f"""
    Based on the following content, identify the important topics and their subheadings, and generate a mind map structure representing their relationships.
    - Mark main topics with 'level': 0 (central nodes).
    - Mark subheadings under each main topic with 'level': 1 (branches).
    - Include 'id' as a unique string (e.g., topic_name_subheading_name) and 'label' as the readable name.
    - Provide 'edges' to show relationships (e.g., from main topic to subheading).
    - Ensure the structure is hierarchical, suitable for a mind map.
    Example output for content about "Programming":
    {{
        "nodes": [
            {{"id": "programming", "label": "Programming", "level": 0}},
            {{"id": "programming_variables", "label": "Variables", "level": 1}},
            {{"id": "programming_loops", "label": "Loops", "level": 1}}
        ],
        "edges": [
            {{"from": "programming", "to": "programming_variables"}},
            {{"from": "programming", "to": "programming_loops"}}
        ]
    }}
    Provide the output as a JSON object with:
    - "nodes": a list of objects with "id" (unique string), "label" (string), and "level" (integer, 0 for main topics, 1 for subtopics)
    - "edges": a list of objects with "from" (source node id) and "to" (target node id)
    Limit the content to the first 3000 characters if longer.
    Return ONLY the JSON object, no additional text or explanation.

    Content:
    {user_input[:3000]}
    """
    
    # Call the model
    with st.spinner("Generating mind map from model..."):
        try:
            model_output = get_mindmap_output(prompt)
            if not model_output or model_output.isspace():
                raise ValueError("Model returned empty or whitespace-only response")
            
            # Parse JSON
            try:
                mindmap_data = json.loads(model_output)
            except json.JSONDecodeError as e:
                st.error(f"Failed to parse JSON: {e}")
                return
            
            # Validate structure
            if not isinstance(mindmap_data, dict) or "nodes" not in mindmap_data or "edges" not in mindmap_data:
                st.error("Invalid model output. Expected 'nodes' and 'edges'.")
                return
            
            # Fix nodes
            for node in mindmap_data["nodes"]:
                if "level" not in node:
                    node["level"] = 1
                    st.warning(f"Node {node.get('id', 'unknown')} missing 'level'. Set to 1.")
                if "id" not in node or "label" not in node:
                    st.error(f"Invalid node: {node}")
                    return
            
        except Exception as e:
            st.error(f"Failed to generate mind map: {e}")
            return
    
    # Create graph
    G = nx.DiGraph()
    for node in mindmap_data["nodes"]:
        G.add_node(node["id"], label=node["label"], level=node["level"])
    for edge in mindmap_data["edges"]:
        if edge["from"] in G.nodes and edge["to"] in G.nodes:
            G.add_edge(edge["from"], edge["to"])
        else:
            st.warning(f"Skipping invalid edge: {edge}")
    
    # Compute layout
    if G.number_of_nodes() > 0:
        try:
            if layout_style == "Radial":
                pos = nx.spring_layout(G, k=1.5, iterations=100)
                for node, data in G.nodes(data=True):
                    if data.get("level", 1) == 0:
                        main_nodes = [n for n, d in G.nodes(data=True) if d.get("level", 1) == 0]
                        if len(main_nodes) > 1:
                            angle = (main_nodes.index(node) * 360 / len(main_nodes))
                            radius = 0.5
                            pos[node] = [radius * np.cos(np.radians(angle)), radius * np.sin(np.radians(angle))]
                        else:
                            pos[node] = [0, 0]
            elif layout_style == "Tree":
                pos = nx.spring_layout(G, k=0.7, iterations=50)
                main_nodes = [n for n, d in G.nodes(data=True) if d.get("level", 1) == 0]
                for node, data in G.nodes(data=True):
                    if data.get("level", 1) == 0:
                        if len(main_nodes) > 1:
                            angle = (main_nodes.index(node) * 360 / len(main_nodes))
                            pos[node] = [0.5 * np.cos(np.radians(angle)), 0.5 * np.sin(np.radians(angle))]
                        else:
                            pos[node] = [0, 0]
                    elif data.get("level", 1) == 1:
                        angle = hash(node) % 360
                        radius = 1.8
                        pos[node] = [radius * np.cos(np.radians(angle)), radius * np.sin(np.radians(angle))]
        except Exception as e:
            st.error(f"Error computing layout: {e}. Falling back to default Radial layout.")
            pos = nx.spring_layout(G, k=1.5, iterations=100)
            for node, data in G.nodes(data=True):
                if data.get("level", 1) == 0:
                    main_nodes = [n for n, d in G.nodes(data=True) if d.get("level", 1) == 0]
                    if len(main_nodes) > 1:
                        angle = (main_nodes.index(node) * 360 / len(main_nodes))
                        pos[node] = [0.5 * np.cos(np.radians(angle)), 0.5 * np.sin(np.radians(angle))]
                    else:
                        pos[node] = [0, 0]
    else:
        st.error("No nodes to display in the mind map.")
        return
    
    # Render mind map
    labels = [data["label"] for _, data in G.nodes(data=True)]
    x_positions = [pos[node][0] for node in G.nodes()]
    y_positions = [pos[node][1] for node in G.nodes()]
    colors = [central_color if data.get("level", 1) == 0 else subtopic_color for _, data in G.nodes(data=True)]
    is_starred = [st.session_state.get('starred_topics', {}).get(data["label"], False) for _, data in G.nodes(data=True)]
    sizes = [node_size * 2 if data.get("level", 1) == 0 else node_size for _, data in G.nodes(data=True)]
    
    fig = go.Figure()
    
    # Edges
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        xc = (x0 + x1) / 2 + (y1 - y0) * 0.1
        yc = (y0 + y1) / 2 + (x0 - x1) * 0.1
        fig.add_trace(go.Scatter(
            x=[x0, xc, x1],
            y=[y0, yc, y1],
            mode='lines',
            line=dict(color='#666', width=2, shape='spline'),
            hoverinfo='none'
        ))
    
    # Nodes
    fig.add_trace(go.Scatter(
        x=x_positions,
        y=y_positions,
        mode='markers+text',
        text=labels,
        textposition="middle center",
        textfont=dict(size=12, color='#000000'),
        marker=dict(
            size=sizes,
            color=[starred_color if starred else color for starred, color in zip(is_starred, colors)],
            line=dict(width=2, color='#333'),
            symbol=['hexagon' if data.get("level", 1) == 0 else 'circle' for _, data in G.nodes(data=True)]
        ),
        hoverinfo='none'
    ))
    
    # Layout
    fig.update_layout(
        title="Knowledge Mind Map",
        showlegend=False,
        xaxis=dict(visible=False, fixedrange=True),
        yaxis=dict(visible=False, fixedrange=True),
        dragmode=False,
        height=750,
        width=800,
        plot_bgcolor='white',
        margin=dict(l=0, r=0, t=50, b=0)
    )
    
    config = {'staticPlot': True, 'displayModeBar': False}
    st.plotly_chart(fig, config=config, use_container_width=True)
    st.session_state.flowchart_generated = True
    
    # Save and action buttons
    mindmap_path = f"mindmap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(mindmap_path, "w", encoding="utf-8") as f:
        f.write("Mind Map Data (JSON):\n\n")
        f.write(json.dumps(mindmap_data, indent=2))
    st.session_state.last_flowchart_path = mindmap_path
    
    col1, col2, col3 = st.columns(3)
    with col1:
        with open(mindmap_path, "rb") as f:
            st.download_button(
                label="📥 Download Mind Map Data",
                data=f,
                file_name="knowledge_mindmap.json",
                mime="application/json"
            )
    with col2:
        if st.button("🔄 Regenerate Mind Map"):
            st.session_state.flowchart_generated = False
            if os.path.exists(mindmap_path):
                os.remove(mindmap_path)
            st.rerun()
    with col3:
        if is_authenticated() and st.button("💾 Save to Firebase"):
            try:
                with open(mindmap_path, "r", encoding="utf-8") as f:
                    mindmap_text = f.read()
                from firebase_auth import save_flowchart
                save_flowchart(st.session_state.user['uid'], mindmap_text, datetime.now().isoformat())
                st.success("Mind map saved to Firebase!")
            except (ImportError, AttributeError) as e:
                st.error(f"Firebase save not implemented: {e}")
    
    if st.button("← Back to Options"):
        st.session_state.page = "options"
        st.rerun()