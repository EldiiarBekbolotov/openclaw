"""
Personalized Email Generation Agent for Hack United Sponsorship Outreach.
Uses Groq LLaMA model for fast, personalized email generation.
"""
import logging
from typing import Dict, Any, TypedDict
from groq import Groq
from backend.config import config

logger = logging.getLogger(__name__)

class LeadData(TypedDict):
    """Structure for lead information."""
    email: str
    company: str
    industry: str
    source: str
    website: str
    description: str
    score: int
    priority: str

class GeneratedEmail(TypedDict):
    """Structure for generated email content."""
    subject: str
    body: str
    personalization_notes: str

class EmailGenerator:
    """Agent responsible for generating personalized sponsorship emails."""

    def __init__(self):
        self.client = Groq(api_key=config.GROQ_API_KEY)
        self.model = config.GROQ_MODEL_LLAMA

    def generate_email(self, lead: LeadData) -> GeneratedEmail:
        """
        Generate a personalized sponsorship outreach email.

        Args:
            lead: Lead information including scoring data

        Returns:
            GeneratedEmail with subject, body, and personalization notes
        """
        try:
            prompt = self._build_email_prompt(lead)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional sponsorship outreach specialist. Generate compelling, personalized emails for hackathon sponsorship opportunities."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.7
            )

            result_text = response.choices[0].message.content.strip()
            email_data = self._parse_email_response(result_text)

            logger.info(f"Generated email for {lead['company']}")

            return email_data

        except Exception as e:
            logger.error(f"Error generating email for {lead['company']}: {str(e)}")
            # Return fallback email
            return self._generate_fallback_email(lead)

    def _build_email_prompt(self, lead: LeadData) -> str:
        """Build the email generation prompt."""
        priority_guidance = {
            "high": "This is a high-priority lead. Make the email enthusiastic and highlight premium sponsorship opportunities.",
            "medium": "This is a medium-priority lead. Focus on value proposition and community impact.",
            "low": "This is a lower-priority lead. Keep it professional but concise."
        }

        return f"""
        Generate a personalized sponsorship outreach email for Hack United, a nonprofit hackathon organization.

        LEAD INFORMATION:
        Company: {lead['company']}
        Industry: {lead['industry']}
        Website: {lead.get('website', 'Not available')}
        Description: {lead.get('description', 'Not available')}
        Source: {lead['source']}
        Priority: {lead['priority']} (Score: {lead['score']}/10)

        PRIORITY GUIDANCE: {priority_guidance[lead['priority']]}

        REQUIREMENTS:
        - Professional yet friendly tone
        - Highlight Hack United's mission: empowering underrepresented communities through hackathons
        - Mention specific benefits relevant to their industry
        - Include clear call-to-action
        - Keep under 300 words
        - Personalize based on company/industry information

        FORMAT YOUR RESPONSE AS:
        SUBJECT: [Email subject line]
        BODY: [Full email body]
        NOTES: [Brief notes on personalization choices]
        """

    def _parse_email_response(self, response: str) -> GeneratedEmail:
        """Parse the AI response to extract email components."""
        lines = response.split('\n')
        subject = "Partnership Opportunity with Hack United"
        body = "Dear [Contact],\n\nWe'd love to discuss sponsorship opportunities..."
        notes = "Generated email content"

        current_section = None
        body_lines = []

        for line in lines:
            if line.startswith('SUBJECT:'):
                subject = line.split(':', 1)[1].strip()
                current_section = 'subject'
            elif line.startswith('BODY:'):
                current_section = 'body'
            elif line.startswith('NOTES:'):
                notes = line.split(':', 1)[1].strip()
                current_section = 'notes'
            elif current_section == 'body':
                body_lines.append(line)

        body = '\n'.join(body_lines).strip()

        return GeneratedEmail(
            subject=subject,
            body=body,
            personalization_notes=notes
        )

    def _generate_fallback_email(self, lead: LeadData) -> GeneratedEmail:
        """Generate a basic fallback email if AI generation fails."""
        subject = f"Sponsorship Opportunity with Hack United - {lead['company']}"

        body = f"""Dear {lead['company']} Team,

        I'm reaching out from Hack United, a nonprofit organization dedicated to empowering underrepresented communities through hackathons and tech education.

        We believe {lead['company']} would be an excellent partner for our upcoming events, given your work in {lead['industry']}.

        Our sponsorship packages offer various opportunities to engage with talented developers and give back to the community.

        I'd love to schedule a brief call to discuss how we can work together.

        Best regards,
        [Your Name]
        Hack United Sponsorship Team"""

        return GeneratedEmail(
            subject=subject,
            body=body,
            personalization_notes="Fallback email generated due to API error"
        )