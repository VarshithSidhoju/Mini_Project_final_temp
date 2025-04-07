import streamlit as st

st.write("Firebase config exists:", "firebase" in st.secrets)
if "firebase" in st.secrets:
    st.write("Project ID:", st.secrets["firebase"]["project_id"])