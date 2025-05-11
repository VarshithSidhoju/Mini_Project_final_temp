import streamlit as st 
from model import get_output

# Process tasks like extracting topics or generating questions
def process_task(task_name, prompt_template):
    st.title(f"🔍 {task_name}")
    with st.spinner("Processing... (AI is working)"):
        user_input = st.session_state.get("custom_topic", "")
        if user_input:
            prompt = prompt_template.format(user_input)
            st.session_state.response = get_output(prompt)
            st.write(st.session_state.response)
        else:
            st.warning("⚠️ No content available to process. Please upload a file or enter a topic.")
    
    if st.button("⬅️ Back to Options"):
        st.session_state.page = "options"
        st.rerun()