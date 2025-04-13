import streamlit as st
import json
import os
from model import get_output  # Assuming this calls your AI model
import time
from login_page import show_login_page
from Intitialise import initialize_session  # Ensure this matches your filename
from Upload import process_input
from Mock_test import generate_mock_test, validate_questions, record_attempt, parse_questions
from Analysis import analyze_performance, display_analysis
from Process import process_task
from typing import List, Dict, Union
from datetime import datetime
import re
import networkx as nx
import plotly.graph_objects as go
from firebase_auth import is_authenticated, logout_user, save_starred_topic, unstar_topic, get_starred_topics

# Must be the first Streamlit command
st.set_page_config(page_title="Edugenius", layout="centered")

# Initialize session state after set_page_config
initialize_session()

st.markdown("""
<style>
    div.stButton > button:first-child {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

def load_templates():
    try:
        with open("templates.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_templates(templates):
    with open("templates.json", "w") as f:
        json.dump(templates, f)

def generate_prompt(num_mcq, num_3_marks, num_5_marks, difficulty_level, topics=None):
    prompt = f"Generate a comprehensive question paper with: "
    if num_mcq > 0:
        prompt += f'{num_mcq} MCQs with 1 mark each, '
    if num_3_marks > 0:
        prompt += f'{num_3_marks} Questions with 3 marks each, '
    if num_5_marks > 0:
        prompt += f'{num_5_marks} Questions with 5 marks each. '
    prompt += f'Difficulty level: {difficulty_level}. '
    
    if st.session_state.uploaded_file:
        prompt += f"\n\nBase the questions on this content:\n{st.session_state.file_content[:3000]}"
    elif st.session_state.custom_topic:
        prompt += f"\n\nBase the questions on this topic: {st.session_state.custom_topic}"
    
    if topics:
        prompt += f'\nFocus specifically on these aspects: {", ".join(topics)}'
    
    prompt += "\n\nFormat the output with clear question numbering and mark allocations."
    return prompt

def generate_flowchart():
    """Generate and display a static flowchart using Plotly with important topics and subheadings from user content"""
    st.title("📊 Knowledge Flowchart")
    
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
    if isinstance(user_input, bytes):  # Handle uploaded file content
        user_input = user_input.decode("utf-8", errors="ignore")
    
    # Validate user input
    if not user_input or user_input.strip() == "":
        st.error("No valid input provided. Please upload a file or enter a topic.")
        return
    
    # Flowchart customization options
    with st.expander("⚙️ Flowchart Settings", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            layout_style = st.selectbox(
                "Layout Style",
                ["Top-Down", "Left-Right", "Bottom-Up", "Right-Left"],
                index=0  # Default to Top-Down
            )
            node_size = st.slider("Node Size", 10, 50, st.session_state.flowchart_settings.get("node_size", 30))
        with col2:
            main_color = st.color_picker("Main Topic Color", st.session_state.flowchart_settings.get("main_topic_color", "#4CAF50"))
            subtopic_color = st.color_picker("Subtopic Color", st.session_state.flowchart_settings.get("subtopic_color", "#81C784"))
            starred_color = st.color_picker("Starred Topic Color", st.session_state.flowchart_settings.get("starred_color", "#FF9800"))
    
    st.session_state.flowchart_settings.update({
        "layout": layout_style,
        "node_size": node_size,
        "main_topic_color": main_color,
        "subtopic_color": subtopic_color,
        "starred_color": starred_color
    })
    
    # Craft prompt for the model to extract important topics and subheadings
    prompt = f"""
    Based on the following content, identify the important topics and their subheadings, and generate a flowchart structure representing their relationships.
    - Mark main topics with 'level': 0.
    - Mark subheadings under each main topic with 'level': 1.
    - Include 'id' as a unique string (e.g., topic_name_subheading_name) and 'label' as the readable name.
    - Provide 'edges' to show relationships (e.g., from main topic to subheading).
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
    
    # Call the model with debugging
    with st.spinner("Generating flowchart from model..."):
        try:
            model_output = get_output(prompt)  # Get raw output from the model
            st.write("Raw model output:", repr(model_output))  # Debug: Show raw output with hidden chars
            if not model_output or model_output.isspace():
                raise ValueError("Model returned empty or whitespace-only response")
            
            # Extract and clean JSON from the output
            json_match = re.search(r'\{.*\}', model_output, re.DOTALL)
            if json_match:
                json_str = json_match.group(0).strip()
                # Remove trailing commas and normalize whitespace
                json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
                json_str = re.sub(r'\s+', ' ', json_str)
                st.write("Cleaned JSON:", repr(json_str))  # Debug: Show cleaned string
                try:
                    flowchart_data = json.loads(json_str)
                except json.JSONDecodeError as e:
                    st.error(f"Failed to parse extracted JSON: {str(e)}. Cleaned JSON: {json_str}")
                    return
            else:
                st.error("No valid JSON object found in model output. Raw output:")
                st.write(model_output)
                return
            
        except Exception as e:
            st.error(f"Failed to generate flowchart from model: {str(e)}")
            st.session_state.last_error = str(e)
            return
    
    # Validate model output
    if not isinstance(flowchart_data, dict) or "nodes" not in flowchart_data or "edges" not in flowchart_data:
        st.error("Model output is invalid. Expected JSON with 'nodes' and 'edges'. Raw output:")
        st.write(flowchart_data)
        return
    
    # Create a directed graph using networkx for layout
    G = nx.DiGraph()
    for node in flowchart_data["nodes"]:
        G.add_node(node["id"], label=node["label"], level=node.get("level", 0))
    for edge in flowchart_data["edges"]:
        G.add_edge(edge["from"], edge["to"])
    
    # Compute layout based on style with error handling
    if G.number_of_nodes() > 0:
        try:
            if layout_style == "Top-Down":
                pos = nx.multipartite_layout(G, subset_key="level")
                pos = {node: [pos[node][0] if isinstance(pos[node], (list, tuple)) else pos[node], -data["level"] * 2] 
                       for node, data in G.nodes(data=True)}
            elif layout_style == "Left-Right":
                pos = nx.spring_layout(G, k=0.5, iterations=50)
            elif layout_style == "Bottom-Up":
                pos = nx.multipartite_layout(G, subset_key="level")
                pos = {node: [pos[node][0] if isinstance(pos[node], (list, tuple)) else pos[node], data["level"] * 2] 
                       for node, data in G.nodes(data=True)}
            elif layout_style == "Right-Left":
                pos = nx.spring_layout(G, k=0.5, iterations=50)
                x_coords = [pos[n][0] for n in G.nodes()]  # Get all x-coordinates
                pos = {node: [-x_coords[list(G.nodes()).index(node)], pos[node][1]] 
                       for node, data in G.nodes(data=True)}
            st.write("Node positions:", pos)  # Debug: Show computed positions
        except Exception as e:
            st.error(f"Error computing layout: {str(e)}. Falling back to default Top-Down layout.")
            pos = nx.multipartite_layout(G, subset_key="level")
            pos = {node: [pos[node][0] if isinstance(pos[node], (list, tuple)) else pos[node], -data["level"] * 2] 
                   for node, data in G.nodes(data=True)}
    else:
        st.error("No nodes to display in the graph.")
        return
    
    # Prepare data for Plotly
    labels = [data["label"] for _, data in G.nodes(data=True)]
    x_positions = [pos[node][0] for node in G.nodes()]
    y_positions = [pos[node][1] for node in G.nodes()]
    colors = [main_color if data["level"] == 0 else subtopic_color for _, data in G.nodes(data=True)]
    is_starred = [st.session_state.get('starred_topics', {}).get(data["label"], False) for _, data in G.nodes(data=True)]
    sizes = [node_size * 2 if data["level"] == 0 else node_size for _, data in G.nodes(data=True)]  # Use slider value
    
    # Create a Scatter plot for nodes
    fig = go.Figure()
    
    # Add nodes with custom shapes and colors
    fig.add_trace(go.Scatter(
        x=x_positions,
        y=y_positions,
        mode='markers+text',
        text=labels,
        textposition="top center",
        marker=dict(
            size=sizes,
            color=[starred_color if starred else color for starred, color in zip(is_starred, colors)],
            line=dict(width=2, color='#333'),
            symbol=['square' if data["level"] == 0 else 'circle' for _, data in G.nodes(data=True)]
        ),
        hoverinfo='none'  # Disable hover interaction
    ))
    
    # Add edges as lines
    for edge in flowchart_data["edges"]:
        from_node = next(n for n in G.nodes(data=True) if n[0] == edge["from"])[0]
        to_node = next(n for n in G.nodes(data=True) if n[0] == edge["to"])[0]
        fig.add_trace(go.Scatter(
            x=[pos[from_node][0], pos[to_node][0]],
            y=[pos[from_node][1], pos[to_node][1]],
            mode='lines',
            line=dict(color='#666', width=2),
            hoverinfo='none'  # Disable hover interaction
        ))
    
    # Update layout and configure to disable interactivity
    fig.update_layout(
        title="Knowledge Flowchart",
        showlegend=False,
        xaxis=dict(visible=False, fixedrange=True),  # Disable zooming/panning on x-axis
        yaxis=dict(visible=False, fixedrange=True),  # Disable zooming/panning on y-axis
        dragmode=False,  # Disable dragging (corrected from 'none' to False)
        height=750,
        width=800,
        plot_bgcolor='white'
    )
    
    # Enforce static rendering with Plotly config
    config = {'staticPlot': True, 'displayModeBar': False}  # Disable mode bar and enforce static plot
    st.plotly_chart(fig, config=config, use_container_width=True)
    st.session_state.flowchart_generated = True
    
    # Optional: Save data for download
    flowchart_path = f"flowchart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(flowchart_path, "w", encoding="utf-8") as f:
        f.write("Flowchart Data (JSON):\n\n")
        f.write(json.dumps(flowchart_data, indent=2))
    st.session_state.last_flowchart_path = flowchart_path
    
    col1, col2, col3 = st.columns(3)
    with col1:
        with open(flowchart_path, "rb") as f:
            st.download_button(
                label="📥 Download Flowchart Data",
                data=f,
                file_name="knowledge_graph.json",
                mime="application/json"
            )
    with col2:
        if st.button("🔄 Regenerate Flowchart"):
            st.session_state.flowchart_generated = False
            if os.path.exists(flowchart_path):
                os.remove(flowchart_path)
            st.rerun()
    with col3:
        if is_authenticated() and st.button("💾 Save to Firebase"):
            try:
                with open(flowchart_path, "r", encoding="utf-8") as f:
                    flowchart_text = f.read()
                from firebase_auth import save_flowchart
                save_flowchart(st.session_state.user['uid'], flowchart_text, datetime.now().isoformat())
                st.success("Flowchart saved to Firebase!")
            except (ImportError, AttributeError) as e:
                st.error(f"Firebase save not implemented: {str(e)}")
    
    if st.button("← Back to Options"):
        st.session_state.page = "options"
        st.rerun()

# Ensure required libraries are imported at the top if not already present
if 'networkx' not in st.session_state.get('imports', []) or 'plotly' not in st.session_state.get('imports', []):
    import networkx as nx
    import plotly.graph_objects as go
    st.session_state.imports = st.session_state.get('imports', []) + ['networkx', 'plotly']

def render_app_content():
    with st.sidebar:
        if 'user' in st.session_state:
            st.write(f"👤 Welcome, {st.session_state.user['email']}!")
            if st.button("🚪 Logout"):
                logout_user()
                st.rerun()
            
            st.write("## Navigation")
            if st.button("🏠 Home"):
                st.session_state.page = "upload"
                st.rerun()
            if st.button("⚙️ Options"):
                st.session_state.page = "options"
                st.rerun()
    
    if st.session_state.page == "upload":
        st.title("📚 Edugenius: AI Study Assistant")
        st.subheader("Upload your study material or enter a topic")
        
        uploaded_file = st.file_uploader("Upload a file", type=["txt", "pdf", "docx"])
        custom_topic = st.text_area("Or enter a study topic manually:")
        
        if uploaded_file:
            st.session_state.uploaded_file = uploaded_file
            st.session_state.file_content = uploaded_file.read().decode("utf-8", errors="ignore")
            st.success("File uploaded successfully!")
        
        if st.button("Next ➡️"):
            process_input(uploaded_file, custom_topic)
            st.session_state.page = "options"
            st.rerun()
    
    elif st.session_state.page == "options":
        st.title("📖 Study Assistant")
        st.subheader("Choose an action:")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📌 Extract Important Topics"):
                st.session_state.page = "topics"
                st.rerun()
            if st.button("📝 Generate Important Questions"):
                st.session_state.page = "questions"
                st.rerun()
            if st.button("🗺️ Generate Flowchart"):
                st.session_state.page = "flowchart"
                st.rerun()
        with col2:
            if st.button("🎯 Generate Mock Tests"):
                st.session_state.page = "mock_tests"
                st.rerun()
            if st.button("📊 Performance Analysis"):
                st.session_state.page = "analysis"
                st.rerun()
            if st.button("🌟 Starred Topics"):
                st.session_state.page = "starred_topics"
                st.rerun()

        
        if st.button("🏠 Back to Home"):
            st.session_state.page = "upload"
            st.rerun()
    
    elif st.session_state.page == "flowchart":
        generate_flowchart()

    elif st.session_state.page == "topics":
        st.title("📘 Key Topics")
        
        # Initialize starred_topics if not exists
        if 'starred_topics' not in st.session_state:
            st.session_state.starred_topics = {}
        
        # Load existing starred topics from Firestore if authenticated
        if is_authenticated() and st.session_state.user.get('uid'):
            starred_data = get_starred_topics(st.session_state.user['uid'])
            if starred_data:
                st.session_state.starred_topics = {
                    data['point']: True 
                    for data in starred_data.values() 
                    if data.get('starred', False)
                }

        # Generate topics if they don't exist
        if not st.session_state.get("topics_dict"):
            with st.spinner("Analyzing your content..."):
                content = st.session_state.file_content if st.session_state.uploaded_file else st.session_state.custom_topic
                
                if content:
                    response = process_task(
                        "Important Topics",
                        f"Extract main topics and key points from:\n{content[:3000]}"
                    )
                    
                    if response:
                        topics = {}
                        current_topic = None
                        
                        for line in response.split('\n'):
                            line = line.strip()
                            if line.startswith("## "):
                                current_topic = line[3:].strip()
                                topics[current_topic] = []
                            elif line.startswith("- ") and current_topic:
                                point = line[2:].strip()
                                topics[current_topic].append(point)
                        
                        st.session_state.topics_dict = topics
                        st.rerun()

        # Display topics in cards
        topics_dict = st.session_state.get("topics_dict", {})
        
        if topics_dict:
            for main_topic, points in topics_dict.items():
                st.markdown(f"### {main_topic}")
                
                for point in points:
                    # Check star status
                    is_starred = bool(st.session_state.starred_topics.get(point, False))
                    
                    # Create card with star button
                    st.markdown(f"""
                    <div style="
                        background-color: #f8f9fa;
                        border-radius: 10px;
                        padding: 15px;
                        margin-bottom: 15px;
                        border-left: 5px solid #4CAF50;
                        position: relative;
                    ">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div style="flex-grow: 1;">
                                <p style="margin: 0; font-size: 1.1rem;">{point}</p>
                            </div>
                            <div style="margin-left: 10px;">
                                <button id="star_{hash(point)}" style="
                                    background: none;
                                    border: none;
                                    font-size: 1.5rem;
                                    cursor: pointer;
                                    padding: 5px;
                                ">{"⭐" if is_starred else "☆"}</button>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Handle star button click
                    if st.button(" ", key=f"star_btn_{hash(point)}", 
                                help="Click to star/unstar this topic",
                                type="secondary", 
                                label_visibility="hidden"):
                        if is_authenticated():
                            # Toggle star status
                            new_state = not is_starred
                            
                            # Prepare topic data
                            topic_data = {
                                "main_topic": main_topic,
                                "point": point,
                                "content": point,
                                "starred": new_state,
                                "timestamp": datetime.now().isoformat()
                            }
                            
                            # Save to Firestore
                            success = save_starred_topic(
                                st.session_state.user['uid'],
                                f"{main_topic}_{point}",
                                topic_data
                            )
                            
                            if success:
                                # Update session state
                                if new_state:
                                    st.session_state.starred_topics[point] = True
                                else:
                                    st.session_state.starred_topics.pop(point, None)
                                st.rerun()
                        else:
                            st.warning("Please login to star topics")
        else:
            st.warning("No topics found. Please add content first.")
        
        if st.button("🌟 View Starred Topics"):
            st.session_state.page = "starred_topics"
            st.rerun()

    elif st.session_state.page == "starred_topics":
        st.title("⭐ Your Starred Topics")
        
        # Load fresh data from Firestore
        if is_authenticated():
            starred_data = get_starred_topics(st.session_state.user['uid'])
            if starred_data:
                # Update session state
                st.session_state.starred_topics = {
                    data['point']: True 
                    for data in starred_data.values() 
                    if data.get('starred', False)
                }
        
        if not st.session_state.starred_topics:
            st.info("You haven't starred any topics yet!")
        else:
            # Get full data from Firestore for display
            starred_data = get_starred_topics(st.session_state.user['uid'])
            for topic_id, data in starred_data.items():
                if data.get('starred', False):
                    # Card for starred topics
                    st.markdown(f"""
                    <div style="
                        background-color: #e8f5e9;
                        border-radius: 10px;
                        padding: 15px;
                        margin-bottom: 15px;
                        border-left: 5px solid #2e7d32;
                        position: relative;
                    ">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <h4 style="margin: 0 0 5px 0; color: #2e7d32;">{data['main_topic']}</h4>
                                <p style="margin: 0;">{data['point']}</p>
                                <small style="color: #666;">Saved on {data.get('timestamp', '')[:10]}</small>
                            </div>
                            <div>
                                <button id="unstar_{hash(topic_id)}" style="
                                    background: #ffebee;
                                    border: none;
                                    border-radius: 5px;
                                    padding: 5px 10px;
                                    color: #c62828;
                                    cursor: pointer;
                                ">Remove</button>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Handle unstar button click
                    if st.button(" ", key=f"unstar_btn_{hash(topic_id)}", 
                            help="Click to remove from starred",
                            type="secondary",
                            label_visibility="hidden"):
                        if unstar_topic(st.session_state.user['uid'], topic_id):
                            st.session_state.starred_topics.pop(data['point'], None)
                            st.rerun()
        
        if st.button("← Back to All Topics"):
            st.session_state.page = "topics"
            st.rerun()
            
    elif st.session_state.page == "mock_tests":
        st.title("📝 Mock Test")
        
        # Generate questions if not already created
        if not st.session_state.questions:
            if st.session_state.custom_topic:
                with st.spinner("Generating questions..."):
                    st.session_state.questions = generate_mock_test(st.session_state.custom_topic)
                    st.rerun()
            else:
                st.warning("Please enter a topic first")
                st.session_state.page = "upload"
                st.rerun()
        
        # Initialize timer on first render
        if st.session_state.start_time is None:
            st.session_state.start_time = datetime.now()
            st.session_state.test_active = True

        # Calculate progress
        total_questions = len(st.session_state.questions)
        answered = len([a for a in st.session_state.user_answers.values() if a is not None and a != ""])
        progress = answered / total_questions if total_questions > 0 else 0
        
        # Display progress header
        col1, col2 = st.columns([3, 1])
        with col1:
            st.progress(min(progress, 1.0))
            st.caption(f"Completed: {answered}/{total_questions}")
        with col2:
            elapsed = datetime.now() - st.session_state.start_time
            st.metric("Time", f"{elapsed.seconds//60}m {elapsed.seconds%60}s")

        # Get current question
        q = st.session_state.questions[st.session_state.current_question_index]
        current_answer = st.session_state.user_answers.get(q["question"], "")

        # Current question display

        with st.container():
            st.markdown(f"**Question {st.session_state.current_question_index + 1}**")
            st.markdown(f"#### {q['question']}")
            
            # Answer input
            if q["type"] == "MCQ":
                options = q["options"]
                # Store the actual selected option text, not just the index
                selected_option = st.radio(
                    "Select your answer:",
                    options=options,
                    index=options.index(current_answer) if current_answer in options else 0,
                    key=f"q_{st.session_state.current_question_index}_mcq"
                )
                # Store the full option text that matches the correct answer
                st.session_state.user_answers[q["question"]] = selected_option
            else:
                answer = st.text_area(
                    "Your answer:",
                    value=current_answer,
                    height=150,
                    key=f"q_{st.session_state.current_question_index}_sa"
                )
                st.session_state.user_answers[q["question"]] = answer
        # Navigation controls (now with 2 columns)
        nav_col1, nav_col2 = st.columns([1, 1])
        
        with nav_col1:
            if st.button("◀ Previous", disabled=st.session_state.current_question_index == 0):
                st.session_state.current_question_index -= 1
                st.rerun()
        
        with nav_col2:
            if st.button("Next ▶", disabled=st.session_state.current_question_index >= total_questions - 1):
                st.session_state.current_question_index += 1
                st.rerun()

        # Submit button (full width below navigation)
        all_answered = all(
            q["question"] in st.session_state.user_answers and 
            st.session_state.user_answers[q["question"]] not in [None, ""]
            for q in st.session_state.questions
        )
        
        if st.button("✅ Submit Test"):
            try:
                st.session_state.end_time = datetime.now()
                
                # Safely calculate time taken
                if st.session_state.start_time and st.session_state.end_time:
                    try:
                        st.session_state.time_taken = float((
                            st.session_state.end_time - st.session_state.start_time
                        ).total_seconds())
                    except:
                        st.session_state.time_taken = 0.0
                else:
                    st.session_state.time_taken = 0.0
                    
                st.session_state.test_completed = True
                st.write("User Answers:", st.session_state.user_answers)
                st.write("Correct Answers:", {q["question"]: q["answer"] for q in st.session_state.questions})
                analyze_performance()
                record_attempt()
                st.session_state.page = "analysis"
                st.rerun()
                
            except Exception as e:
                st.error(f"Submission error: {str(e)}")
                st.session_state.page = "mock_tests"
                st.rerun()

    if st.session_state.page == "analysis":
        display_analysis()

        if st.button("Back to Options"):
            st.session_state.page = "options"
            st.rerun()
    elif st.session_state.page == "questions":
        st.title("📝 Generate Important Questions")
        option = st.radio("Choose an option:", ["Generate Key Questions", "Generate a Full Question Paper"])
        
        if option == "Generate Key Questions":
            process_task("Important Questions", "Generate 5 key questions for: {}")
        else:
            def generate_prompt(num_mcq, num_3_marks, num_5_marks, difficulty_level, topics=None):
                prompt = f"Generate a comprehensive question paper with: "
                if num_mcq > 0:
                    prompt += f'{num_mcq} MCQs with 1 mark each, '
                if num_3_marks > 0:
                    prompt += f'{num_3_marks} Questions with 3 marks each, '
                if num_5_marks > 0:
                    prompt += f'{num_5_marks} Questions with 5 marks each. '
                prompt += f'Difficulty level: {difficulty_level}. '
                
                # Use either the uploaded content or custom topic
                if st.session_state.uploaded_file:
                    prompt += f"\n\nBase the questions on this content:\n{st.session_state.file_content[:3000]}"  # Using first 3000 chars
                elif st.session_state.custom_topic:
                    prompt += f"\n\nBase the questions on this topic: {st.session_state.custom_topic}"
                
                if topics:
                    prompt += f'\nFocus specifically on these aspects: {", ".join(topics)}'
                
                prompt += "\n\nFormat the output with clear question numbering and mark allocations."
                return prompt
            
            # Let user specify topics/focus areas
            topics = st.text_input("Specific topics to focus on (comma separated):")
            topics_list = [t.strip() for t in topics.split(",")] if topics else None
            
            num_mcq = st.slider("Number of MCQs", 0, 20, 5)
            num_3_marks = st.slider("Number of 3-mark Questions", 0, 20, 3)
            num_5_marks = st.slider("Number of 5-mark Questions", 0, 20, 2)
            difficulty = st.selectbox("Difficulty Level", ["Easy", "Medium", "Hard"])
            
            if st.button("🚀 Generate Question Paper"):
                if not st.session_state.uploaded_file and not st.session_state.custom_topic:
                    st.warning("Please upload content or enter a topic first!")
                else:
                    with st.spinner("Generating your custom question paper..."):
                        prompt = generate_prompt(num_mcq, num_3_marks, num_5_marks, difficulty, topics_list)
                        st.session_state.response = get_output(prompt)
                        st.text_area("📄 Generated Question Paper:", st.session_state.response, height=400)
        if st.button("Back to Options"):
            st.session_state.page = "options"
            st.rerun()
        if st.button("🏠 Back to Home"):
            st.session_state.page = "upload"
            st.rerun()


def main():
    initialize_session()
    if not is_authenticated():
        show_login_page()
        return
    render_app_content()

if __name__ == "__main__":
    main()