import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json

def create_base_folder():
    """Create the main folder for all posts if it doesn't exist."""
    folder_name = 'zolbarsakusun'
    os.makedirs(folder_name, exist_ok=True)
    return folder_name

def create_folder(base_folder, post_id):
    """Create a folder for the post if it doesn't exist."""
    folder_path = os.path.join(base_folder, post_id)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path

def download_image(url, folder, filename):
    """Download an image and save it to the specified folder."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        file_path = os.path.join(folder, filename)
        with open(file_path, 'wb') as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"Error downloading image {url}: {str(e)}")
        return False

def extract_poster_from_title(title):
    """Extract the poster's username from the page title.
    
    Handles variations like 'on Twitter:', 'auf Twitter:', etc.
    
    Args:
        title (str): The page title to parse
        
    Returns:
        str|None: The extracted username if found, None otherwise
    """
    if title:
        # Match pattern with various language versions
        match = re.search(r'(.*?)\s+(?:on|auf|sur|en|на)\s+Twitter:', title)
        if match:
            return match.group(1).strip()
    return None

def get_main_tweet(soup):
    """Get the main tweet content, ignoring replies."""
    # First try to find the tweet that matches the title poster
    title = soup.find('title')
    if title:
        poster = extract_poster_from_title(title.text)
        if poster:
            # Find the tweet from the specific poster
            tweets = soup.find_all('div', class_='tweet')
            for tweet in tweets:
                tweet_poster = tweet.find('strong', class_='fullname')
                if tweet_poster and tweet_poster.text.strip() == poster:
                    return tweet
    
    # If we can't find the specific poster's tweet, return the permalink tweet
    return soup.find('div', class_='permalink-tweet')

def scrape_post(base_url, post_link, base_folder):
    """Scrape a single post page."""
    try:
        # Get the post ID from the link
        post_id = post_link.split('/')[-1].split('_')[0]
        
        # Create folder for this post inside the base folder
        post_folder = create_folder(base_folder, post_id)
        
        # Get the post page
        post_url = urljoin(base_url, post_link)
        response = requests.get(post_url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get the main tweet content
        tweet = get_main_tweet(soup)
        if not tweet:
            print(f"Could not find tweet content for {post_id}")
            return
        
        # Extract tweet text
        tweet_text_elem = tweet.find('p', class_='tweet-text')
        if tweet_text_elem:
            tweet_text = tweet_text_elem.get_text().strip()
            
            # Save tweet text
            with open(os.path.join(post_folder, 'text.txt'), 'w', encoding='utf-8') as f:
                f.write(tweet_text)
        
        # Find and download images
        media_container = tweet.find('div', class_='AdaptiveMedia-container')
        if media_container:
            # Find all images
            images = media_container.find_all('img')
            for idx, img in enumerate(images):
                if img.get('src'):
                    # Handle both relative and absolute URLs
                    img_url = urljoin(base_url, img['src'])
                    filename = f'image_{idx+1}.jpg'
                    download_image(img_url, post_folder, filename)
        
        # Extract poster information
        poster = extract_poster_from_title(soup.find('title').text if soup.find('title') else None)
        
        # Save metadata
        metadata = {
            'post_id': post_id,
            'url': post_url,
            'poster': poster,
            'timestamp': tweet.find('a', class_='tweet-timestamp').get('title') if tweet.find('a', class_='tweet-timestamp') else None
        }
        with open(os.path.join(post_folder, 'metadata.json'), 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
            
        print(f"Successfully scraped post {post_id} by {poster}")
        
    except Exception as e:
        print(f"Error scraping post {post_link}: {str(e)}")

def main():
    base_url = "https://archive.amarna-forum.net/hakan/twitter/02_ZolbarSakusun/"
    
    try:
        # Create the base folder
        base_folder = create_base_folder()
        
        # Get the main page
        response = requests.get(base_url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all post links in the table
        post_links = []
        for row in soup.find_all('tr'):
            link_cell = row.find('td')
            if link_cell and link_cell.find('a'):
                post_links.append(link_cell.find('a')['href'])
        
        # Scrape each post
        for link in post_links:
            scrape_post(base_url, link, base_folder)
            
    except Exception as e:
        print(f"Error accessing main page: {str(e)}")

if __name__ == "__main__":
    main()