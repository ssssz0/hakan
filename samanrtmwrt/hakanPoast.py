import os
import json
import random
import time
import schedule
import tweepy
import re
from datetime import datetime
from pathlib import Path

class ArchiveBot:
    def __init__(self):
        # Initialize v2 client with all credentials
        self.client = tweepy.Client(
            bearer_token="AAAAAAAAAAAAAAAAAAAAAL0bxgEAAAAA4mRQTOjXp%2FHBLGZCI73VjrKNZbo%3DYLfNGbrdlFRHOIRV1QmTuDZ443cm2mzw1vMAjBzW481xAveOMr",
            consumer_key="wIByb9TDbrNZHzUo7EkEGdaqx",
            consumer_secret="1kcB3GxNrG8jgSP49koBbq78epqZWPqKhoBCoXcrMdhiklytmI",
            access_token="1804297192733085697-uf4ECdoh47o3M3IRXsFBZswjLgjaIg",
            access_token_secret="GIj2w6jLSPOhtzNaKoHoXZhNKjLUBImbQuOvVchYLeSBC",
            wait_on_rate_limit=True
        )

        # Initialize v1.1 API for media upload
        auth = tweepy.OAuth1UserHandler(
            "wIByb9TDbrNZHzUo7EkEGdaqx",
            "1kcB3GxNrG8jgSP49koBbq78epqZWPqKhoBCoXcrMdhiklytmI",
            "1804297192733085697-uf4ECdoh47o3M3IRXsFBZswjLgjaIg",
            "GIj2w6jLSPOhtzNaKoHoXZhNKjLUBImbQuOvVchYLeSBC"
        )
        self.api = tweepy.API(auth)
        
        # Initialize history tracking
        self.history_file = 'post_history.json'
        self.posted_ids = self.load_history()
        
        # Archive directory
        self.archive_dir = Path('samanrtmwrt')
        
        # Temp directory for image processing
        self.temp_dir = Path('temp')
        if not self.temp_dir.exists():
            self.temp_dir.mkdir()

    def load_history(self):
        """Load the history of posted tweet IDs"""
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r') as f:
                return set(json.load(f))
        return set()
    
    def save_history(self):
        """Save the history of posted tweet IDs"""
        with open(self.history_file, 'w') as f:
            json.dump(list(self.posted_ids), f)
    
    def clean_tweet_text(self, text):
        """Remove Twitter image URLs and clean up text"""
        # Remove pic.twitter.com links and t.co links
        cleaned_text = re.sub(r'https?://t\.co/\w+', '', text)
        cleaned_text = re.sub(r'pic\.twitter\.com/\w+', '', cleaned_text)
        # Remove any hanging ellipsis from truncated tweets
        cleaned_text = re.sub(r'…\s*$', '', cleaned_text)
        # Remove any double spaces created by the cleaning
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)
        return cleaned_text.strip()

    def process_image(self, image_path):
        """Process and prepare image for upload"""
        temp_path = self.temp_dir / f"temp_{os.path.basename(image_path)}"
        # Copy image to temp directory
        with open(image_path, 'rb') as src, open(temp_path, 'wb') as dst:
            dst.write(src.read())
        return temp_path

    def upload_media(self, image_paths):
        """Upload images to Twitter and return media IDs"""
        media_ids = []
        try:
            for image_path in image_paths[:4]:  # Twitter allows max 4 images
                print(f"Uploading image: {image_path}")
                # Process image
                temp_path = self.process_image(image_path)
                # Upload using v1.1 API
                media = self.api.media_upload(filename=str(temp_path))
                media_ids.append(media.media_id)
                # Clean up temp file
                temp_path.unlink()
            return media_ids
        except Exception as e:
            print(f"Error uploading media: {str(e)}")
            return None
        
    def get_available_posts(self):
        """Get list of available post IDs that haven't been posted yet"""
        all_posts = set(folder.name for folder in self.archive_dir.iterdir() 
                       if folder.is_dir() and not folder.name.startswith('.'))
        return list(all_posts - self.posted_ids)
    
    def get_post_content(self, post_id):
        """Get the content of a specific post"""
        post_dir = self.archive_dir / post_id
        
        # Read metadata
        with open(post_dir / 'metadata.json', 'r', encoding='utf-8') as f:
            metadata = json.load(f)
            
        # Read text content
        with open(post_dir / 'text.txt', 'r', encoding='utf-8') as f:
            text = f.read().strip()
            
        # Clean the text
        text = self.clean_tweet_text(text)
        
        # Check if it's a retweet
        poster = metadata.get('poster', '')
        if poster and poster not in ['samanrtmwrt', 'ZolbarSakusun']:
            text = f"RT from {poster}: {text}"
            
        # Get image paths if they exist
        images = list(post_dir.glob('image_*.jpg'))
        
        return text, metadata, images

    def post_tweet(self):
        """Post a random tweet from the archive"""
        try:
            available_posts = self.get_available_posts()
            
            if not available_posts:
                print("All posts have been used. Resetting history.")
                self.posted_ids.clear()
                available_posts = self.get_available_posts()
            
            # Select random post
            post_id = random.choice(available_posts)
            print(f"Selected post: {post_id}")
            
            # Get post content
            text, metadata, images = self.get_post_content(post_id)
            print(f"Found {len(images)} images")
            
            # Ensure text is within Twitter's character limit (280)
            if len(text) > 280:
                text = text[:277] + "..."

            # Upload images if they exist
            media_ids = None
            if images:
                try:
                    print("Uploading images...")
                    media_ids = self.upload_media(images)
                    print(f"Successfully uploaded {len(media_ids)} images")
                except Exception as e:
                    print(f"Error uploading media: {str(e)}")

            # Post to Twitter
            try:
                print("Creating tweet...")
                if media_ids:
                    response = self.client.create_tweet(
                        text=text,
                        media_ids=media_ids
                    )
                else:
                    response = self.client.create_tweet(
                        text=text
                    )
                
                if response.data:
                    print(f"Successfully posted tweet {post_id} at {datetime.now()}")
                    if media_ids:
                        print(f"Included {len(media_ids)} images")
                    # Add to history
                    self.posted_ids.add(post_id)
                    self.save_history()
                else:
                    print(f"Failed to post tweet {post_id}")
                    
            except Exception as e:
                print(f"Error creating tweet: {str(e)}")
                
        except Exception as e:
            print(f"Error in post_tweet: {str(e)}")

def main():
    bot = ArchiveBot()
    
    print("Starting bot...")
    
    # Post once immediately
    print("Posting initial tweet...")
    bot.post_tweet()
    
    # Then set up the schedule
    print("Setting up 3-hour schedule...")
    schedule.every(3).hours.do(bot.post_tweet)
    
    print("Bot is running! Will post every 3 hours...")
    
    # Keep the script running
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)
        except KeyboardInterrupt:
            print("\nBot stopped by user")
            break
        except Exception as e:
            print(f"Error in main loop: {str(e)}")
            time.sleep(60)  # Wait a minute before retrying

if __name__ == "__main__":
    main()