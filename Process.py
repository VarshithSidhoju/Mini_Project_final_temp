import streamlit as st 
from model import get_output
# Process tasks like extracting topics or generating questions
def process_task(task_name, prompt_template):
    st.title(f"🔍 {task_name}")
    st.write("Processing... (AI is working)")
    user_input = st.session_state.uploaded_file or st.session_state.custom_topic
    if user_input:
        prompt = prompt_template.format(user_input)
        st.session_state.response = get_output(prompt)
        st.write(st.session_state.response)
    if st.button("⬅️ Back to Options"):
        st.session_state.page = "options"
        st.rerun()