"""
Netlify Function: Get Leads
Retrieves leads from Google Sheets for dashboard display.
"""
import json
import os
from typing import List, Dict, Any
import gspread
from google.oauth2.service_account import Credentials

def handler(event, context):
    """
    Netlify function handler for retrieving leads.

    Supports query parameters:
    - status: Filter by status (sent, replied, etc.)
    - limit: Maximum number of leads to return (default: 100)
    - offset: Number of leads to skip (default: 0)
    """
    try:
        # Only allow GET requests
        if event['httpMethod'] != 'GET':
            return {
                'statusCode': 405,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Method not allowed'})
            }

        # Parse query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        status_filter = query_params.get('status')
        limit = int(query_params.get('limit', 100))
        offset = int(query_params.get('offset', 0))

        # Connect to Google Sheets
        creds = Credentials.from_service_account_file(
            os.environ.get('GOOGLE_SHEETS_CREDENTIALS_PATH', 'credentials.json'),
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(os.environ['GOOGLE_SHEETS_SPREADSHEET_ID'])
        worksheet = spreadsheet.worksheet(os.environ.get('GOOGLE_SHEETS_WORKSHEET_NAME', 'Leads'))

        # Get all data
        all_data = worksheet.get_all_records()

        # Apply filters
        filtered_data = all_data
        if status_filter:
            filtered_data = [row for row in all_data if row.get('Status', '').lower() == status_filter.lower()]

        # Apply pagination
        paginated_data = filtered_data[offset:offset + limit]

        # Format response
        leads = []
        for row in paginated_data:
            lead = {
                'email': row.get('Email', ''),
                'company': row.get('Company', ''),
                'industry': row.get('Industry', ''),
                'source': row.get('Source', ''),
                'score': row.get('Score', ''),
                'status': row.get('Status', ''),
                'sent_date': row.get('Sent_Date', ''),
                'reply': row.get('Reply', ''),
                'notes': row.get('Notes', '')
            }
            leads.append(lead)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'leads': leads,
                'total_count': len(filtered_data),
                'returned_count': len(leads),
                'offset': offset,
                'limit': limit
            })
        }

    except Exception as e:
        print(f"Error retrieving leads: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Internal server error'})
        }