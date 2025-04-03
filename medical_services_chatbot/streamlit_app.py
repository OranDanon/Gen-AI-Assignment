"""
Medical Services Chatbot - Streamlit Frontend

This is the main Streamlit application that implements the Medical Services Chatbot.
It communicates with the FastAPI backend microservice to handle the core logic.
"""

import streamlit as st
from typing import Dict, Any, List
import json
import requests
import os
from dotenv import load_dotenv
from core.logging_config import configure_logging, get_logger
from core.monitoring import track_request, check_backend_health, start_metrics_server
import threading

# Load environment variables
load_dotenv()

# Configure logging
configure_logging()
logger = get_logger("streamlit_app")

# Configuration
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
METRICS_PORT = int(os.environ.get("METRICS_PORT", "8001"))

# Start metrics server in a separate thread
metrics_thread = threading.Thread(target=start_metrics_server, args=(METRICS_PORT,))
metrics_thread.daemon = True
metrics_thread.start()

# Set page config
st.set_page_config(
    page_title="Medical Services Chatbot",
    page_icon="🏥",
    layout="wide"
)

# Initialize session state
if 'language' not in st.session_state:
    st.session_state.language = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}
if 'is_qa_mode' not in st.session_state:
    st.session_state.is_qa_mode = False

# Define text based on language
texts = {
    "english": {
        "title": "Medical Services Chatbot",
        "welcome": "Welcome to the Medical Services Chatbot!",
        "select_language": "Please select your preferred language:",
        "chat_title": "Information Collection",
        "chat_placeholder": "Type your information here...",
        "clear": "Clear Chat",
        "error": "An error occurred. Please try again.",
        "qa_mode": "Q&A Mode",
        "info_mode": "Information Collection Mode",
        "connection_error": "Could not connect to the backend service. Please try again later.",
        "health_status": "System Health Status",
        "healthy": "System is healthy",
        "unhealthy": "System is unhealthy"
    },
    "hebrew": {
        "title": "צ'אטבוט שירותי רפואה",
        "welcome": "ברוכים הבאים לצ'אטבוט שירותי רפואה!",
        "select_language": "אנא בחר את השפה המועדפת שלך:",
        "chat_title": "איסוף מידע",
        "chat_placeholder": "הקלד את המידע שלך כאן...",
        "clear": "נקה צ'אט",
        "error": "אירעה שגיאה. אנא נסה שוב.",
        "qa_mode": "מצב שאלות ותשובות",
        "info_mode": "מצב איסוף מידע",
        "connection_error": "לא ניתן להתחבר לשירות האחורי. אנא נסה שוב מאוחר יותר.",
        "health_status": "סטטוס בריאות המערכת",
        "healthy": "המערכת תקינה",
        "unhealthy": "המערכת לא תקינה"
    }
}

def get_current_texts():
    """Get the current language texts"""
    return texts[st.session_state.language] if st.session_state.language else texts["english"]

@track_request("welcome_message")
def api_get_welcome_message(language: str) -> str:
    """Get welcome message from API"""
    try:
        response = requests.get(f"{API_BASE_URL}/welcome-message/{language}")
        if response.status_code == 200:
            data = response.json()
            logger.info("welcome_message_retrieved", language=language)
            return data["message"]
        else:
            logger.error("welcome_message_error", 
                        status_code=response.status_code, 
                        response=response.text)
            st.error(f"Error: {response.status_code} - {response.text}")
            return "Sorry, couldn't get welcome message. Please try again."
    except requests.exceptions.RequestException as e:
        logger.error("welcome_message_connection_error", error=str(e))
        st.error(f"Connection error: {str(e)}")
        return get_current_texts()["connection_error"]

@track_request("process_input")
def api_process_user_input(user_input: str, chat_history: List[Dict[str, str]], language: str) -> Dict[str, Any]:
    """Process user input via API"""
    try:
        payload = {
            "user_input": user_input,
            "chat_history": chat_history,
            "language": language
        }
        response = requests.post(f"{API_BASE_URL}/process-input", json=payload)
        if response.status_code == 200:
            logger.info("user_input_processed", language=language)
            return response.json()
        else:
            logger.error("process_input_error", 
                        status_code=response.status_code, 
                        response=response.text)
            st.error(f"Error: {response.status_code} - {response.text}")
            return {"role": "assistant", "content": get_current_texts()["error"]}
    except requests.exceptions.RequestException as e:
        logger.error("process_input_connection_error", error=str(e))
        st.error(f"Connection error: {str(e)}")
        return {"role": "assistant", "content": get_current_texts()["connection_error"]}

@track_request("extract_user_info")
def api_extract_user_info(chat_history: List[Dict[str, str]], language: str) -> Dict[str, Any]:
    """Extract user info via API"""
    try:
        payload = {
            "chat_history": chat_history,
            "language": language
        }
        response = requests.post(f"{API_BASE_URL}/extract-user-info", json=payload)
        if response.status_code == 200:
            logger.info("user_info_extracted", language=language)
            return response.json()
        else:
            logger.error("extract_user_info_error", 
                        status_code=response.status_code, 
                        response=response.text)
            st.error(f"Error: {response.status_code} - {response.text}")
            return {}
    except requests.exceptions.RequestException as e:
        logger.error("extract_user_info_connection_error", error=str(e))
        st.error(f"Connection error: {str(e)}")
        return {}

@track_request("get_answer")
def api_get_answer(user_info: Dict[str, Any], question: str) -> str:
    """Get answer via API"""
    try:
        payload = {
            "user_info": user_info,
            "question": question
        }
        response = requests.post(f"{API_BASE_URL}/get-answer", json=payload)
        if response.status_code == 200:
            data = response.json()
            logger.info("answer_retrieved")
            return data["answer"]
        else:
            logger.error("get_answer_error", 
                        status_code=response.status_code, 
                        response=response.text)
            st.error(f"Error: {response.status_code} - {response.text}")
            return get_current_texts()["error"]
    except requests.exceptions.RequestException as e:
        logger.error("get_answer_connection_error", error=str(e))
        st.error(f"Connection error: {str(e)}")
        return get_current_texts()["connection_error"]

def display_health_status():
    """Display the health status of the system"""
    current_texts = get_current_texts()
    health_status = check_backend_health(API_BASE_URL)
    
    st.sidebar.title(current_texts["health_status"])
    if health_status["status"] == "healthy":
        st.sidebar.success(current_texts["healthy"])
    else:
        st.sidebar.error(current_texts["unhealthy"])
        if "error" in health_status:
            st.sidebar.error(f"Error: {health_status['error']}")

def display_language_selection():
    """Display the language selection interface"""
    current_texts = get_current_texts()
    display_health_status()

    # Create a centered layout
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.title(f"🏥 {current_texts['title']}")
        st.write(current_texts["select_language"])

        # Create two columns for language buttons
        lang_col1, lang_col2 = st.columns(2)

        with lang_col1:
            if st.button("English", use_container_width=True):
                st.session_state.language = "english"
                st.session_state.chat_history = []
                logger.info("language_selected", language="english")
                st.rerun()

        with lang_col2:
            if st.button("עברית", use_container_width=True):
                st.session_state.language = "hebrew"
                st.session_state.chat_history = []
                logger.info("language_selected", language="hebrew")
                st.rerun()

def display_chat_interface():
    """Display the chat interface for information collection"""
    current_texts = get_current_texts()
    display_health_status()

    st.title(f"🏥 {current_texts['title']}")

    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # If chat history is empty, display welcome message
    if not st.session_state.chat_history:
        if not st.session_state.is_qa_mode:
            welcome_message = api_get_welcome_message(st.session_state.language)
            st.session_state.chat_history.append({"role": "assistant", "content": welcome_message})
            with st.chat_message("assistant"):
                st.write(welcome_message)
        else:
            welcome_message = "Please ask your question about medical services."
            st.session_state.chat_history.append({"role": "assistant", "content": welcome_message})
            with st.chat_message("assistant"):
                st.write(welcome_message)

    # Chat input
    if prompt := st.chat_input(current_texts["chat_placeholder"]):
        # Add user message to chat history
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        logger.info("user_message_received", 
                   message_length=len(prompt),
                   is_qa_mode=st.session_state.is_qa_mode)

        # Display user message
        with st.chat_message("user"):
            st.write(prompt)

        if st.session_state.is_qa_mode:
            # Get answer from Q&A service
            if st.session_state.user_info:
                response = api_get_answer(st.session_state.user_info, prompt)
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                with st.chat_message("assistant"):
                    st.write(response)
            else:
                error_msg = "Please complete the information collection first."
                st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
                with st.chat_message("assistant"):
                    st.write(error_msg)
        else:
            # Get assistant response from API
            response = api_process_user_input(
                prompt,
                st.session_state.chat_history,
                st.session_state.language
            )
            
            # Check if this is a validation response
            if "is_validated" in response and response["is_validated"] == "True":
                # Extract user info and transition to Q&A mode
                st.session_state.user_info = api_extract_user_info(
                    st.session_state.chat_history,
                    st.session_state.language
                )
                st.session_state.is_qa_mode = True
                logger.info("transitioned_to_qa_mode")
                # Add a transition message
                transition_msg = {
                    "english": "Great! Your information has been confirmed. You can now ask questions about medical services.",
                    "hebrew": "מצוין! המידע שלך אושר. כעת תוכל לשאול שאלות על שירותים רפואיים."
                }
                response["content"] = transition_msg.get(st.session_state.language, transition_msg["english"])

            # Add response to chat history and display it
            st.session_state.chat_history.append(response)
            with st.chat_message("assistant"):
                st.write(response["content"])

def main():
    try:
        if not st.session_state.language:
            display_language_selection()
        else:
            display_chat_interface()
    except Exception as e:
        logger.error("application_error", error=str(e), exc_info=True)
        st.error("An unexpected error occurred. Please try again later.")

if __name__ == "__main__":
    main()