import streamlit as st
import json
import re
from typing import List, Dict
from datetime import datetime
from model import get_output


def generate_mock_test(topic: str) -> List[Dict]:
    """Generate mock test questions with robust error handling"""
    # Input validation
    if not topic or not isinstance(topic, str):
        st.warning("⚠️ Please enter a valid topic!")
        return get_default_questions()

    prompt = f"""Generate a mock test about {topic} with:
    - 5 MCQs (4 options each)
    - 3 short-answer questions
    Return ONLY valid JSON with this structure:
    {{
        "questions": [
            {{
                "question": "...",
                "type": "MCQ",
                "options": ["A", "B", "C", "D"],
                "answer": "CorrectOption",
                "explanation": "...",
                "keywords": []
            }},
            {{
                "question": "...", 
                "type": "Short Answer",
                "answer": "...",
                "explanation": "...",
                "keywords": ["key", "terms"]
            }}
        ]
    }}"""
    
    try:
        response = get_output(prompt)
        questions = parse_questions(response)
        
        if not validate_questions(questions):
            st.warning("⚠️ Generated questions didn't pass validation")
            return get_default_questions()
            
        return questions
        
    except Exception as e:
        st.error(f"❌ Generation failed: {str(e)}")
        return get_default_questions()

def parse_questions(raw_response: str) -> List[Dict]:
    """Safely extract questions from API response"""
    try:
        # Try direct JSON parse first
        try:
            data = json.loads(raw_response)
            return data.get("questions", [])
        except json.JSONDecodeError:
            pass
        
        # Try extracting from markdown code block
        json_match = re.search(r'```(?:json)?\n(.*?)\n```', raw_response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(1))
            return data.get("questions", [])
        
        # Final cleanup attempt
        cleaned = raw_response.strip()
        cleaned = re.sub(r'^.*?\{', '{', cleaned, 1, re.DOTALL)
        data = json.loads(cleaned)
        return data.get("questions", [])
        
    except Exception as e:
        st.warning(f"⚠️ Parsing failed: {str(e)}")
        return []

def validate_questions(questions: List[Dict]) -> bool:
    """Comprehensive question validation"""
    if not isinstance(questions, list) or len(questions) < 1:
        return False
    
    required = {
        "MCQ": ["question", "type", "options", "answer"],
        "Short Answer": ["question", "type", "answer"]
    }
    
    for q in questions:
        q_type = q.get("type")
        if q_type not in required:
            return False
        if not all(k in q for k in required[q_type]):
            return False
        if q_type == "MCQ" and len(q.get("options", [])) != 4:
            return False
            
    return True

def get_default_questions() -> List[Dict]:
    """Reliable fallback questions"""
    return [
# MCQ Example
        {
            "question": "What is the capital of France?",
            "type": "MCQ",
            "options": ["London", "Berlin", "Paris", "Madrid"],
            "answer": "Paris",  # Must match exactly (case-insensitive now)
            "explanation": "Paris has been the capital since 508 AD"
        },

        # Short Answer Example (with keywords)
        {
            "question": "Explain photosynthesis",
            "type": "Short Answer",
            "answer": "process by which plants convert sunlight into energy",
            "keywords": ["plants", "sunlight", "energy", "convert"],
            "explanation": "Uses chlorophyll to transform light energy"
        },

        # Short Answer Example (without keywords - will use direct match)
        {
            "question": "Who invented Python?",
            "type": "Short Answer", 
            "answer": "guido van rossum",
            "explanation": "Created in the late 1980s"
        }
    ]

def record_attempt():
    """Safely record test attempt with validation"""
    if not hasattr(st.session_state, 'analysis_results'):
        st.warning("No results to record")
        return
    
    try:
        # Safely get all values with type conversion
        analysis = st.session_state.analysis_results
        attempt = {
            "user": str(st.session_state.get('current_user', 'Anonymous')),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "score": float(analysis.get("score", 0)),
            "time_taken": float(analysis.get("time_taken", 0)),
            "correct_mcqs": int(analysis.get("correct_mcqs", 0)),
            "total_mcqs": int(analysis.get("total_mcqs", 1)),
            "correct_short": float(analysis.get("correct_short", 0)),
            "total_short": int(analysis.get("total_short", 1))
        }
        
        # Initialize history if needed
        if 'attempts_history' not in st.session_state:
            st.session_state.attempts_history = []
            
        st.session_state.attempts_history.append(attempt)
        
    except Exception as e:
        st.error(f"Failed to record attempt: {str(e)}")