# ocr_processor.py
import logging
import os
from typing import Union, BinaryIO
from io import BytesIO

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import DocumentContentFormat
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError

import config

logger = logging.getLogger(__name__)

# Lazy initialization pattern
_document_client = None


def get_document_client():
    """
    Lazily initialize and return the Document Intelligence client.
    Client is created only on first use and reused for subsequent calls.
    """
    global _document_client
    if _document_client is None:
        try:
            _document_client = DocumentIntelligenceClient(
                endpoint=config.DOCUMENT_INTELLIGENCE_ENDPOINT,
                credential=AzureKeyCredential(config.DOCUMENT_INTELLIGENCE_KEY)
            )
            logger.info("DocumentIntelligenceClient initialized successfully")
        except ValueError as e:
            logger.error("Error creating DocumentIntelligenceClient", exc_info=True)
            raise ValueError(f"Error creating DocumentIntelligenceClient: {e}")
    return _document_client


def analyze_document(document_source):
    """Analyze a document using Azure Document Intelligence."""
    client = get_document_client()
    try:
        logger.debug("Sending document to Azure Document Intelligence for analysis.")
        poller = client.begin_analyze_document(
            "prebuilt-layout",
            document_source,
            output_content_format=DocumentContentFormat.MARKDOWN,
            pages="1"
        )
        result = poller.result()
        logger.info("Successfully received OCR results from Document Intelligence.")
        return result
    except HttpResponseError as e:
        logger.error(f"Azure API error: {str(e)}", exc_info=True)
        if hasattr(e, 'status_code'):
            logger.error(f"Status code: {e.status_code}")
        if hasattr(e, 'reason'):
            logger.error(f"Reason: {e.reason}")
        if hasattr(e, 'error'):
            logger.error(f"Error details: {e.error}")
        raise ValueError(f"Azure Document Intelligence API error: {str(e)}")
    except Exception as e:
        logger.error(f"Error during OCR analysis: {str(e)}", exc_info=True)
        raise ValueError(f"OCR processing error: {str(e)}")


def format_ocr_result(result):
    """Format the OCR result into a structured text output."""
    text_content = []
    text_content.append("# Text File #")
    for page in result.pages:
        for line in page.lines:
            text_content.append(line.content)
    text_content.append(f"""\pagebreak""")
    text_content.append("# MarkDown File #")
    text_content.append(result.content)
    full_text = "\n".join(text_content)
    logger.debug(f"OCR extracted text length: {len(full_text)} characters")
    return full_text


def process(file_input: Union[str, BinaryIO]):
    """
    Process a document using Azure Document Intelligence OCR.

    Args:
        file_input: Either a file path string or a file-like object

    Returns:
        Extracted text content as a string
    """
    # For Streamlit uploads, we need to reset the file position
    if hasattr(file_input, 'seek') and not isinstance(file_input, str):
        file_input.seek(0)

    try:
        if isinstance(file_input, str):
            logger.info(f"Starting OCR on file path: {file_input}")
            with open(file_input, "rb") as fd:
                result = analyze_document(fd)
        else:
            # Get file details for better logging
            filename = getattr(file_input, 'name', 'uploaded file')
            file_size = getattr(file_input, 'size', 'unknown size')
            logger.info(f"Starting OCR on uploaded file: {filename} ({file_size} bytes)")
            result = analyze_document(file_input)

        return format_ocr_result(result)
    except Exception as e:
        logger.error(f"Process error: {str(e)}")
        raise

if __name__ == "__main__":
    file_paths = ["test_files\\raw\\283_raw.pdf",
                  "test_files\\283_ex1.pdf",
                  "test_files\\283_ex2.pdf",
                  "test_files\\283_ex3.pdf"]
    for path in file_paths:
        extracted_md = process(path)
        md_path = path.replace(".pdf",".md")
        with open(md_path, 'w', encoding='utf-8') as file:
            file.write(extracted_md)