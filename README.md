# GenAI Developer Assessment Projects

This repository contains two projects:

### 1. [Medical Q&A Bot](./Medical_Q&A_Bot)

A microservice-based chatbot system that answers questions about medical services for Israeli HMOs (Maccabi, Meuhedet, and Clalit) based on user-specific information.

**Key Features:**
- Bilingual support (Hebrew/English with RTL handling)
- Two-phase interaction: information collection followed by personalized Q&A
- Stateless microservice architecture with FastAPI backend and Streamlit frontend
- Integration with Azure OpenAI GPT-4o and FAISS vector database
- Tailored responses based on user's HMO and membership tier

**Technologies:**
- Azure OpenAI
- FastAPI
- Streamlit
- FAISS vector database

### 2. [National Insurance Form Extraction](./Field_Extraction)

A document processing system designed to extract specific fields from National Insurance Institute (ביטוח לאומי) forms in both Hebrew and English.

**Key Features:**
- OCR processing of PDF and image files
- Intelligent field extraction using Azure OpenAI
- Data validation against predefined schemas
- User-friendly Streamlit interface

**Technologies:**
- Azure Document Intelligence
- Azure OpenAI
- Streamlit
- Pydantic

## Getting Started

Each project has its own detailed README with specific setup instructions:

- [Medical Q&A Bot Documentation](./medical_services_chatbot/README.md)
- [National Insurance Form Extraction Documentation](./national_insurance_extractor/README.md)

## Assignment Specifications
For the complete project requirements, refer to [assignment.md](assignment.md).
