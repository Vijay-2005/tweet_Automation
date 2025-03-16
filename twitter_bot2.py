import os
import json
import requests
import tweepy
from datetime import datetime
import random

def fetch_tech_news():
    """
    Fetches the latest tech news articles using NewsAPI.
    Returns a list of news articles with titles, descriptions, and URLs.
    """
    NEWS_API_KEY = "b1bd05a03cc543f29cca50a1e93e455a"  # Replace with your NewsAPI key
    
    # Increased pageSize to ensure we have plenty of articles to cycle through
    url = f"https://newsapi.org/v2/top-headlines?category=technology&language=en&pageSize=15&apiKey={NEWS_API_KEY}"
    
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
        print("All articles have been used. Fetching fresh news...")
        return None
    
    # Randomly select from available articles
    selected_index = random.choice(available_articles)
    
    print(f"\nSelected Article {selected_index + 1} of {len(articles)}:")
    print("--------------------------")
    print(f"Title: {articles[selected_index]['title']}")
    print(f"Source: {articles[selected_index]['source']}")
    print(f"Description: {articles[selected_index]['description']}")
    print(f"URL: {articles[selected_index]['url']}")
    print("--------------------------")
    
    return selected_index

def generate_tweet_text(article):
    """
    Uses the Gemini API to generate a tweet about the selected tech article.
    """
    GEMINI_API_KEY = "AIzaSyBxZGMn3QOfvVzsiVHLPYRjUP_Xcqtpf0s"
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
            print("Unexpected response format:", data)
            return None
    else:
        print("Error generating tweet text:", response.text)
        return None

def post_tweet(tweet_text):
    """
    Posts the tweet using Twitter's API.
    """
    BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAAJJspwEAAAAA7oxShKueYbdkd9USZpGreiZSQl0%3D8QMdOibgIjGuIU84R38X8VfC9VgM6LXC0elTnlaqdc0EcmpBWu"
    CONSUMER_KEY = "V3ea4VkgWuUrdBwcz2cFROTLA"
    CONSUMER_SECRET = "HoMRQg1tOcXvNMJFCxu3HRNcVdq7Jq8bNSWmF6ksdIRLxazPjS"
    ACCESS_TOKEN = "1635973611080269825-myajTJ5j7WGtDbSzPk8aQaYybxx4gX"
    ACCESS_TOKEN_SECRET = "DB95qIIgaqIvMnTh253qOsI15FAYM4armbg66K0otc78o"
    
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
    
    # Keep track of used article indices
    used_indices = []
    
    while True:
        # Step 2: Select an article that hasn't been used yet
        selected_index = select_article(articles, used_indices)
        
        # If all articles have been used, fetch new ones
        if selected_index is None:
            articles = fetch_tech_news()
            if not articles:
                print("Failed to fetch tech news articles. Exiting.")
                return
            used_indices = []
            selected_index = select_article(articles, used_indices)
        
        # Mark this article as used
        used_indices.append(selected_index)
        selected_article = articles[selected_index]

        # Step 3: Generate tweet text
        print("\nGenerating tweet text using Gemini API...")
        tweet_text = generate_tweet_text(selected_article)
        if not tweet_text:
            print("Failed to generate tweet text. Trying another article...")
            continue

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

        # Wait for user response with multiple options
        print("\nOptions:")
        print("1. Type 'post' to publish this tweet")
        print("2. Type 'new' to generate a tweet about a different article")
        print("3. Type 'exit' to quit without posting")
        
        approval = input("Your choice: ").lower()
        
        if approval == "post":
            print("Posting tweet...")
            post_tweet(tweet_text)
            break
        elif approval == "new":
            print("Looking for a new article...")
            continue
        elif approval == "exit":
            print("Exiting without posting.")
            break
        else:
            print("Invalid choice. Please try again.")
            continue

if __name__ == "__main__":
    main()