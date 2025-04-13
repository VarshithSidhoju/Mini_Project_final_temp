# initialise.py
import streamlit as st
from datetime import datetime
import json
try:
    from firebase_auth import is_authenticated, get_starred_topics  # Explicit import
except ImportError:
    # Fallback if firebase_auth is incomplete
    def is_authenticated(): return False
    def get_starred_topics(uid): return {}
from pyvis.network import Network
import streamlit.components.v1 as components

def initialize_session():
    """Initialize all session state variables with enhanced defaults"""
    session_defaults = {
        "uploaded_file": None,
        "custom_topic": "",
        "file_content": "",
        "page": "upload",
        "topics_dict": {},
        "topics_list": [],
        "starred_topics": {},
        "selected_topics": [],
        "questions": [],
        "current_question_index": 0,
        "question_types": [],
        "user_answers": {},
        "test_active": False,
        "test_completed": False,
        "test_generated": False,
        "start_time": None,
        "end_time": None,
        "time_taken": None,
        "time_per_question": [],
        "firebase_collections": {
            "user_topics": "user_topics",
            "flowcharts": "user_flowcharts"
        },
        "analysis_results": {
            "score": 0.0,
            "total_questions": 0,
            "accuracy": 0.0,
            "correct_mcqs": 0,
            "total_mcqs": 0,
            "correct_short_answers": 0,
            "total_short_answers": 0,
            "time_taken": 0,
            "performance_by_type": {
                "MCQ": {"correct": 0, "total": 0},
                "Short Answer": {"correct": 0, "total": 0}
            },
            "question_details": [],
            "keywords_matched": 0,
            "total_keywords": 0,
            "knowledge_gaps": []
        },
        "leaderboard": [],
        "personal_best": None,
        "subject": "",
        "topics": [],
        "difficulty": "Medium",
        "num_mcq": 5,
        "num_short_answer": 3,
        "flowchart_settings": {
            "node_size": 25,
            "main_topic_color": "#4CAF50",
            "subtopic_color": "#FFECB3",
            "starred_color": "#FFD700",
            "layout": "hierarchical"
        },
        "templates": {},
        "current_template": None,
        "last_error": None,
        "generation_attempts": 0,
        "flowchart_generated": False,
        "last_flowchart_path": None
    }
    
    # Initialize only missing variables
    for key, value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # Initialize topics_dict if not exists but topics_list exists
    if not st.session_state.topics_dict and st.session_state.topics_list:
        st.session_state.topics_dict = {topic: [] for topic in st.session_state.topics_list}
    
    # Load templates if not loaded
    if not st.session_state.templates:
        try:
            with open("templates.json", "r") as f:
                st.session_state.templates = json.load(f)
                if "flowchart" not in st.session_state.templates:
                    st.session_state.templates["flowchart"] = {
                        "node_size": 25,
                        "colors": {
                            "main": "#4CAF50",
                            "sub": "#FFECB3",
                            "starred": "#FFD700"
                        }
                    }
        except (FileNotFoundError, json.JSONDecodeError):
            st.session_state.templates = session_defaults["templates"]
    
    # Initialize question type tracking
    if not st.session_state.question_types:
        st.session_state.question_types = ["MCQ", "Short Answer"]

    # Initialize starred topics from Firebase if authenticated
    if is_authenticated() and not st.session_state.starred_topics:
        try:
            starred_data = get_starred_topics(st.session_state.user['uid'])
            if starred_data:
                st.session_state.starred_topics = {
                    data['point']: True 
                    for data in starred_data.values() 
                    if data.get('starred', False)
                }
        except (NameError, AttributeError, Exception) as e:
            st.warning(f"Could not load starred topics: {str(e)}. Proceeding without starred topics.")
            st.session_state.starred_topics = {}