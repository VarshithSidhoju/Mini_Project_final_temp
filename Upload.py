import streamlit as st
import os
from langchain_community.document_loaders import PyPDFLoader

# Process user input (uploaded file or custom topic)
def process_input(uploaded_file, custom_topic):
    # Reset previous session state for input
    st.session_state.custom_topic = None
    st.session_state.file_content = None
    st.session_state.uploaded_file = None

    if uploaded_file:
        # Check if the file is a PDF
        if uploaded_file.type == "application/pdf":
            try:
                # Save the file temporarily
                file_path = f"temp/{uploaded_file.name}"
                os.makedirs("temp", exist_ok=True)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # Extract text from PDF using LangChain's PyPDFLoader
                loader = PyPDFLoader(file_path)
                documents = loader.load()
                text = "".join(doc.page_content for doc in documents)
                
                # Store the extracted text as file_content
                st.session_state.file_content = text
                st.session_state.uploaded_file = file_path
                
                # If no custom topic is provided, use the extracted text as the topic
                if not custom_topic:
                    st.session_state.custom_topic = text
                else:
                    st.session_state.custom_topic = custom_topic
                
                st.success("PDF uploaded and text extracted successfully!")
            except Exception as e:
                st.error(f"Error extracting text from PDF: {str(e)}")
        else:
            # Handle non-PDF files (e.g., txt, docx)
            try:
                file_path = f"temp/{uploaded_file.name}"
                os.makedirs("temp", exist_ok=True)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                text = uploaded_file.read().decode("utf-8", errors="ignore")
                st.session_state.file_content = text
                st.session_state.uploaded_file = file_path
                
                # If no custom topic is provided, use the file content as the topic
                if not custom_topic:
                    st.session_state.custom_topic = text
                else:
                    st.session_state.custom_topic = custom_topic
                
                st.success("File uploaded and content extracted successfully!")
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
    
    elif custom_topic:
        # If only a manual topic is provided
        st.session_state.custom_topic = custom_topic
    
    if st.session_state.custom_topic or st.session_state.uploaded_file:
        st.session_state.page = "options"
        st.rerun()
    else:
        st.warning("⚠️ Please upload a file or enter a topic!")