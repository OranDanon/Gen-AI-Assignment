# main.py
"""
Medical Services Chatbot - FastAPI Backend

This is the main FastAPI application that serves as the backend for the
Medical Services Chatbot. It handles user information collection and Q&A services.
"""

import os
from typing import List, Dict, Any
import time
import psutil

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.qa_service import QAService
from core.user_info_gathering_agent import UserInfoCollector
from core.logging_config import get_logger

# Load environment variables
load_dotenv()

# Initialize logger
logger = get_logger("fastapi_backend")

# Initialize the FastAPI app
app = FastAPI(
    title="Medical Services Chatbot API",
    description="API for the Medical Services Chatbot",
    version="1.0.0"
)

# Add CORS middleware to allow requests from Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize our services
user_info_collector = UserInfoCollector()
qa_service = QAService()

# Track service start time
START_TIME = time.time()

# Define request models
class ChatMessage(BaseModel):
    role: str
    content: str

class ProcessUserInputRequest(BaseModel):
    user_input: str
    chat_history: List[Dict[str, str]]
    language: str

class ExtractUserInfoRequest(BaseModel):
    chat_history: List[Dict[str, str]]
    language: str

class GetAnswerRequest(BaseModel):
    user_info: Dict[str, Any]
    question: str

class HealthStatus(BaseModel):
    status: str
    version: str
    uptime_seconds: float
    memory_usage_percent: float
    cpu_usage_percent: float

# Define endpoints
@app.get("/")
async def root():
    return {"message": "Medical Services Chatbot API is running"}

@app.get("/health")
async def health_check() -> HealthStatus:
    """Health check endpoint that returns system status"""
    try:
        # Get system metrics
        memory = psutil.Process().memory_percent()
        cpu = psutil.Process().cpu_percent()
        uptime = time.time() - START_TIME

        status = HealthStatus(
            status="healthy",
            version=app.version,
            uptime_seconds=uptime,
            memory_usage_percent=memory,
            cpu_usage_percent=cpu
        )

        logger.info("health_check", 
                   status=status.status,
                   uptime=uptime,
                   memory=memory,
                   cpu=cpu)
        
        return status
    except Exception as e:
        logger.error("health_check_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )

@app.get("/welcome-message/{language}")
async def get_welcome_message(language: str):
    """Get the welcome message in the specified language"""
    return {"message": user_info_collector.get_welcome_message(language)}

@app.post("/process-input")
async def process_user_input(request: ProcessUserInputRequest):
    """Process user input and return appropriate response"""
    try:
        response = user_info_collector.process_user_input(
            request.user_input,
            request.chat_history,
            request.language
        )
        return response
    except Exception as e:
        logger.error("process_input_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Error processing input: {str(e)}")

@app.post("/extract-user-info")
async def extract_user_info(request: ExtractUserInfoRequest):
    """Extract structured user information from chat history"""
    try:
        user_info = user_info_collector.extract_user_info(
            request.chat_history,
            request.language
        )
        return user_info
    except Exception as e:
        logger.error("extract_user_info_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Error extracting user info: {str(e)}")

@app.post("/get-answer")
async def get_answer(request: GetAnswerRequest):
    """Get an answer to the user's question using the QA service"""
    try:
        answer = qa_service.get_answer(
            request.user_info,
            request.question
        )
        return {"answer": answer}
    except Exception as e:
        logger.error("get_answer_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Error getting answer: {str(e)}")

# Run the server
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)