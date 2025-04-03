"""
Azure OpenAI Integration Module

This module handles all interactions with Azure OpenAI services, including
information collection and Q&A functionality.
"""

import os
from typing import Dict, Any, List
from openai import AzureOpenAI
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.environ.get("AZURE_OPENAI_KEY")
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_API_VERSION")

# Model names
GPT_MODEL_NAME = "gpt-4o"
GPT_MINI_MODEL_NAME = "gpt-4o-mini"
EMBEDDING_MODEL_NAME = "text-embedding-ada-002"

# Confirmation Phases
CONFIRM_PHASES = {
    "hebrew": "כל הפרטים נרשמו בהצלחה",
    "english": "Thank you for confirming all the details collected successfully"
}

class UserInfoCollector:
    def __init__(self):
        """Initialize Azure OpenAI client with credentials"""
        self.client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
        )
        self.deployment_name = GPT_MODEL_NAME

    def get_welcome_message(self, language: str) -> str:
        """Get the welcome message based on language"""
        messages = {
            "english": """Hello! I'm your Medical Services Assistant. I'll help you with information about medical services in Israel.

I'll need some information from you to provide personalized assistance:
- First Name
- Last Name
- ID Number
- Gender (Male/Female)
- Age
- HMO Name (Maccabi/Meuhedet/Clalit)
- HMO Card Number
- Insurance membership tier (Gold/Silver/Bronze)

I'll collect this information through a friendly conversation. Please provide the information as I ask for it, and I'll help ensure it's correct.

Let's begin! What's your first name?""",
            
            "hebrew": """שלום! אני העוזר שלך לשירותי רפואה. אני אעזור לך עם מידע על שירותי רפואה בישראל.

אני אצטרך כמה פרטים ממך כדי לספק סיוע מותאם אישית:
- שם פרטי
- שם משפחה
- מספר זהות
- מין (זכר/נקבה)
- גיל
- שם קופת חולים (מכבי/כללית/מאוחדת)
- מספר כרטיס קופת חולים
- דרגת חברות (זהב/כסף/ארד)

אני אאסוף את המידע הזה דרך שיחה ידידותית. אנא ספק את המידע כשאני מבקש אותו, ואני אעזור לוודא שהוא נכון.

בואו נתחיל! מה שמך הפרטי?"""
        }
        return messages.get(language, messages["english"])

    def get_information_collection_prompt(self, language: str) -> str:
        """Get the appropriate prompt for information collection based on language"""
        prompts = {
            "english": """You are a helpful assistant collecting user information for medical services.
Please collect the following information in a conversational manner:
- First and last name (characters only  )
- ID number (9 digits)
- Gender (Male/Female)
- Age (number between 0 and 120)
- HMO name (Maccabi/Meuhedet/Clalit)
- HMO card number (9 digits)
- Insurance membership tier (Gold/Silver/Bronze)

Ask for one piece of information at a time in a friendly way.
If the information seems incorrect or incomplete, ask the user to clarify or provide it again.
Once all information is collected, display it in a structured format for confirmation by asking explicitly: "Is all the information correct?"
Once approved response by: "Thank you for confirming all the details collected successfully."
""",

            "hebrew": """אתה עוזר שמאסוף מידע משתמש עבור שירותי רפואה.
אנא אסוף את המידע הבא בצורה שיחה:
- שם פרטי ושם משפחה (אותיות בלבד)
- מספר זהות (9 ספרות)
- מין (זכר/אישה)
- גיל (מספר בין 0 ל-120)
- שם קופת חולים (מכבי/כללית/מאוחדת)
- מספר כרטיס קופת חולים (9 ספרות)
- דרגת חברות (זהב/כסף/ארד)

שאל על פריט מידע אחד בכל פעם בצורה ידידותית.
אם המידע נראה שגוי או לא מלא, בקש מהמשתמש להבהיר או לספק אותו שוב.
לאחר איסוף כל המידע, הצג אותו בפורמט מסודר לאישור ע"י שימוש בביטוי הבא: "האם כל הפרטים נכונים? אם המשתמש אישר רשום: "כל הפרטים נרשמו בהצלחה!"
"""
        }
        return prompts.get(language, prompts["english"])

    def process_user_input(self, user_input: str, chat_history: List[Dict[str, str]], language: str) -> Dict[str, Any]:
        """Process user input and return appropriate response"""
        messages = [
            {"role": "system", "content": self.get_information_collection_prompt(language)},
            *chat_history,
            {"role": "user", "content": user_input}
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                temperature=0,
                max_tokens=800
            )
            
            content = response.choices[0].message.content

            # Check if this is a validation response
            is_valid = CONFIRM_PHASES.get(language).strip() in content.strip()
            
            return {
                "content": content,
                "role": "assistant",
                "is_validated": str(is_valid)
            }
        except Exception as e:
            return {
                "content": f"Error processing request: {str(e)}",
                "role": "assistant"
            }

    def extract_user_info(self, chat_history: List[Dict[str, str]], language: str) -> Dict[str, Any]:
        """Extract structured user information from chat history"""
        system_prompt = """Extract user information from the conversation and return it in the following strict JSON format:
{
    "first_name": "string",
    "last_name": "string",
    "id_number": "string",
    "gender": "string",
    "age": "number",
    "hmo_name": "string",
    "hmo_card_number": "string",
    "membership_tier": "string"
}

IMPORTANT:
1. Return ONLY the JSON object, no additional text or explanation
2. All fields must be present
3. Use null for any missing values
4. Ensure the response is valid JSON
5. Do not include any comments or markdown formatting"""

        messages = [
            {"role": "system", "content": system_prompt},
            *chat_history,
            {"role": "user", "content": "Extract the information and return only JSON"}
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                temperature=0,
                max_tokens=800,
                response_format={"type": "json_object"}  # Force JSON response format
            )
            
            # Parse the response to get structured data
            content = response.choices[0].message.content
            try:
                parsed_data = json.loads(content)
                # Validate required fields
                required_fields = ["first_name", "last_name", "id_number", "gender", 
                                 "age", "hmo_name", "hmo_card_number", "membership_tier"]
                if all(field in parsed_data for field in required_fields):
                    return parsed_data
                else:
                    return {}
            except json.JSONDecodeError:
                return {}
        except Exception as e:
            return {} 