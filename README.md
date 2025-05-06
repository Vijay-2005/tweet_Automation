# Tweet Automation Bot

## Vercel Deployment Instructions

This Twitter automation bot is configured for deployment on Vercel. It automatically posts tech news tweets via Twitter API and runs continuously without any timeout.

### Deployment Steps:

1. Fork or clone this repository to your GitHub account
2. Create a new project in Vercel and link it to your GitHub repository
3. Add the following environment variables in Vercel project settings:
   - `BEARER_TOKEN`: Your Twitter Bearer Token
   - `CONSUMER_KEY`: Your Twitter API Consumer Key
   - `CONSUMER_SECRET`: Your Twitter API Consumer Secret
   - `ACCESS_TOKEN`: Your Twitter Access Token
   - `ACCESS_TOKEN_SECRET`: Your Twitter Access Token Secret
   - `TELEGRAM_TOKEN`: Your Telegram Bot Token
   - `TELEGRAM_CHAT_ID`: Your Telegram Chat ID
   - `NEWS_API_KEY`: Your NewsAPI API Key
   - `GEMINI_API_KEY`: Your Google Gemini API Key
4. Deploy the project

The main file `twitter_bot5.py` will be deployed as a serverless function.

### Local Development

1. Create a `.env` file with the above environment variables
2. Install dependencies: `pip install -r requirements.txt`
3. Run locally: `python twitter_bot5.py`