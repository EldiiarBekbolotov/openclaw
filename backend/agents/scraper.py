"""
Hackathon Website Scraper Agent for Hack United Sponsorship Outreach.
Reusable agent for scraping hackathon websites to find sponsor leads.
"""
import logging
import requests
import time
from typing import List, Dict, Any, TypedDict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from backend.config import config

logger = logging.getLogger(__name__)

class ScrapedLead(TypedDict):
    """Structure for scraped lead information."""
    email: str
    company: str
    industry: str
    source: str
    website: str
    description: str

class HackathonScraper:
    """Agent responsible for scraping hackathon websites for sponsor leads."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def scrape_hackathon_sponsors(self, hackathon_url: str, max_retries: int = 3) -> List[ScrapedLead]:
        """
        Scrape sponsor information from a hackathon website.

        Args:
            hackathon_url: URL of the hackathon website
            max_retries: Maximum number of retry attempts for requests

        Returns:
            List of scraped sponsor leads
        """
        leads = []

        try:
            # Scrape main sponsors page
            sponsors_page = self._scrape_page(hackathon_url + "/sponsors", max_retries)
            if sponsors_page:
                leads.extend(self._extract_sponsors_from_page(sponsors_page, hackathon_url))

            # Also try common sponsor page URLs
            common_paths = ["/partners", "/supporters", "/thanks", "/about"]
            for path in common_paths:
                page_url = urljoin(hackathon_url, path)
                page_content = self._scrape_page(page_url, max_retries)
                if page_content:
                    leads.extend(self._extract_sponsors_from_page(page_content, hackathon_url))

            # Remove duplicates
            unique_leads = self._deduplicate_leads(leads)

            logger.info(f"Scraped {len(unique_leads)} sponsor leads from {hackathon_url}")
            return unique_leads

        except Exception as e:
            logger.error(f"Error scraping {hackathon_url}: {str(e)}")
            return []

    def _scrape_page(self, url: str, max_retries: int) -> Optional[str]:
        """Scrape a single page with retry logic."""
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                return response.text
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff

        return None

    def _extract_sponsors_from_page(self, html_content: str, source_url: str) -> List[ScrapedLead]:
        """Extract sponsor information from HTML content."""
        leads = []
        soup = BeautifulSoup(html_content, 'lxml')

        # Look for sponsor sections
        sponsor_selectors = [
            '.sponsors', '.partners', '.supporters', '.thanks',
            '[class*="sponsor"]', '[class*="partner"]', '[id*="sponsor"]'
        ]

        sponsor_elements = []
        for selector in sponsor_selectors:
            sponsor_elements.extend(soup.select(selector))

        # If no specific sections found, look for images (logos) which might be sponsors
        if not sponsor_elements:
            images = soup.find_all('img', {'src': True})
            sponsor_elements = [img.parent for img in images if 'logo' in img.get('src', '').lower()]

        for element in sponsor_elements:
            lead = self._extract_lead_from_element(element, source_url)
            if lead:
                leads.append(lead)

        return leads

    def _extract_lead_from_element(self, element, source_url: str) -> Optional[ScrapedLead]:
        """Extract lead information from a single HTML element."""
        try:
            # Extract company name from alt text, title, or text content
            company = ""
            if element.name == 'img':
                company = element.get('alt', '') or element.get('title', '')
            else:
                # Look for text content
                text_content = element.get_text(strip=True)
                if text_content:
                    company = text_content

                # Look for logo images within the element
                logo_img = element.find('img')
                if logo_img:
                    alt_text = logo_img.get('alt', '')
                    if alt_text and len(alt_text) > len(company):
                        company = alt_text

            if not company or len(company) < 2:
                return None

            # Extract website from links
            website = ""
            link = element.find('a', href=True)
            if link:
                href = link['href']
                if href.startswith('http'):
                    website = href
                else:
                    website = urljoin(source_url, href)

            # Extract email if available (rare but possible)
            email = ""
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            import re
            email_match = re.search(email_pattern, element.get_text())
            if email_match:
                email = email_match.group()

            # Basic industry inference from company name
            industry = self._infer_industry(company)

            return ScrapedLead(
                email=email,
                company=company.strip(),
                industry=industry,
                source=f"Scraped from {urlparse(source_url).netloc}",
                website=website,
                description=f"Sponsor found on hackathon website"
            )

        except Exception as e:
            logger.warning(f"Error extracting lead from element: {str(e)}")
            return None

    def _infer_industry(self, company_name: str) -> str:
        """Basic industry inference from company name."""
        name_lower = company_name.lower()

        tech_keywords = ['tech', 'software', 'digital', 'cloud', 'ai', 'data', 'cyber', 'web']
        finance_keywords = ['bank', 'finance', 'capital', 'investment', 'wealth']
        consulting_keywords = ['consulting', 'advisory', 'partners', 'group']

        if any(keyword in name_lower for keyword in tech_keywords):
            return "Technology"
        elif any(keyword in name_lower for keyword in finance_keywords):
            return "Financial Services"
        elif any(keyword in name_lower for keyword in consulting_keywords):
            return "Consulting"
        else:
            return "Unknown"

    def _deduplicate_leads(self, leads: List[ScrapedLead]) -> List[ScrapedLead]:
        """Remove duplicate leads based on company name."""
        seen_companies = set()
        unique_leads = []

        for lead in leads:
            company_key = lead['company'].lower().strip()
            if company_key not in seen_companies:
                seen_companies.add(company_key)
                unique_leads.append(lead)

        return unique_leads