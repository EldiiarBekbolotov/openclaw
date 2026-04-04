"""
Local FastAPI development server for testing the sponsorship outreach system.
This wraps the backend.main coordinator for local development.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from backend.main import SponsorshipOutreachCoordinator
from backend.config import config
import gspread
import logging
import asyncio
from datetime import datetime
from collections import defaultdict
import json
import io
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global queue for streaming logs
log_queue = asyncio.Queue()

class QueueHandler(logging.Handler):
    """Custom handler that puts log records into a queue for streaming."""
    def emit(self, record):
        try:
            msg = self.format(record)
            asyncio.create_task(log_queue.put(msg))
        except Exception:
            self.handleError(record)

# Add queue handler to existing loggers
queue_handler = QueueHandler()
queue_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(queue_handler)
logging.getLogger('backend').addHandler(queue_handler)

# Create FastAPI app
app = FastAPI(
    title="Hack United Sponsorship Outreach API",
    description="Local development API for sponsorship outreach system"
)

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize the coordinator on startup."""
    logger.info("Initializing Sponsorship Outreach Coordinator...")
    try:
        app.coordinator = SponsorshipOutreachCoordinator()
        logger.info("✓ Coordinator initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize coordinator: {str(e)}")
        raise

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Hack United Sponsorship Outreach API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

# Helper function to get Google Sheets worksheet
def get_worksheet():
    """Connect to and return the Google Sheets worksheet."""
    try:
        creds = config.get_google_credentials()
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(config.GOOGLE_SHEETS_SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(config.GOOGLE_SHEETS_WORKSHEET_NAME)
        return worksheet
    except Exception as e:
        logger.error(f"Failed to connect to Google Sheets: {str(e)}")
        raise

# API endpoints for frontend
@app.get("/api/get_campaign_stats")
async def get_campaign_stats():
    """Get campaign statistics from Google Sheets."""
    try:
        worksheet = get_worksheet()
        all_data = worksheet.get_all_records()
        
        # Calculate statistics
        total_leads = len(all_data)
        status_counts = defaultdict(int)
        industry_counts = defaultdict(int)
        source_counts = defaultdict(int)
        
        sent_count = 0
        replied_count = 0
        bounced_count = 0
        scores = []
        
        for row in all_data:
            status = row.get('Status', '').lower()
            status_counts[status] += 1
            
            industry = row.get('Industry', '')
            if industry:
                industry_counts[industry] += 1
            
            source = row.get('Source', '')
            if source:
                source_counts[source] += 1
            
            if status == 'sent':
                sent_count += 1
            
            reply = row.get('Reply', '').lower()
            if reply and reply != 'no':
                replied_count += 1
            
            if status in ['bounced', 'failed']:
                bounced_count += 1
            
            score_str = row.get('Score', '')
            if score_str and str(score_str).replace('.', '', 1).isdigit():
                scores.append(float(score_str))
        
        # Calculate rates
        reply_rate = (replied_count / sent_count * 100) if sent_count > 0 else 0
        bounce_rate = (bounced_count / sent_count * 100) if sent_count > 0 else 0
        avg_score = sum(scores) / len(scores) if scores else 0
        
        return {
            "total_leads": total_leads,
            "emails_sent": sent_count,
            "replies_received": replied_count,
            "bounced_emails": bounced_count,
            "reply_rate_percent": round(reply_rate, 2),
            "bounce_rate_percent": round(bounce_rate, 2),
            "average_score": round(avg_score, 1),
            "engagement_rate_percent": round((replied_count / total_leads * 100) if total_leads > 0 else 0, 2)
        }
    except Exception as e:
        logger.error(f"Error getting campaign stats: {e}")
        return {
            "total_leads": 0,
            "emails_sent": 0,
            "reply_rate_percent": 0,
            "average_score": 0,
            "error": str(e)
        }

@app.get("/api/get_leads")
async def get_leads(status: str = None, limit: int = 100, offset: int = 0):
    """Get leads from Google Sheets with optional filtering."""
    try:
        worksheet = get_worksheet()
        all_data = worksheet.get_all_records()
        
        # Apply filters
        filtered_data = all_data
        if status:
            filtered_data = [row for row in all_data if row.get('Status', '').lower() == status.lower()]
        
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
            "leads": leads,
            "total_count": len(filtered_data),
            "returned_count": len(leads),
            "offset": offset,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Error getting leads: {e}")
        return {
            "leads": [],
            "error": str(e)
        }

@app.post("/api/add_lead")
async def add_lead(lead_data: dict):
    """Add a new lead to Google Sheets."""
    try:
        logger.info(f"Received lead data: {lead_data}")
        worksheet = get_worksheet()
        logger.info(f"Connected to worksheet: {worksheet.title}")
        
        # Validate required fields
        if not lead_data.get('email') or not lead_data.get('company'):
            return {
                "success": False,
                "error": "Email and company are required"
            }
        
        # Check if lead already exists
        try:
            existing_emails = worksheet.col_values(1)  # Email column
            logger.info(f"Existing emails: {existing_emails[:5]}...")  # Log first 5 for debug
            if lead_data['email'] in existing_emails:
                return {
                    "success": False,
                    "error": "Lead with this email already exists"
                }
        except Exception as e:
            logger.warning(f"Could not check existing emails: {e}")
        
        # Prepare row data
        row_data = [
            lead_data.get('email', ''),
            lead_data.get('company', ''),
            lead_data.get('industry', ''),
            lead_data.get('source', 'Manual entry'),
            '',  # Score (to be calculated later)
            'manual',  # Status
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            '',  # Reply
            lead_data.get('description', '')  # Notes
        ]
        
        logger.info(f"Prepared row data: {row_data}")
        
        # Add to sheet
        result = worksheet.append_row(row_data)
        logger.info(f"Successfully appended row. Result: {result}")
        
        return {
            "success": True,
            "message": "Lead added successfully",
            "lead": {
                "email": lead_data.get('email'),
                "company": lead_data.get('company'),
                "industry": lead_data.get('industry', ''),
                "source": lead_data.get('source', 'Manual entry')
            }
        }
    except Exception as e:
        logger.error(f"Error adding lead: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/run_campaign")
async def run_campaign(campaign_data: dict):
    """Run the sponsorship outreach campaign."""
    try:
        urls = campaign_data.get('urls', [])
        
        if not urls:
            return {
                "success": False,
                "error": "No URLs provided"
            }
        
        logger.info(f"Starting campaign with {len(urls)} URLs")
        logger.info(f"URLs: {urls}")
        
        # Run the campaign
        result = await asyncio.to_thread(
            app.coordinator.run_outreach_campaign, 
            urls
        )
        
        logger.info("Campaign completed successfully")
        
        return {
            "success": True,
            "message": "Campaign executed successfully",
            "leads_processed": len(urls),
            "result": result
        }
    except Exception as e:
        logger.error(f"Error running campaign: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/campaign/logs")
async def campaign_logs():
    """Stream campaign logs via Server-Sent Events."""
    async def event_generator():
        """Generate SSE events from the log queue."""
        while True:
            try:
                # Wait for log message with timeout
                msg = await asyncio.wait_for(log_queue.get(), timeout=60)
                yield f"data: {json.dumps({'log': msg})}\n\n"
            except asyncio.TimeoutError:
                # Send keepalive every 60 seconds
                yield ": keepalive\n\n"
            except Exception as e:
                logger.error(f"Error in log generator: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
