import streamlit as st
import json
import os
from model import get_output
import time
from Intitialise import initialize_session
from Upload import process_input
from Mock_test import generate_mock_test,validate_questions,record_attempt,parse_questions
from Analysis import analyze_performance, display_analysis
from Process import process_task
from typing import List, Dict, Union
from datetime import datetime
from login_page import show_login_page
from firebase_auth import is_authenticated, logout_user
# Page configuration
st.set_page_config(page_title="Edugenius", layout="centered")

st.markdown("""
<style>
    div.stButton > button:first-child {
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)
# Load templates from a JSON file (if any)
def load_templates():
    try:
        with open("templates.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_templates(templates):
    with open("templates.json", "w") as f:
        json.dump(templates, f)

def render_app_content():
    """All your existing page rendering code goes here"""
    with st.sidebar:
        if 'user' in st.session_state:  # Check if user exists
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
    
    # Rest of your page rendering logic
    if st.session_state.page == "upload":
        st.title("📚 Edugenius: AI Study Assistant")
        st.subheader("Upload your study material or enter a topic")
        uploaded_file = st.file_uploader("Choose a PDF or Text file", type=["pdf", "txt"])
        custom_topic = st.text_area("Or enter a study topic manually:")
        if st.button("Next ➡️"):
            process_input(uploaded_file, custom_topic)
    
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
        with col2:
            if st.button("🎯 Generate Mock Tests"):
                st.session_state.page = "mock_tests"
                st.rerun()
            if st.button("📊 Performance Analysis"):
                st.session_state.page = "analysis"
                st.rerun()
        if st.button("🏠 Back to Home"):
            st.session_state.page = "upload"
            st.rerun()

# Generate mock test questions

# Extract important topics
if st.session_state.page == "topics":
    process_task("Important Topics", "Extract the most important topics from: {}")

# Generate important questions
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


# Mock test page


# Check if user is on mock test page
if st.session_state.page == "mock_tests":
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

def main():
    # Initialize session variables
    initialize_session()
    
    # Check authentication
    if not is_authenticated():
        show_login_page()
        return
    
    # Main application content
    render_app_content()

if __name__ == "__main__":
    main()
