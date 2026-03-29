"""
Netlify Function: Add Manual Lead
Allows manual addition of leads to the Google Sheets database.
"""
import json
import os
from typing import Dict, Any
import gspread
from google.oauth2.service_account import Credentials

def handler(event, context):
    """
    Netlify function handler for adding manual leads.

    Expected POST body:
    {
        "email": "contact@company.com",
        "company": "Company Name",
        "industry": "Technology",
        "source": "Manual entry",
        "website": "https://company.com",
        "description": "Company description"
    }
    """
    try:
        # Only allow POST requests
        if event['httpMethod'] != 'POST':
            return {
                'statusCode': 405,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Method not allowed'})
            }

        # Parse request body
        try:
            data = json.loads(event['body'])
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Invalid JSON body'})
            }

        # Validate required fields
        required_fields = ['email', 'company']
        for field in required_fields:
            if field not in data:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': f'Missing required field: {field}'})
                }

        # Validate email format (basic)
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, data['email']):
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Invalid email format'})
            }

        # Connect to Google Sheets
        creds = Credentials.from_service_account_file(
            os.environ.get('GOOGLE_SHEETS_CREDENTIALS_PATH', 'credentials.json'),
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(os.environ['GOOGLE_SHEETS_SPREADSHEET_ID'])
        worksheet = spreadsheet.worksheet(os.environ.get('GOOGLE_SHEETS_WORKSHEET_NAME', 'Leads'))

        # Check if lead already exists
        existing_emails = worksheet.col_values(1)  # Email column
        if data['email'] in existing_emails:
            return {
                'statusCode': 409,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Lead with this email already exists'})
            }

        # Prepare row data
        from datetime import datetime
        row_data = [
            data['email'],
            data['company'],
            data.get('industry', ''),
            data.get('source', 'Manual entry'),
            '',  # Score (to be calculated later)
            'manual',  # Status
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # Added date
            '',  # Reply
            data.get('description', '')  # Notes
        ]

        # Add to sheet
        worksheet.append_row(row_data)

        return {
            'statusCode': 201,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'message': 'Lead added successfully',
                'lead': {
                    'email': data['email'],
                    'company': data['company'],
                    'industry': data.get('industry', ''),
                    'source': data.get('source', 'Manual entry')
                }
            })
        }

    except Exception as e:
        print(f"Error adding lead: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Internal server error'})
        }