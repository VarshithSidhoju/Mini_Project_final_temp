import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth
import json
import requests
import datetime
from firebase_admin import firestore

# Initialize Firebase Admin SDK
def initialize_firebase():
    try:
        if not firebase_admin._apps:
            firebase_creds = st.secrets["firebase"]
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

# Authentication Functions
def login_user(email, password):
    try:
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

# Firestore Database Functions
def get_db():
    if not firebase_admin._apps:
        initialize_firebase()
    return firestore.client()

def save_starred_topic(user_id: str, topic_id: str, topic_data: dict) -> bool:
    """
    Save a complete topic with all metadata to Firestore.
    
    Args:
        user_id: The user's unique ID from Firebase Auth
        topic_id: A unique identifier for the topic (recommended format: "main_topic_subtopic")
        topic_data: Dictionary containing topic metadata with required keys:
            - main_topic: str
            - subtopic: str
            - content: str
            - starred: bool
    
    Returns:
        bool: True if successful, False if failed
    
    Example:
        topic_data = {
            "main_topic": "Machine Learning",
            "subtopic": "Neural Networks",
            "content": "Explanation of backpropagation...",
            "starred": True
        }
        save_starred_topic("user123", "ml_neural_nets", topic_data)
    """
    
    # Validate input data
    required_keys = ["main_topic", "subtopic", "content", "starred"]
    if not all(key in topic_data for key in required_keys):
        st.error("Invalid topic data structure. Missing required fields.")
        return False
    
    if not isinstance(topic_data["starred"], bool):
        st.error("Starred status must be boolean")
        return False
    
    try:
        db = get_db()
        user_ref = db.collection("user_topics").document(user_id)
        
        # Add timestamp and ensure consistent data structure
        topic_data.update({
            "timestamp": datetime.datetime.now().isoformat(),
            "last_updated": datetime.datetime.now().isoformat()
        })
        
        # Atomic update using transaction
        @firestore.transactional
        def update_starred_topic(transaction, user_ref):
            doc = user_ref.get(transaction=transaction)
            current_data = doc.to_dict() or {}
            starred_topics = current_data.get("starred_topics", {})
            
            # Update only the specified topic
            starred_topics[topic_id] = topic_data
            
            transaction.set(user_ref, {
                "starred_topics": starred_topics,
                "last_updated": topic_data["last_updated"]
            }, merge=True)
        
        # Run the transaction
        transaction = db.transaction()
        update_starred_topic(transaction, user_ref)
        
        return True
        
    except firestore.exceptions.FirestoreError as e:
        st.error(f"Firestore error while saving topic: {str(e)}")
        return False
    except ValueError as e:
        st.error(f"Invalid data format: {str(e)}")
        return False
    except Exception as e:
        st.error(f"Unexpected error saving topic: {str(e)}")
        return False

def get_starred_topics(user_id):
    """Retrieve all starred topics with complete metadata"""
    try:
        db = get_db()
        doc_ref = db.collection("user_topics").document(user_id)
        doc = doc_ref.get()
        
        if doc.exists:
            starred_data = doc.to_dict().get("starred_topics", {})
            # Filter to only return starred items
            return {k: v for k, v in starred_data.items() if v.get("starred", False)}
        return {}
    except Exception as e:
        st.error(f"Error loading starred topics: {str(e)}")
        return {}

def unstar_topic(user_id, topic_id):
    """Remove a topic from starred topics"""
    try:
        db = get_db()
        user_ref = db.collection("user_topics").document(user_id)
        
        user_ref.update({
            f"starred_topics.{topic_id}": firestore.DELETE_FIELD
        })
        return True
    except Exception as e:
        st.error(f"Error unstarring topic: {str(e)}")
        return False

def initialize_user_topics(user_id):
    """Initialize a user's topics document if it doesn't exist"""
    try:
        db = get_db()
        user_ref = db.collection("user_topics").document(user_id)
        
        if not user_ref.get().exists:
            user_ref.set({
                "starred_topics": {},
                "created_at": datetime.datetime.now().isoformat()
            })
        return True
    except Exception as e:
        st.error(f"Error initializing user topics: {str(e)}")
        return False 