import streamlit as st
# Process user input (uploaded file or custom topic)
def process_input(uploaded_file, custom_topic):
    if uploaded_file:
        file_path = f"temp/{uploaded_file.name}"
        os.makedirs("temp", exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.session_state.uploaded_file = file_path

    if custom_topic:
        st.session_state.custom_topic = custom_topic

    if uploaded_file or custom_topic:
        st.session_state.page = "options"
        st.rerun()
    else:
        st.warning("⚠️ Please upload a file or enter a topic!")