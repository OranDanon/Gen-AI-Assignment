import json
import os
import re
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from openai import AzureOpenAI
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

# Hebrew-English mappings
HMO_MAPPING = {
    'Maccabi': 'מכבי',
    'Clalit': 'כללית',
    'Meuhedet': 'מאוחדת',
    'מכבי': 'מכבי',
    'כללית': 'כללית',
    'מאוחדת': 'מאוחדת'
}

TIER_MAPPING = {
    'Gold': 'זהב',
    'Silver': 'כסף',
    'Bronze': 'ארד',
    'זהב': 'זהב',
    'כסף': 'כסף',
    'ארד': 'ארד'
}

class QAService:
    def __init__(self):
        # Initialize the database
        self.services_db = {}
        self._initialize_database()
        self.client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
        )
    
    def _map_to_hebrew(self, hmo: str, tier: str) -> tuple[str, str]:
        """Map English HMO and tier names to Hebrew."""
        hebrew_hmo = HMO_MAPPING.get(hmo, hmo)
        hebrew_tier = TIER_MAPPING.get(tier, tier)
        return hebrew_hmo, hebrew_tier
    
    def _initialize_database(self):
        """Initialize the database by reading all HTML files and converting tables to dict structure"""
        services_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../phase2_data")
        if not os.path.exists(services_dir):
            raise FileNotFoundError(f"Services directory not found at: {services_dir}")
            
        for filename in os.listdir(services_dir):
            if filename.endswith("_services.html"):
                service_name = filename.replace("_services.html", "")
                file_path = os.path.join(services_dir, filename)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                soup = BeautifulSoup(html_content, 'html.parser')
                table = soup.find('table')
                if table:
                    self._parse_table(table, service_name)
    
    def _extract_tiers_from_html(self, cell) -> Dict[str, str]:
        """Extract tier information from a cell using regex."""
        # Get all the text content
        text_content = cell.get_text()
        
        # Split by newlines to get each tier line
        lines = [line.strip() for line in text_content.split('\n') if line.strip()]
        
        # Extract tier and description using regex
        tiers_dict = {}
        for line in lines:
            # Match pattern: <tier name>: <description>
            match = re.match(r'(\w+):\s*(.*)', line)
            if match:
                tier_name = match.group(1)
                description = match.group(2)
                tiers_dict[tier_name] = description
        
        return tiers_dict
    
    def _parse_table(self, table, service_name: str):
        """Parse HTML table into a nested dictionary structure organized by HMO and tier"""
        # Get headers (HMOs)
        headers = [th.text.strip() for th in table.find_all('th')[1:]]
        
        # Process each row
        for row in table.find_all('tr')[1:]:  # Skip header row
            cells = row.find_all('td')
            if not cells:
                continue
                
            service = cells[0].text.strip()
            
            # Process each HMO column
            for i, cell in enumerate(cells[1:]):
                hmo = headers[i]
                
                # Initialize HMO if not exists
                if hmo not in self.services_db:
                    self.services_db[hmo] = {}
                
                # Extract tiers and their descriptions
                tiers_dict = self._extract_tiers_from_html(cell)
                
                # Store benefits for each tier
                for tier, benefits in tiers_dict.items():
                    # Initialize tier if not exists
                    if tier not in self.services_db[hmo]:
                        self.services_db[hmo][tier] = {}
                    
                    # Store benefits under the service
                    if benefits and benefits != '':  # Only store if there are actual benefits
                        self.services_db[hmo][tier][service] = benefits
                    else:
                        self.services_db[hmo][tier][service] = "לא זמין"  # Mark as unavailable in Hebrew
    
    def _create_prompt(self, user_info: Dict[str, Any], question: str, relevant_data: Dict[str, Any]) -> str:
        """Create a prompt for GPT-4 with user info and relevant data"""
        prompt = f"""You are a helpful medical services assistant providing just question and answer responses. You have access to the following information about the user and their benefits:

User Information:
- Name: {user_info['first_name']} {user_info['last_name']}
- Age: {user_info['age']}
- Gender: {user_info['gender']}
- HMO: {user_info['hmo_name']}
- Membership Tier: {user_info['membership_tier']}

Relevant Benefits Information:
{json.dumps(relevant_data, indent=2, ensure_ascii=False)}

User Question: {question}

Please provide a clear and accurate answer based on the user's specific benefits. If the information is not available in the provided data, please say so. Format your response in a natural, conversational way while maintaining accuracy.

Answer:"""
        return prompt
    
    def _find_relevant_data(self, user_info: Dict[str, Any], question: str) -> Dict[str, Any]:
        """Find relevant data from the database based on the user's HMO and tier"""
        # Map English names to Hebrew if needed
        hmo, tier = self._map_to_hebrew(user_info['hmo_name'], user_info['membership_tier'])
        
        # Get all services for the user's HMO and tier
        if hmo in self.services_db and tier in self.services_db[hmo]:
            return self.services_db[hmo][tier]
        return {}
    
    def get_answer(self, user_info: Dict[str, Any], question: str) -> str:
        """Get an answer to the user's question using GPT-4"""
        # Find relevant data from the database
        relevant_data = self._find_relevant_data(user_info, question)
        
        if not relevant_data:
            return "I apologize, but I couldn't find specific information about your question in the available data. Please try rephrasing your question or contact your HMO directly for more information."
        
        # Create the prompt
        prompt = self._create_prompt(user_info, question, relevant_data)
        
        try:
            # Call Azure OpenAI API
            response = self.client.chat.completions.create(
                model=GPT_MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a helpful medical services chatbot that provides accurate information about medical benefits based on the user's HMO and membership tier."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"I apologize, but I encountered an error while processing your request: {str(e)}" 