# Hack United Sponsorship Outreach System - Setup Guide

This guide will walk you through setting up the AI-powered nonprofit sponsorship outreach system for Hack United.

## Prerequisites

- GitHub account
- Gmail account (for SMTP sending)
- Free accounts for:
  - [Groq](https://groq.com) (for AI models)
  - [Railway](https://railway.app) (for backend deployment)
  - [Netlify](https://netlify.com) (for frontend deployment)

## 1. Google Sheets Setup

### Create a Google Sheet

1. Go to [sheets.google.com](https://sheets.google.com) and create a new spreadsheet
2. Name it "Hack United Leads" or similar
3. Set up the columns as described in `backend/main.py` comments:
   ```
   A: Email | B: Company | C: Industry | D: Source | E: Score | F: Status | G: Sent_Date | H: Reply | I: Notes
   ```

### Create Service Account Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing one
3. Enable the Google Sheets API
4. Go to "Credentials" → "Create Credentials" → "Service Account"
5. Give it a name like "hack-united-sheets"
6. Grant it "Editor" role for Google Sheets
7. Create a JSON key and download it as `credentials.json`
8. Place this file in your project root (same level as `backend/`)

### Share the Sheet

1. In Google Sheets, click "Share"
2. Add the service account email (from the JSON file) as an editor
3. Copy the spreadsheet ID from the URL (the long string between `/d/` and `/edit`)

## 2. API Keys Setup

### Groq API Key

1. Sign up at [groq.com](https://groq.com)
2. Go to your dashboard and create an API key
3. Copy the key for use in environment variables

### Gmail App Password

1. Go to your Gmail settings
2. Enable 2-factor authentication if not already enabled
3. Go to "App passwords" in security settings
4. Generate a password for "Mail"
5. Copy the 16-character password (ignore spaces)

## 3. Local Development Setup

### Clone and Install

```bash
git clone <your-repo-url>
cd hack-united-sponsorship

# Install Python dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
```

### Configure Environment Variables

Edit `.env` with your actual values:

```bash
# Groq API
GROQ_API_KEY=your_actual_groq_key_here
GROQ_MODEL_MIXTRAL=mixtral-8x7b-32768
GROQ_MODEL_LLAMA=llama3-8b-8192

# Google Sheets
GOOGLE_SHEETS_CREDENTIALS_PATH=credentials.json
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id_here
GOOGLE_SHEETS_WORKSHEET_NAME=Leads

# Gmail
GMAIL_USERNAME=your_email@gmail.com
GMAIL_APP_PASSWORD=your_16_char_app_password

# Optional
LOG_LEVEL=INFO
```

### Test Locally

#### Test Backend

```bash
cd backend
python main.py
```

This should run the outreach campaign and log results.

#### Test Backend Locally

```bash
# Install dependencies and run FastAPI server
pip install -r requirements.txt
uvicorn backend.api:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/docs` to verify the API endpoints.

## 4. Deployment

### Backend Deployment (Railway)

1. **Connect Repository**
   - Go to [railway.app](https://railway.app) and sign up
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository

2. **Configure Environment Variables**
   - In Railway dashboard, go to your project → "Variables"
   - Add all variables from your `.env` file

3. **Set Up Cron Job**
   - Railway should automatically detect the cron schedule from `railway.yaml`
   - The system will run daily outreach campaigns at 9 AM EST

4. **Deploy**
   - Railway will automatically build and deploy on git push
   - Check logs in Railway dashboard

### Frontend Deployment (Netlify)

1. **Connect Repository**
   - Go to [netlify.com](https://netlify.com) and sign up
   - Click "New site from Git" → "Deploy manually" or connect GitHub
   - Set build command to: `echo 'No build required'`
   - Set publish directory to: `frontend`

2. **Configure Environment Variables**
   - In Netlify dashboard, go to Site settings → Environment variables
   - Add the Google Sheets and Gmail variables (same as backend)

3. **Deploy**
   - Netlify will automatically deploy on git push
   - Your site will be available at `https://your-site-name.netlify.app`

## 5. Testing the System

### Manual Lead Addition

1. Go to your deployed frontend
2. Use the "Add Manual Lead" form
3. Check that the lead appears in Google Sheets

### Automated Outreach

1. The system runs automatically via Railway cron jobs
2. Check Railway logs for campaign results
3. Monitor Google Sheets for new leads and sent emails

### API Testing

Test the Netlify functions:

- `/.netlify/functions/api/get_leads` - Should return leads data
- `/.netlify/functions/api/get_campaign_stats` - Should return statistics
- `/.netlify/functions/api/add_lead` - Should accept POST requests

## 6. Monitoring and Maintenance

### Logs

- **Backend**: Check Railway logs for application logs
- **Frontend**: Check Netlify function logs for API errors

### Cost Monitoring

- **Groq**: Monitor API usage in their dashboard (~$0.10/1K tokens)
- **Railway**: Free tier includes 512MB RAM, $5/month for more
- **Netlify**: Free tier includes 100GB bandwidth
- **Google Sheets**: Free

### Troubleshooting

**Common Issues:**

1. **Google Sheets Authentication Error**
   - Ensure `credentials.json` is in the correct location
   - Verify the service account has editor access to the sheet
   - Check spreadsheet ID is correct

2. **Gmail SMTP Errors**
   - Verify app password is correct (no spaces)
   - Check Gmail allows less secure apps or app passwords
   - Ensure 2FA is enabled on Gmail account

3. **Groq API Errors**
   - Check API key is valid and has credits
   - Verify model names are correct
   - Handle rate limits (retry logic is built-in)

4. **Netlify Function Timeouts**
   - Functions have 10-second timeout by default
   - Optimize database queries
   - Consider pagination for large datasets

### Security Notes

- Never commit `credentials.json` or `.env` files
- Use environment variables for all secrets
- Regularly rotate API keys and app passwords
- Monitor for unusual API usage

## 7. Customization

### Adding New Lead Sources

- Modify `backend/agents/scraper.py` to add new hackathon URLs
- Update the scraping logic for different website structures

### Customizing Email Templates

- Edit `backend/agents/email_generator.py` prompts
- Add industry-specific messaging

### Enhancing Scoring

- Modify `backend/agents/scorer.py` to include additional criteria
- Add more detailed scoring rubrics

## Support

For issues or questions:

1. Check the logs in Railway/Netlify dashboards
2. Review this setup guide
3. Test locally first
4. Check GitHub issues for similar problems

The system is designed to be robust with error handling and retries. Most issues can be resolved by checking environment variables and API credentials.
