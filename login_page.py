import streamlit as st
from firebase_auth import login_user, signup_user, logout_user, is_authenticated

def show_login_page():
    st.title("Welcome to the Exam Prep App")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submit_button = st.form_submit_button("Login")
            
            if submit_button:
                if login_user(email, password):
                    st.success("Login successful!")
                    st.rerun()
    
    with tab2:
        with st.form("signup_form"):
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")
            submit_button = st.form_submit_button("Sign Up")
            
            if submit_button:
                if password != confirm_password:
                    st.error("Passwords don't match!")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters long")
                else:
                    if signup_user(email, password):
                        st.success("Account created successfully! Please login.")
                        st.rerun()