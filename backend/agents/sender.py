"""
Email Sender Agent for Hack United Sponsorship Outreach.
Handles Gmail SMTP sending and Google Sheets logging.
"""
import logging
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, TypedDict, Optional
from datetime import datetime
import gspread
from backend.config import config

logger = logging.getLogger(__name__)

class EmailData(TypedDict):
    """Structure for email to be sent."""
    to_email: str
    subject: str
    body: str
    lead_company: str
    lead_score: int

class SendResult(TypedDict):
    """Structure for email send result."""
    success: bool
    message_id: Optional[str]
    error: Optional[str]

class EmailSender:
    """Agent responsible for sending emails and logging to Google Sheets."""

    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self._sheets_client = None
        self._worksheet = None

    def send_email(self, email_data: EmailData, max_retries: int = 3) -> SendResult:
        """
        Send an email via Gmail SMTP with retry logic.

        Args:
            email_data: Email content and recipient information
            max_retries: Maximum number of retry attempts

        Returns:
            SendResult indicating success/failure
        """
        for attempt in range(max_retries):
            try:
                # Create message
                msg = MIMEMultipart()
                msg['From'] = config.GMAIL_USERNAME
                msg['To'] = email_data['to_email']
                msg['Subject'] = email_data['subject']

                # Add body
                msg.attach(MIMEText(email_data['body'], 'plain'))

                # Send email
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
                server.login(config.GMAIL_USERNAME, config.GMAIL_APP_PASSWORD)
                text = msg.as_string()
                server.sendmail(config.GMAIL_USERNAME, email_data['to_email'], text)
                server.quit()

                message_id = f"{email_data['to_email']}_{int(time.time())}"

                # Log to Google Sheets
                self._log_to_sheets(email_data, "sent", message_id)

                logger.info(f"Email sent successfully to {email_data['to_email']}")

                return SendResult(
                    success=True,
                    message_id=message_id,
                    error=None
                )

            except Exception as e:
                error_msg = f"Attempt {attempt + 1} failed: {str(e)}"
                logger.warning(error_msg)

                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    # Log failure to sheets
                    self._log_to_sheets(email_data, "failed", error=str(e))
                    return SendResult(
                        success=False,
                        message_id=None,
                        error=str(e)
                    )

    def _log_to_sheets(self, email_data: EmailData, status: str, message_id: Optional[str] = None, error: Optional[str] = None) -> None:
        """
        Log email activity to Google Sheets.

        Args:
            email_data: Email information
            status: Status of the email (sent/failed)
            message_id: Unique message identifier
            error: Error message if failed
        """
        try:
            worksheet = self._get_worksheet()

            # Find existing row or create new one
            email_col = self._find_column_index("Email")
            if email_col is None:
                logger.error("Could not find Email column in Google Sheets")
                return

            # Check if email already exists
            existing_row = self._find_row_by_email(email_data['to_email'])
            if existing_row:
                # Update existing row
                row_num = existing_row
            else:
                # Add new row
                row_num = len(worksheet.get_all_values()) + 1

            # Prepare row data
            row_data = [
                email_data['to_email'],
                email_data['lead_company'],
                "",  # Industry (to be filled manually)
                "",  # Source (to be filled manually)
                email_data['lead_score'],
                status,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S") if status == "sent" else "",
                "",  # Reply status
                error or ""  # Notes
            ]

            # Update the row
            start_col = chr(ord('A') + email_col)  # Convert index to letter
            end_col = chr(ord('A') + email_col + len(row_data) - 1)
            cell_range = f"{start_col}{row_num}:{end_col}{row_num}"

            worksheet.update(cell_range, [row_data])

            logger.info(f"Logged {status} email to Google Sheets for {email_data['to_email']}")

        except Exception as e:
            logger.error(f"Failed to log to Google Sheets: {str(e)}")

    def _get_worksheet(self):
        """Get or create Google Sheets worksheet connection."""
        if self._worksheet is None:
            try:
                creds = config.get_google_credentials()
                self._sheets_client = gspread.authorize(creds)
                spreadsheet = self._sheets_client.open_by_key(config.GOOGLE_SHEETS_SPREADSHEET_ID)
                self._worksheet = spreadsheet.worksheet(config.GOOGLE_SHEETS_WORKSHEET_NAME)
            except Exception as e:
                logger.error(f"Failed to connect to Google Sheets: {str(e)}")
                raise

        return self._worksheet

    def _find_column_index(self, column_name: str) -> Optional[int]:
        """Find the column index for a given column name."""
        try:
            headers = self._worksheet.row_values(1)
            for i, header in enumerate(headers):
                if header.lower() == column_name.lower():
                    return i
        except Exception as e:
            logger.error(f"Error finding column {column_name}: {str(e)}")
        return None

    def _find_row_by_email(self, email: str) -> Optional[int]:
        """Find the row number for a given email address."""
        try:
            email_col = self._find_column_index("Email")
            if email_col is None:
                return None

            col_letter = chr(ord('A') + email_col)
            email_values = self._worksheet.col_values(email_col + 1)  # 1-indexed

            for i, cell_value in enumerate(email_values):
                if cell_value == email:
                    return i + 1  # 1-indexed row number

        except Exception as e:
            logger.error(f"Error finding row for email {email}: {str(e)}")
        return None