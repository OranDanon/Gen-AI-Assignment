"""
Data Models Module

This module defines the Pydantic models used for request validation and 
data structure throughout the application. It ensures that the data 
exchanged between the frontend and backend follows a consistent schema.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class UserInfo(BaseModel):
    """
    Pydantic model for user information and conversation history.
    
    This model defines the structure of the data sent from the frontend to the backend,
    including all user personal details and their conversation history.
    
    All fields are optional because they may be filled in gradually during
    the information collection phase.
    """
    first_name: str = ""
    last_name: str = ""
    id_number: str = ""
    gender: str = ""
    age: int = 0
    hmo_name: str = ""
    hmo_card_number: str = ""
    membership_tier: str = ""
    conversation_history: List[Dict[str, Any]] = []

class ValidationDetails(BaseModel):
    """ Pydantic model for validation details"""
    first_name: str = Field(default="", description="Error message if invalid, empty string if valid")
    last_name: str = Field(default="", description="Error message if invalid, empty string if valid")
    id_number: str = Field(default="", description="Error message if invalid, empty string if valid")
    gender: str = Field(default="", description="Error message if invalid, empty string if valid")
    age: str = Field(default="", description="Error message if invalid, empty string if valid")
    hmo_name: str = Field(default="", description="Error message if invalid, empty string if valid")
    hmo_card_number: str = Field(default="", description="Error message if invalid, empty string if valid")
    membership_tier: str = Field(default="", description="Error message if invalid, empty string if valid")

class FormValidation(BaseModel):
    """
    Validation rules:
    - Full name: letters only
    - ID number: 9 digits
    - Gender: Male/Female
    - Age: number between 0 and 120
    - HMO name: Maccabi/Meuhedet/Clalit
    - HMO card number: 9 digits
    - HMO membership tier: Gold/Silver/Bronze
    """
    is_valid: bool = Field(description="Whether the form is valid or not")
    general_message: str = Field(description="General message about the form validation status")
    validation_details: ValidationDetails = Field(description="Validation details for each field") 