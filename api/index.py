import os
import json
import requests
import random
from http.server import BaseHTTPRequestHandler
from datetime import datetime
import tweepy
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def fetch_tech_news():
    """
    Fetches the latest tech news articles using NewsAPI.
    Returns a list of news articles with titles, descriptions, and URLs.
    """
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")
    
    # Increased pageSize to ensure we have plenty of articles to cycle through
    url = f"https://newsapi.org/v2/top-headlines?category=technology&language=en&pageSize=15&apiKey={NEWS_API_KEY}"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        articles = data.get("articles", [])
        
        if not articles:
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
        
        return formatted_articles
    else:
        return None

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
            return None
    else:
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
        return True, "Tweet posted successfully!"
    except Exception as e:
        return False, f"Error posting tweet: {str(e)}"

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(f"Twitter bot API is active! Use POST requests to /api/post-tweet to trigger actions. Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".encode())
        return

    def do_POST(self):
        if self.path == '/api/post-tweet':
            try:
                # Get request body length
                content_length = int(self.headers.get('Content-Length', 0))
                
                # Fetch articles
                articles = fetch_tech_news()
                if not articles:
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Failed to fetch news articles"}).encode())
                    return
                
                # Select an article
                selected_index = random.randint(0, len(articles)-1)
                selected_article = articles[selected_index]
                
                # Generate tweet
                tweet_text = generate_tweet_text(selected_article)
                if not tweet_text:
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Failed to generate tweet text"}).encode())
                    return
                
                # Post tweet
                success, message = post_tweet(tweet_text)
                
                if success:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    response_data = {
                        "status": "success",
                        "message": message,
                        "article": selected_article["title"],
                        "tweet": tweet_text
                    }
                    self.wfile.write(json.dumps(response_data).encode())
                else:
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": message}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write("Not found".encode()) 