import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth
import json
import requests

# Initialize Firebase Admin SDK
def initialize_firebase():
    try:
        # Check if Firebase app is already initialized
        if not firebase_admin._apps:
            # Load the Firebase service account key from secrets
            firebase_creds = st.secrets["firebase"]
            
            # Create credentials object from the dictionary
            cred = credentials.Certificate({
                "type": firebase_creds["type"],
                "project_id": firebase_creds["project_id"],
                "private_key_id": firebase_creds["private_key_id"],
                "private_key": firebase_creds["private_key"].replace('\\n', '\n'),
                "client_email": firebase_creds["client_email"],
                "client_id": firebase_creds["client_id"],
                "auth_uri": firebase_creds["auth_uri"],
                "token_uri": firebase_creds["token_uri"],
                "auth_provider_x509_cert_url": firebase_creds["auth_provider_x509_cert_url"],
                "client_x509_cert_url": firebase_creds["client_x509_cert_url"]
            })
            
            firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Firebase initialization error: {str(e)}")

# Firebase Authentication functions
def login_user(email, password):
    try:
        # Use Firebase REST API for client-side login
        api_key = st.secrets["firebase"]["api_key"]
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        st.session_state.user = {
            "uid": data["localId"],
            "email": data["email"],
            "id_token": data["idToken"],
            "refresh_token": data["refreshToken"]
        }
        return True
    except requests.exceptions.HTTPError as e:
        error_data = json.loads(e.response.text)
        st.error(f"Login failed: {error_data.get('error', {}).get('message', 'Unknown error')}")
        return False
    except Exception as e:
        st.error(f"Login error: {str(e)}")
        return False

def signup_user(email, password):
    try:
        api_key = st.secrets["firebase"]["api_key"]
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={api_key}"
        
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        st.session_state.user = {
            "uid": data["localId"],
            "email": data["email"],
            "id_token": data["idToken"],
            "refresh_token": data["refreshToken"]
        }
        return True
    except requests.exceptions.HTTPError as e:
        error_data = json.loads(e.response.text)
        st.error(f"Signup failed: {error_data.get('error', {}).get('message', 'Unknown error')}")
        return False
    except Exception as e:
        st.error(f"Signup error: {str(e)}")
        return False

def logout_user():
    if "user" in st.session_state:
        del st.session_state.user
    st.session_state.clear()
    st.rerun()

def get_user():
    return st.session_state.get("user", None)

def is_authenticated():
    return "user" in st.session_state