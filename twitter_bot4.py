import os
import json
import requests
import tweepy
import asyncio
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime
import random
import logging
import threading
import signal

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")  # Replace with your Telegram bot token
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # Replace with your Telegram chat ID
current_articles = []
used_indices = []
current_article = None
current_tweet = None

def fetch_tech_news():
    """
    Fetches the latest tech news articles using NewsAPI.
    Returns a list of news articles with titles, descriptions, and URLs.
    """
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")  # Replace with your NewsAPI key
    
    # Increased pageSize to ensure we have plenty of articles to cycle through
    url = f"https://newsapi.org/v2/top-headlines?category=technology&language=en&pageSize=15&apiKey={NEWS_API_KEY}"
    
    logger.info("Fetching latest tech news from NewsAPI...")
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        articles = data.get("articles", [])
        
        if not articles:
            logger.warning("No tech news articles found.")
            return None
            
        # Format the articles for processing
        formatted_articles = []
        for article in articles:
            title = article.get("title", "")
            description = article.get("description", "")
            source = article.get("source", {}).get("name", "")
            url = article.get("url", "")
            
            if title and (description or url):
                formatted_articles.append({
                    "title": title,
                    "description": description,
                    "source": source,
                    "url": url
                })
        
        logger.info(f"Found {len(formatted_articles)} tech news articles.")
        return formatted_articles
    else:
        logger.error(f"Error fetching tech news: {response.status_code}")
        return None

def select_article(articles, used_indices=None):
    """
    Select an article from the list that hasn't been used yet.
    If used_indices is provided, avoid those articles.
    """
    if used_indices is None:
        used_indices = []
    
    # Filter out already used articles
    available_articles = [i for i in range(len(articles)) if i not in used_indices]
    
    if not available_articles:
        return None
    
    # Randomly select from available articles
    selected_index = random.choice(available_articles)
    selected_article = articles[selected_index]
    
    article_info = (
        f"📰 *Selected Article {selected_index + 1} of {len(articles)}:*\n\n"
        f"*Title:* {selected_article['title']}\n"
        f"*Source:* {selected_article['source']}\n"
        f"*Description:* {selected_article['description']}\n"
        f"*URL:* {selected_article['url']}"
    )
    
    return selected_index, article_info

def generate_tweet_text(article):
    """
    Uses the Gemini API to generate a tweet about the selected tech article.
    """
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    endpoint = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent"
    url = f"{endpoint}?key={GEMINI_API_KEY}"
    
    prompt = f"""
    Generate a high-quality tweet about this tech news article:

    Title: {article['title']}
    Description: {article['description']}
    Source: {article['source']}
    
    Requirements:
    - Keep it under 270 characters to leave room for a URL
    - try to add value to the user
    - try to make the tweet related to AI (if applicable)
    - tweet should be informative, engaging and based on viral content
    - Make it engaging and conversation-starting
    - Include 1-2 relevant hashtags
    - Be informative but concise
    - Write in a professional but approachable tone
    - DO NOT include 'RT' or any indication this is AI-generated
    - DO NOT include the URL (it will be added separately)
    - Act as a seasoned social media strategist specialized in technology
    - End with a call-to-action like "Read more" or ask a question to encourage engagement

    Just provide the tweet text with no additional commentary.
    """
    
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }
    
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        try:
            tweet_text = data['candidates'][0]['content']['parts'][0]['text']
            # Add the URL to the tweet
            final_tweet = f"{tweet_text.strip()}\n\n{article['url']}"
            return final_tweet
        except (KeyError, IndexError):
            logger.error("Unexpected response format")
            return None
    else:
        logger.error(f"Error generating tweet text: {response.text}")
        return None

def post_tweet(tweet_text):
    """
    Posts the tweet using Twitter's API.
    """
    BEARER_TOKEN = os.getenv("BEARER_TOKEN")
    CONSUMER_KEY = os.getenv("CONSUMER_KEY")
    CONSUMER_SECRET = os.getenv("CONSUMER_SECRET")
    ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
    ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")
    
    # Create client
    client = tweepy.Client(
        bearer_token=BEARER_TOKEN,
        consumer_key=CONSUMER_KEY,
        consumer_secret=CONSUMER_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_TOKEN_SECRET
    )
    
    # Post text-only tweet
    try:
        response = client.create_tweet(text=tweet_text)
        logger.info(f"Tweet posted successfully: {response}")
        return True, f"✅ Tweet posted successfully!"
    except Exception as e:
        logger.error(f"Error posting tweet: {str(e)}")
        return False, f"❌ Error posting tweet: {str(e)}"

# Telegram Bot functions
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "👋 Welcome to the Twitter-Telegram Bot!\n"
        "Use /tweet to find and post tech news tweets."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "Commands:\n"
        "/tweet - Start the tweet generation process\n"
        "/help - Show this help message\n"
        "\nWhen a tweet is generated, you can reply with:\n"
        "- 'post' to publish the tweet\n"
        "- 'new' to generate a new tweet\n"
        "- 'exit' to cancel the process"
    )

async def tweet_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start the tweet generation process."""
    global current_articles, used_indices, current_article, current_tweet
    
    await update.message.reply_text("🔍 Looking for tech news articles...")
    
    # Fetch articles if we don't have them
    if not current_articles:
        current_articles = fetch_tech_news()
        used_indices = []
        
    if not current_articles:
        await update.message.reply_text("❌ Failed to fetch tech news articles. Please try again later.")
        return
    
    # Select an article
    result = select_article(current_articles, used_indices)
    if result is None:
        await update.message.reply_text("🔄 All articles have been used. Fetching new articles...")
        current_articles = fetch_tech_news()
        used_indices = []
        result = select_article(current_articles, used_indices)
        
        if result is None:
            await update.message.reply_text("❌ Failed to fetch new articles. Please try again later.")
            return
    
    selected_index, article_info = result
    used_indices.append(selected_index)
    current_article = current_articles[selected_index]
    
    # Send article info to Telegram
    await update.message.reply_text(article_info, parse_mode='Markdown')
    await update.message.reply_text("⏳ Generating tweet text...")
    
    # Generate tweet
    current_tweet = generate_tweet_text(current_article)
    if not current_tweet:
        await update.message.reply_text("❌ Failed to generate tweet. Type 'new' to try another article or 'exit' to quit.")
        return
    
    # Send tweet preview
    await update.message.reply_text(
        f"✏️ *Generated Tweet:*\n\n{current_tweet}\n\n"
        "Options:\n"
        "- Type 'post' to publish this tweet\n"
        "- Type 'new' to generate a tweet about a different article\n"
        "- Type 'exit' to quit without posting", 
        parse_mode='Markdown'
    )
    
    # Save draft
    draft = {
        "article": current_article,
        "tweet_text": current_tweet,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    with open("tweet_draft.json", "w") as f:
        json.dump(draft, f, indent=2)

def force_exit():
    """Force exit the application in a reliable way"""
    logger.info("Forcing application to exit")
    os._exit(0)  # This is a more reliable way to exit than sys.exit()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global current_articles, used_indices, current_article, current_tweet
    
    if not current_tweet:
        await update.message.reply_text("Please use /tweet to start generating tweets first.")
        return
    
    text = update.message.text.lower()
    
    if text == "post":
        await update.message.reply_text("🚀 Posting tweet...")
        success, message = post_tweet(current_tweet)
        await update.message.reply_text(message)
        if success:
            current_tweet = None  # Reset after successful posting
            await update.message.reply_text("✅ Tweet posted. Bot is shutting down.")
            # Stop the bot after a successful post
            threading.Timer(2.0, force_exit).start()
            
    elif text == "new":
        await update.message.reply_text("🔍 Looking for a new article...")
        await tweet_command(update, context)
        
    elif text == "exit":
        await update.message.reply_text("👋 Tweet generation cancelled.")
        current_tweet = None
        threading.Timer(2.0, force_exit).start()
        
    else:
        await update.message.reply_text(
            "Please choose one of the following options:\n"
            "- Type 'post' to publish the tweet\n"
            "- Type 'new' to generate a new tweet\n"
            "- Type 'exit' to cancel"
        )
     

async def send_telegram_message(message):
    """Send a message to the specified Telegram chat."""
    bot = Bot(token="7323688717:AAE6fu2f8YYNFBAqnXqi36CaHo2FMxstuDA")
    await bot.send_message(chat_id="TELEGRAM_CHAT_ID", text=message, parse_mode='Markdown')

def main() -> None:
    """Start the Telegram bot."""
    application = Application.builder().token("7323688717:AAE6fu2f8YYNFBAqnXqi36CaHo2FMxstuDA").build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("tweet", tweet_command))
    
    # Message handler for text responses
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the Bot
    print(f"Starting Telegram Twitter Bot - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()