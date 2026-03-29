"""
Local FastAPI development server for testing the sponsorship outreach system.
This wraps the backend.main coordinator for local development.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.main import SponsorshipOutreachCoordinator
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# API endpoints for frontend
@app.get("/api/get_campaign_stats")
async def get_campaign_stats():
    """Get campaign statistics from Google Sheets."""
    try:
        # For now, return mock data since we don't have Google Sheets integration in local dev
        return {
            "total_leads": 0,
            "emails_sent": 0,
            "reply_rate_percent": 0,
            "average_score": 0
        }
    except Exception as e:
        logger.error(f"Error getting campaign stats: {e}")
        return {"error": str(e)}

@app.get("/api/get_leads")
async def get_leads(status: str = None, limit: int = 100, offset: int = 0):
    """Get leads from Google Sheets with optional filtering."""
    try:
        # For now, return mock data since we don't have Google Sheets integration in local dev
        return {
            "leads": []
        }
    except Exception as e:
        logger.error(f"Error getting leads: {e}")
        return {"error": str(e)}

@app.post("/api/add_lead")
async def add_lead(lead_data: dict):
    """Add a new lead to Google Sheets."""
    try:
        # For now, just log the lead data since we don't have Google Sheets integration in local dev
        logger.info(f"Adding lead: {lead_data}")
        return {"success": True, "message": "Lead added successfully"}
    except Exception as e:
        logger.error(f"Error adding lead: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
