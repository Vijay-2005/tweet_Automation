import os
import json
import requests
import tweepy
from datetime import datetime
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def fetch_tech_news():
    """
    Fetches the latest tech news articles using NewsAPI.
    Returns a list of news articles with titles, descriptions, and URLs.
    """
    NEWS_API_KEY = os.getenv("NEWS_API_KEY")
    url = f"https://newsapi.org/v2/top-headlines?category=technology&language=en&pageSize=5&apiKey={NEWS_API_KEY}"
    
    print("Fetching latest tech news from NewsAPI...")
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        articles = data.get("articles", [])
        
        if not articles:
            print("No tech news articles found.")
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
        
        print(f"Found {len(formatted_articles)} tech news articles.")
        return formatted_articles
    else:
        print(f"Error fetching tech news: {response.status_code}")
        print(response.text)
        return None

def select_best_article(articles):
    """
    Uses Gemini API to select the most interesting article from the list.
    """
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    endpoint = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent"
    url = f"{endpoint}?key={GEMINI_API_KEY}"
    
    # Format articles for the prompt
    articles_text = ""
    for i, article in enumerate(articles, 1):
        articles_text += f"Article {i}:\n"
        articles_text += f"Title: {article['title']}\n"
        articles_text += f"Source: {article['source']}\n"
        articles_text += f"Description: {article['description']}\n"
        articles_text += f"URL: {article['url']}\n\n"
    
    prompt = f"""
    Below are {len(articles)} recent technology news articles.
    
    {articles_text}
    
    Please analyze these articles and select the SINGLE most interesting, significant, or impactful tech story.
    Consider factors like innovation, potential impact, and general public interest.
    
    Return only the number of your selected article (1-{len(articles)}) followed by a brief explanation of why it's significant.
    Format: "Selected Article: [NUMBER]
    Explanation: [WHY THIS IS SIGNIFICANT]"
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
            selection_text = data['candidates'][0]['content']['parts'][0]['text']
            # Extract the selected article number
            selection_lines = selection_text.strip().split('\n')
            for line in selection_lines:
                if line.startswith("Selected Article:"):
                    try:
                        article_num = int(line.split(':')[1].strip()) - 1
                        if 0 <= article_num < len(articles):
                            print(f"\nGemini selected article {article_num+1} as most interesting:")
                            print(f"Title: {articles[article_num]['title']}")
                            return articles[article_num]
                    except:
                        pass
            
            # Fallback to the first article if parsing fails
            print("Could not determine selection, defaulting to first article.")
            return articles[0]
        except (KeyError, IndexError):
            print("Unexpected response format from article selection.")
            return articles[0]
    else:
        print("Error selecting best article:", response.text)
        return articles[0]  # Default to first article

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
    - try to make the tweet related to AI 
    - tweet should be informative, engaging and based on viral content
    - Make it engaging and conversation-starting
    - Include 1-2 relevant hashtags
    - Be informative but concise
    - Write in a professional but approachable tone
    - DO NOT include 'RT' or any indication this is AI-generated
    - DO NOT include the URL (it will be added separately)
    -Act as a seasoned social media strategist specialized in technology. 
    Generate an engaging tweet (max 280 characters) that summarizes today's top technology news. 
    Use the headline '[Insert Headline]' as your basis. Your tweet should include a concise summary of the news, 
    incorporate at least two relevant hashtags (e.g., #TechNews, #Innovation), and end with a call-to-action 
    (e.g., 'Read more' or 'Discover more'). Maintain a  friendly yet professional tone, avoid technical jargon, and make sure the tweet is compelling and easy to understand.
    

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
            print("Unexpected response format:", data)
            return None
    else:
        print("Error generating tweet text:", response.text)
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
        print("Tweet posted. Response:", response)
        return True
    except Exception as e:
        print(f"Error posting tweet: {str(e)}")
        return False

def main():
    print(f"Starting Twitter Bot - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Fetch tech news articles
    articles = fetch_tech_news()
    if not articles:
        print("Failed to fetch tech news articles. Exiting.")
        return
    
    # Step 2: Select the best article
    selected_article = select_best_article(articles)
    
    print("\nSelected Article:")
    print("--------------------------")
    print(f"Title: {selected_article['title']}")
    print(f"Source: {selected_article['source']}")
    print(f"Description: {selected_article['description']}")
    print(f"URL: {selected_article['url']}")
    print("--------------------------")

    # Step 3: Generate tweet text
    print("\nGenerating tweet text using Gemini API...")
    tweet_text = generate_tweet_text(selected_article)
    if not tweet_text:
        print("Failed to generate tweet text. Exiting.")
        return

    print("\nGenerated Tweet Text:")
    print("--------------------------")
    print(tweet_text)
    print("--------------------------")
    
    # Save the tweet draft for review
    draft = {
        "article": selected_article,
        "tweet_text": tweet_text,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    with open("tweet_draft.json", "w") as f:
        json.dump(draft, f, indent=2)
    print("\nDraft saved to tweet_draft.json. Please review the draft.")

    # Wait for manual approval before posting
    approval = input("\nType 'post' to publish the tweet, or any other key to cancel: ")
    if approval.lower() == "post":
        print("Posting tweet...")
        post_tweet(tweet_text)
    else:
        print("Tweet not posted. You can modify the draft if needed.")

if __name__ == "__main__":
    main()
