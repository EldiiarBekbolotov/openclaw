"""
Configuration management for Hack United Sponsorship Outreach System.
Loads environment variables and provides typed configuration.
"""
import os
import json
from typing import Optional
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration with environment variables."""

    # Groq API Configuration
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL_MIXTRAL: str = os.getenv("GROQ_MODEL_MIXTRAL", "mixtral-8x7b-32768")
    GROQ_MODEL_LLAMA: str = os.getenv("GROQ_MODEL_LLAMA", "llama3-8b-8192")

    # Google Sheets Configuration
    GOOGLE_SHEETS_CREDENTIALS_PATH: str = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH", "credentials.json")
    GOOGLE_SHEETS_CREDENTIALS_JSON: str = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON", "")
    GOOGLE_SHEETS_SPREADSHEET_ID: str = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")
    GOOGLE_SHEETS_WORKSHEET_NAME: str = os.getenv("GOOGLE_SHEETS_WORKSHEET_NAME", "Leads")

    # Gmail SMTP Configuration
    GMAIL_USERNAME: str = os.getenv("GMAIL_USERNAME", "")
    GMAIL_APP_PASSWORD: str = os.getenv("GMAIL_APP_PASSWORD", "")

    # Deployment URLs
    RAILWAY_STATIC_URL: Optional[str] = os.getenv("RAILWAY_STATIC_URL")
    NETLIFY_SITE_URL: Optional[str] = os.getenv("NETLIFY_SITE_URL")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls) -> None:
        """Validate that all required environment variables are set."""
        required_vars = [
            "GROQ_API_KEY",
            "GOOGLE_SHEETS_SPREADSHEET_ID",
            "GMAIL_USERNAME",
            "GMAIL_APP_PASSWORD"
        ]

        missing = [var for var in required_vars if not getattr(cls, var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    @classmethod
    def get_google_credentials(cls) -> Credentials:
        """Load Google Sheets service account credentials from JSON env or file path."""
        if cls.GOOGLE_SHEETS_CREDENTIALS_JSON:
            credentials_info = json.loads(cls.GOOGLE_SHEETS_CREDENTIALS_JSON)
            return Credentials.from_service_account_info(
                credentials_info,
                scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )

        return Credentials.from_service_account_file(
            cls.GOOGLE_SHEETS_CREDENTIALS_PATH,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )

# Global config instance
config = Config()