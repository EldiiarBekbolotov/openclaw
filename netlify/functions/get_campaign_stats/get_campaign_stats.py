"""
Netlify Function: Get Campaign Statistics
Calculates and returns campaign performance metrics from Google Sheets data.
"""
import json
import os
from typing import Dict, Any
from collections import defaultdict
import gspread
from google.oauth2.service_account import Credentials

def handler(event, context):
    """
    Netlify function handler for retrieving campaign statistics.

    Returns metrics like:
    - Total leads
    - Emails sent
    - Reply rate
    - Bounce rate
    - Leads by industry
    - Performance over time
    """
    try:
        # Only allow GET requests
        if event['httpMethod'] != 'GET':
            return {
                'statusCode': 405,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Method not allowed'})
            }

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

        # Calculate statistics
        stats = calculate_campaign_stats(all_data)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(stats)
        }

    except Exception as e:
        print(f"Error retrieving campaign stats: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Internal server error'})
        }

def calculate_campaign_stats(data: list) -> Dict[str, Any]:
    """Calculate campaign statistics from the leads data."""
    total_leads = len(data)

    # Status counts
    status_counts = defaultdict(int)
    industry_counts = defaultdict(int)
    source_counts = defaultdict(int)

    sent_count = 0
    replied_count = 0
    bounced_count = 0

    scores = []
    sent_dates = []

    for row in data:
        status = row.get('Status', '').lower()
        status_counts[status] += 1

        industry = row.get('Industry', '')
        if industry:
            industry_counts[industry] += 1

        source = row.get('Source', '')
        if source:
            source_counts[source] += 1

        # Count sent emails
        if status == 'sent':
            sent_count += 1

        # Count replies
        reply = row.get('Reply', '').lower()
        if reply and reply != 'no':
            replied_count += 1

        # Count bounces (assuming 'bounced' or 'failed' status)
        if status in ['bounced', 'failed']:
            bounced_count += 1

        # Collect scores
        score_str = row.get('Score', '')
        if score_str and score_str.isdigit():
            scores.append(int(score_str))

        # Collect sent dates for timeline
        sent_date = row.get('Sent_Date', '')
        if sent_date:
            sent_dates.append(sent_date)

    # Calculate rates
    reply_rate = (replied_count / sent_count * 100) if sent_count > 0 else 0
    bounce_rate = (bounced_count / sent_count * 100) if sent_count > 0 else 0

    # Average score
    avg_score = sum(scores) / len(scores) if scores else 0

    # Recent activity (last 7 days - simplified)
    recent_activity = len([d for d in sent_dates if d])  # Simplified - in real app, parse dates

    return {
        'total_leads': total_leads,
        'emails_sent': sent_count,
        'replies_received': replied_count,
        'bounced_emails': bounced_count,
        'reply_rate_percent': round(reply_rate, 2),
        'bounce_rate_percent': round(bounce_rate, 2),
        'average_score': round(avg_score, 1),
        'recent_activity_count': recent_activity,
        'leads_by_status': dict(status_counts),
        'leads_by_industry': dict(industry_counts),
        'leads_by_source': dict(source_counts),
        'engagement_rate_percent': round((replied_count / total_leads * 100) if total_leads > 0 else 0, 2)
    }