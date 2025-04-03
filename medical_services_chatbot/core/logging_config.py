"""
Logging configuration for the Medical Services Chatbot
"""

import structlog
import logging
from pythonjsonlogger import jsonlogger
import sys
from typing import Any, Dict

def configure_logging() -> None:
    """Configure structured logging for the application"""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard logging to use JSON format
    json_handler = logging.StreamHandler(sys.stdout)
    json_handler.setFormatter(
        jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s'
        )
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(json_handler)
    root_logger.setLevel(logging.INFO)

    # Create logger instance
    logger = structlog.get_logger()
    logger.info("Logging configured successfully")

def get_logger(name: str) -> structlog.BoundLogger:
    """Get a logger instance with the given name"""
    return structlog.get_logger(name) 