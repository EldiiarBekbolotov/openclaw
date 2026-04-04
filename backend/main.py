"""
Main LangGraph Agent Coordinator for Hack United Sponsorship Outreach System.
Orchestrates the multi-agent workflow for automated sponsorship outreach.

GOOGLE SHEETS DATABASE SCHEMA:
Create a Google Sheet with the following columns (Row 1 as headers):

A: Email          - Lead's email address
B: Company        - Company name
C: Industry       - Industry sector (Technology, Finance, etc.)
D: Source         - How the lead was acquired (Scraped from hackathon.com, Manual entry, etc.)
E: Score          - AI-generated quality score (1-10)
F: Status         - Current status (manual, sent, replied, bounced, failed)
G: Sent_Date      - When email was sent (YYYY-MM-DD HH:MM:SS)
H: Reply          - Reply status (Yes/No/pending)
I: Notes          - Additional notes or error messages

FORMULAS (add these to help with analytics):
- Reply Rate: =COUNTIF(H:H,"Yes")/COUNTIF(F:F,"sent")
- Engagement Rate: =COUNTIF(H:H,"Yes")/COUNTA(A:A) [excluding header]
- Average Score: =AVERAGE(E:E)

SAMPLE DATA:
Email,Company,Industry,Source,Score,Status,Sent_Date,Reply,Notes
contact@techcorp.com,TechCorp,Technology,Manual entry,8,manual,,,High-priority lead
sponsor@hackathon2024.com,Hackathon Inc,Event Management,Scraped from hackathon.com,6,sent,2024-01-15 10:30:00,No,Follow-up needed
"""
import logging
import asyncio
from typing import Dict, Any, TypedDict, List, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END
from backend.config import config
from backend.agents.scorer import LeadScorer, LeadData, ScoredLead
from backend.agents.email_generator import EmailGenerator, GeneratedEmail
from backend.agents.sender import EmailSender, EmailData, SendResult
from backend.agents.scraper import HackathonScraper, ScrapedLead

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    """Explicit state for the LangGraph workflow."""
    leads: List[ScrapedLead]
    scored_leads: List[Dict[str, Any]]
    emails_to_send: List[Dict[str, Any]]
    send_results: List[SendResult]
    current_step: str
    error: Optional[str]

class SponsorshipOutreachCoordinator:
    """Main coordinator for the sponsorship outreach workflow."""

    def __init__(self):
        """Initialize all agents."""
        try:
            config.validate()  # Validate environment variables
            self.scorer = LeadScorer()
            self.email_generator = EmailGenerator()
            self.sender = EmailSender()
            self.scraper = HackathonScraper()
            self.workflow = self._build_workflow()
            logger.info("Sponsorship Outreach Coordinator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize coordinator: {str(e)}")
            raise

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for sponsorship outreach."""
        workflow = StateGraph(AgentState)

        # Add nodes (agent functions)
        workflow.add_node("scrape_leads", self._scrape_leads_node)
        workflow.add_node("score_leads", self._score_leads_node)
        workflow.add_node("generate_emails", self._generate_emails_node)
        workflow.add_node("send_emails", self._send_emails_node)
        workflow.add_node("handle_errors", self._handle_errors_node)

        # Define the workflow edges
        workflow.set_entry_point("scrape_leads")

        # Normal flow
        workflow.add_edge("scrape_leads", "score_leads")
        workflow.add_edge("score_leads", "generate_emails")
        workflow.add_edge("generate_emails", "send_emails")
        workflow.add_edge("send_emails", END)

        # Error handling
        workflow.add_edge("handle_errors", END)

        # Conditional edges for error handling
        workflow.add_conditional_edges(
            "scrape_leads",
            self._check_for_errors,
            {"error": "handle_errors", "continue": "score_leads"}
        )
        workflow.add_conditional_edges(
            "score_leads",
            self._check_for_errors,
            {"error": "handle_errors", "continue": "generate_emails"}
        )
        workflow.add_conditional_edges(
            "generate_emails",
            self._check_for_errors,
            {"error": "handle_errors", "continue": "send_emails"}
        )

        return workflow.compile()

    async def run_outreach_campaign(self, hackathon_urls: List[str]) -> Dict[str, Any]:
        """
        Run the complete sponsorship outreach campaign.

        Args:
            hackathon_urls: List of hackathon website URLs to scrape

        Returns:
            Campaign results summary
        """
        try:
            logger.info(f"Starting outreach campaign for {len(hackathon_urls)} hackathons")

            # Initialize state with URLs
            initial_state = AgentState(
                leads=[],
                scored_leads=[],
                emails_to_send=[],
                send_results=[],
                current_step="initializing",
                error=None
            )
            
            # Store URLs in coordinator for use in nodes
            self.campaign_urls = hackathon_urls

            # Run the workflow
            final_state = await self.workflow.ainvoke(initial_state)

            # Generate summary
            summary = self._generate_campaign_summary(final_state)

            logger.info(f"Campaign completed. Processed {len(final_state['leads'])} leads")
            return summary

        except Exception as e:
            logger.error(f"Campaign failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "leads_processed": 0,
                "emails_sent": 0
            }

    def _scrape_leads_node(self, state: AgentState) -> AgentState:
        """Node function for scraping leads from hackathon websites."""
        try:
            # Use URLs from campaign parameters
            hackathon_urls = getattr(self, 'campaign_urls', [
                "https://mlh.io",
                "https://hackathons.hackclub.com"
            ])
            
            logger.info(f"Scraping {len(hackathon_urls)} hackathon websites...")
            all_leads = []
            for url in hackathon_urls:
                logger.info(f"Scraping: {url}")
                leads = self.scraper.scrape_hackathon_sponsors(url)
                all_leads.extend(leads)
                logger.info(f"Found {len(leads)} leads from {url}")

            state["leads"] = all_leads
            state["current_step"] = "leads_scraped"
            logger.info(f"Scraped {len(all_leads)} total leads")

        except Exception as e:
            state["error"] = f"Scraping failed: {str(e)}"
            logger.error(f"Scraping error: {str(e)}")

        return state

    def _score_leads_node(self, state: AgentState) -> AgentState:
        """Node function for scoring leads."""
        try:
            scored_leads = []
            for lead in state["leads"]:
                # Convert ScrapedLead to LeadData format
                lead_data = LeadData(
                    email=lead["email"],
                    company=lead["company"],
                    industry=lead["industry"],
                    source=lead["source"],
                    website=lead["website"],
                    description=lead["description"]
                )

                score_result = self.scorer.score_lead(lead_data)

                scored_lead = {
                    **lead,
                    "score": score_result["score"],
                    "reasoning": score_result["reasoning"],
                    "priority": score_result["priority"]
                }
                scored_leads.append(scored_lead)

            # Filter to high-priority leads only
            high_priority = [lead for lead in scored_leads if lead["priority"] == "high"]
            state["scored_leads"] = high_priority
            state["current_step"] = "leads_scored"
            logger.info(f"Scored {len(scored_leads)} leads, {len(high_priority)} high-priority")

        except Exception as e:
            state["error"] = f"Scoring failed: {str(e)}"
            logger.error(f"Scoring error: {str(e)}")

        return state

    def _generate_emails_node(self, state: AgentState) -> AgentState:
        """Node function for generating personalized emails."""
        try:
            emails_to_send = []
            for lead in state["scored_leads"]:
                # Convert to LeadData format for email generator
                lead_data = LeadData(
                    email=lead["email"],
                    company=lead["company"],
                    industry=lead["industry"],
                    source=lead["source"],
                    website=lead["website"],
                    description=lead["description"],
                    score=lead["score"],
                    priority=lead["priority"]
                )

                email_result = self.email_generator.generate_email(lead_data)

                email_data = {
                    "lead": lead,
                    "subject": email_result["subject"],
                    "body": email_result["body"],
                    "personalization_notes": email_result["personalization_notes"]
                }
                emails_to_send.append(email_data)

            state["emails_to_send"] = emails_to_send
            state["current_step"] = "emails_generated"
            logger.info(f"Generated {len(emails_to_send)} personalized emails")

        except Exception as e:
            state["error"] = f"Email generation failed: {str(e)}"
            logger.error(f"Email generation error: {str(e)}")

        return state

    def _send_emails_node(self, state: AgentState) -> AgentState:
        """Node function for sending emails."""
        try:
            send_results = []
            for email_data in state["emails_to_send"]:
                # Convert to EmailData format for sender
                sender_data = EmailData(
                    to_email=email_data["lead"]["email"] or f"contact@{email_data['lead']['company'].lower().replace(' ', '')}.com",
                    subject=email_data["subject"],
                    body=email_data["body"],
                    lead_company=email_data["lead"]["company"],
                    lead_score=email_data["lead"]["score"]
                )

                result = self.sender.send_email(sender_data)
                send_results.append(result)

                # Small delay to avoid rate limiting
                asyncio.sleep(1)

            state["send_results"] = send_results
            state["current_step"] = "emails_sent"
            successful_sends = sum(1 for r in send_results if r["success"])
            logger.info(f"Sent {successful_sends}/{len(send_results)} emails successfully")

        except Exception as e:
            state["error"] = f"Email sending failed: {str(e)}"
            logger.error(f"Email sending error: {str(e)}")

        return state

    def _handle_errors_node(self, state: AgentState) -> AgentState:
        """Node function for handling errors."""
        logger.error(f"Workflow error in step {state.get('current_step', 'unknown')}: {state['error']}")
        return state

    def _check_for_errors(self, state: AgentState) -> str:
        """Check if there's an error in the current state."""
        return "error" if state.get("error") else "continue"

    def _generate_campaign_summary(self, state: AgentState) -> Dict[str, Any]:
        """Generate a summary of the campaign results."""
        total_leads = len(state.get("leads", []))
        scored_leads = len(state.get("scored_leads", []))
        emails_generated = len(state.get("emails_to_send", []))
        send_results = state.get("send_results", [])
        emails_sent = sum(1 for r in send_results if r["success"])
        emails_failed = len(send_results) - emails_sent

        return {
            "success": state.get("error") is None,
            "leads_processed": total_leads,
            "high_priority_leads": scored_leads,
            "emails_generated": emails_generated,
            "emails_sent": emails_sent,
            "emails_failed": emails_failed,
            "error": state.get("error"),
            "timestamp": datetime.now().isoformat()
        }

async def main():
    """Main entry point for running the sponsorship outreach system."""
    try:
        coordinator = SponsorshipOutreachCoordinator()

        # Run the campaign
        results = await coordinator.run_outreach_campaign([])

        print("Campaign Results:")
        print(f"- Leads processed: {results['leads_processed']}")
        print(f"- High-priority leads: {results['high_priority_leads']}")
        print(f"- Emails sent: {results['emails_sent']}")
        print(f"- Emails failed: {results['emails_failed']}")

        if results['error']:
            print(f"- Error: {results['error']}")

    except Exception as e:
        logger.error(f"Application failed: {str(e)}")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())