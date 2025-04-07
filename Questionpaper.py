import streamlit as st
def generate_prompt(num_mcq, num_3_marks, num_5_marks, difficulty_level, subject, topics=None):
    prompt = f"Generate a Question Paper of {subject} having "
    if num_mcq > 0:
                prompt += f'{num_mcq} MCQs with 1 mark each, '
    if num_3_marks > 0:
                prompt += f'{num_3_marks} Questions with 3 marks each, '
    if num_5_marks > 0:
                prompt += f'{num_5_marks} Questions with 5 marks each. '
                prompt += f'Difficulty level: {difficulty_level}. '
    if topics:
                prompt += f'Cover topics: {topics}. '
    return prompt
        
subjects = { 'Data Structures': ['Trees', 'Sorting', 'Graphs'], 'Operating Systems': ['Memory Management', 'Scheduling'], 'DBMS': ['Normalization', 'SQL Queries'] }
subject = st.selectbox("📚 Select Subject", list(subjects.keys()))
topics = st.multiselect("📖 Select Topics", subjects[subject])
num_mcq = st.slider("Number of MCQs", 0, 20, 5)
num_3_marks = st.slider("Number of 3-mark Questions", 0, 20, 3)
num_5_marks = st.slider("Number of 5-mark Questions", 0, 20, 2)
difficulty = st.selectbox("Difficulty Level", ["Easy", "Medium", "Hard"])