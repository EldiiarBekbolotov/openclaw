"""
Lead Quality Scoring Agent for Hack United Sponsorship Outreach.
Uses Groq Mixtral model to score potential sponsors based on company data.
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

class ScoredLead(TypedDict):
    """Structure for scored lead with reasoning."""
    score: int  # 1-10 scale
    reasoning: str
    priority: str  # 'high', 'medium', 'low'

class LeadScorer:
    """Agent responsible for scoring lead quality."""

    def __init__(self):
        self.client = Groq(api_key=config.GROQ_API_KEY)
        self.model = config.GROQ_MODEL_MIXTRAL

    def score_lead(self, lead: LeadData) -> ScoredLead:
        """
        Score a potential sponsor lead using AI analysis.

        Args:
            lead: Lead information to score

        Returns:
            ScoredLead with score, reasoning, and priority
        """
        try:
            prompt = self._build_scoring_prompt(lead)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert sponsorship outreach consultant for hackathons. Score leads on a scale of 1-10 based on their potential as sponsors."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )

            result_text = response.choices[0].message.content.strip()
            score, reasoning = self._parse_response(result_text)

            priority = self._determine_priority(score)

            logger.info(f"Scored lead {lead['company']}: {score}/10 ({priority})")

            return ScoredLead(
                score=score,
                reasoning=reasoning,
                priority=priority
            )

        except Exception as e:
            logger.error(f"Error scoring lead {lead['company']}: {str(e)}")
            # Return conservative default score
            return ScoredLead(
                score=5,
                reasoning="Error during scoring analysis",
                priority="medium"
            )

    def _build_scoring_prompt(self, lead: LeadData) -> str:
        """Build the scoring prompt for the AI model."""
        return f"""
        Analyze this potential hackathon sponsor:

        Company: {lead['company']}
        Industry: {lead['industry']}
        Website: {lead.get('website', 'Not provided')}
        Description: {lead.get('description', 'Not provided')}
        Source: {lead['source']}

        Score this lead on a scale of 1-10 for hackathon sponsorship potential, considering:
        - Company size and resources
        - Relevance to tech/developer community
        - Past sponsorship history (if mentioned)
        - Industry alignment with hackathons
        - Geographic location (prefer local/regional)

        Provide your response in this exact format:
        SCORE: [number 1-10]
        REASONING: [brief explanation]
        """

    def _parse_response(self, response: str) -> tuple[int, str]:
        """Parse the AI response to extract score and reasoning."""
        lines = response.split('\n')
        score = 5  # default
        reasoning = "Analysis completed"

        for line in lines:
            if line.startswith('SCORE:'):
                try:
                    score = int(line.split(':', 1)[1].strip())
                    score = max(1, min(10, score))  # clamp to 1-10
                except ValueError:
                    pass
            elif line.startswith('REASONING:'):
                reasoning = line.split(':', 1)[1].strip()

        return score, reasoning

    def _determine_priority(self, score: int) -> str:
        """Determine priority level based on score."""
        if score >= 8:
            return "high"
        elif score >= 6:
            return "medium"
        else:
            return "low"