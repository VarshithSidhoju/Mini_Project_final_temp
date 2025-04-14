import groq
import streamlit as st

def load_model():
    try:
        client = groq.Client(api_key=st.secrets["groq_api_key"])
        return client
    except Exception as e:
        st.error(f"Error loading model: {e}")
        return None

def get_output(question):
    client = load_model()
    if client is None:
        return "Failed to load model."

    try:
        response = client.chat.completions.create(
            model="mistral-saba-24b",  # Changed model here
            messages=[{"role": "user", "content": question}]
        )
        return response.choices[0].message.content  
    except Exception as e:
        st.error(f"Error generating response: {e}")
        return "Error generating response."