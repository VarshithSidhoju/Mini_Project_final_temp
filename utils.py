import streamlit as st
import json
from datetime import datetime

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

def load_templates():
    try:
        with open("templates.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_templates(templates):
    with open("templates.json", "w") as f:
        json.dump(templates, f)