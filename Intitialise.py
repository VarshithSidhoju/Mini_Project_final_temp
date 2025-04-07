import streamlit as st
from datetime import datetime
import json

def initialize_session():
    """Initialize all session state variables with enhanced defaults"""
    session_defaults = {
        # Input Handling
        "uploaded_file": None,
        "custom_topic": "",
        "file_content": "",
        
        # Navigation Control
        "page": "upload",  # States: upload, options, topics, questions, mock_tests, results, analysis
        
        # Test Content Management
        "questions": [],
        "current_question_index": 0,
        "question_types": [],  # Track distribution of question types
        
        # Test Progress Tracking
        "user_answers": {},
        "test_active": False,
        "test_completed": False,
        "test_generated": False,
        
        # Timing Metrics
        "start_time": None,
        "end_time": None,
        "time_taken": None,
        "time_per_question": [],
        
        # Comprehensive Analysis Results
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
            "total_keywords": 0
        },
        
        # Leaderboard System
        "leaderboard": [],
        "personal_best": None,
        
        # Question Generation Settings
        "subject": "",
        "topics": [],
        "difficulty": "Medium",
        "num_mcq": 5,
        "num_short_answer": 3,
        
        # Template Management
        "templates": {},
        "current_template": None,
        
        # Error Handling
        "last_error": None,
        "generation_attempts": 0
    }
    
    # Initialize only missing variables
    for key, value in session_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # Load templates if not loaded
    if not st.session_state.templates:
        try:
            with open("templates.json", "r") as f:
                st.session_state.templates = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            st.session_state.templates = {
                "default": {
                    "num_mcq": 5,
                    "num_short_answer": 3,
                    "time_limit": 30
                }
            }
    
    # Initialize question type tracking
    if not st.session_state.question_types:
        st.session_state.question_types = ["MCQ", "Short Answer"]
    
    # Ensure analysis_results structure
    required_analysis_keys = [
        "performance_by_type", 
        "question_details",
        "keywords_matched"
    ]
    for key in required_analysis_keys:
        if key not in st.session_state.analysis_results:
            st.session_state.analysis_results[key] = session_defaults["analysis_results"][key]