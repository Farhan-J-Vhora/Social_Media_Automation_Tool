# services/x.py
import tweepy
import logging
import os
from PIL import Image
import tempfile
import mimetypes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Twitter API credentials - these should match your app.py
X_BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAAPCw2wEAAAAAUMmXNfaxXf6dtPUAoLRP9f0z1fg%3DmsAVjyC7hk6SID43ZqAdG61Wr3oEe35wgO9D4m8j7Pf5exZh95"
X_CONSUMER_KEY = "Avdcg3yE0urxkltFW0VrKK9Aw"
X_CONSUMER_SECRET = "adw8H8xte7H5sZSJHjxnMZ3FnH9PUzTH37PWr4lE1KFXu7oZV6"
X_ACCESS_TOKEN = "1941515245194969088-057WiJqt9vE7yKT3K1xkTjAMFPXbO7"
X_ACCESS_TOKEN_SECRET = "HGSDYspTKO0bHYZkFIp9OCI3Xl5OPSpb0TWt1nv3ARwU8"

def initialize_twitter_api():
    """Initialize Twitter API v2 client and v1.1 API for media upload"""
    try:
        # Twitter API v2 client for posting tweets
        client = tweepy.Client(
            consumer_key=X_CONSUMER_KEY,
            consumer_secret=X_CONSUMER_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=True
        )
        
        # Twitter API v1.1 for media upload (required for media)
        auth = tweepy.OAuth1UserHandler(
            consumer_key=X_CONSUMER_KEY,
            consumer_secret=X_CONSUMER_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_TOKEN_SECRET
        )
        
        api_v1 = tweepy.API(auth, wait_on_rate_limit=True)
        
        logger.info("[🐦✅] Twitter API initialized successfully")
        return client, api_v1
        
    except Exception as e:
        logger.error(f"[🐦❌] Failed to initialize Twitter API: {str(e)}")
        return None, None

def validate_media_file(file_path):
    """Validate if the media file is suitable for Twitter"""
    try:
        if not os.path.exists(file_path):
            return False, "File does not exist"
        
        file_size = os.path.getsize(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        
        if mime_type is None:
            return False, "Cannot determine file type"
        
        # Twitter media size limits
        if mime_type.startswith('image/'):
            # Images: 5MB limit
            if file_size > 5 * 1024 * 1024:
                return False, "Image file too large (max 5MB)"
        elif mime_type.startswith('video/'):
            # Videos: 512MB limit
            if file_size > 512 * 1024 * 1024:
                return False, "Video file too large (max 512MB)"
        else:
            return False, "Unsupported file type"
        
        return True, "Valid"
        
    except Exception as e:
        return False, f"Error validating file: {str(e)}"

def optimize_image_for_twitter(image_path):
    """Optimize image for Twitter if needed"""
    try:
        with Image.open(image_path) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Check if image needs resizing (Twitter max: 4096x4096)
            max_size = 4096
            if img.width > max_size or img.height > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Save optimized image to temporary file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
                img.save(temp_file.name, 'JPEG', quality=85, optimize=True)
                logger.info(f"[🐦📸] Optimized image: {image_path} -> {temp_file.name}")
                return temp_file.name
        
        return image_path
        
    except Exception as e:
        logger.error(f"[🐦❌] Error optimizing image {image_path}: {str(e)}")
        return image_path

def upload_media_to_twitter(api_v1, media_paths):
    """Upload media files to Twitter and return media IDs"""
    media_ids = []
    
    for media_path in media_paths:
        try:
            # Validate media file
            is_valid, message = validate_media_file(media_path)
            if not is_valid:
                logger.error(f"[🐦❌] Invalid media file {media_path}: {message}")
                continue
            
            mime_type, _ = mimetypes.guess_type(media_path)
            
            if mime_type.startswith('image/'):
                # Optimize image if needed
                optimized_path = optimize_image_for_twitter(media_path)
                
                # Upload image
                media = api_v1.media_upload(filename=optimized_path)
                media_ids.append(media.media_id)
                logger.info(f"[🐦📸✅] Uploaded image: {media_path} (ID: {media.media_id})")
                
                # Clean up temporary file if created
                if optimized_path != media_path:
                    os.unlink(optimized_path)
                    
            elif mime_type.startswith('video/'):
                # Upload video (chunked upload for large files)
                media = api_v1.media_upload(filename=media_path)
                media_ids.append(media.media_id)
                logger.info(f"[🐦🎥✅] Uploaded video: {media_path} (ID: {media.media_id})")
                
        except Exception as e:
            logger.error(f"[🐦❌] Failed to upload media {media_path}: {str(e)}")
            continue
    
    return media_ids

def post_to_x(text, media_paths=None):
    """
    Post to X (Twitter) with text and optional media
    
    Args:
        text (str): Tweet text (max 280 characters)
        media_paths (list): List of local file paths for media
    
    Returns:
        dict: Result with success status, tweet_id, and error message if any
    """
    try:
        logger.info(f"[🐦] Starting X post with text: '{text[:50]}...' and {len(media_paths) if media_paths else 0} media files")
        
        # Initialize APIs
        client, api_v1 = initialize_twitter_api()
        if not client or not api_v1:
            return {
                'success': False,
                'error': 'Failed to initialize Twitter API'
            }
        
        # Validate tweet text
        if not text or len(text.strip()) == 0:
            return {
                'success': False,
                'error': 'Tweet text cannot be empty'
            }
        
        if len(text) > 280:
            return {
                'success': False,
                'error': f'Tweet text too long ({len(text)}/280 characters)'
            }
        
        # Upload media if provided
        media_ids = []
        if media_paths and len(media_paths) > 0:
            # Filter out empty paths
            valid_paths = [path for path in media_paths if path and os.path.exists(path)]
            
            if len(valid_paths) > 4:
                logger.warning(f"[🐦⚠️] Twitter supports max 4 media files, using first 4 of {len(valid_paths)}")
                valid_paths = valid_paths[:4]
            
            if valid_paths:
                media_ids = upload_media_to_twitter(api_v1, valid_paths)
                
                if len(media_ids) == 0:
                    return {
                        'success': False,
                        'error': 'Failed to upload any media files'
                    }
        
        # Create tweet
        tweet_params = {'text': text}
        if media_ids:
            tweet_params['media_ids'] = media_ids
        
        # Post tweet using API v2
        response = client.create_tweet(**tweet_params)
        
        if response.data:
            tweet_id = response.data['id']
            logger.info(f"[🐦✅] Successfully posted tweet with ID: {tweet_id}")
            return {
                'success': True,
                'tweet_id': tweet_id,
                'tweet_url': f'https://twitter.com/i/web/status/{tweet_id}',
                'media_count': len(media_ids)
            }
        else:
            return {
                'success': False,
                'error': 'Tweet creation failed - no response data'
            }
            
    except tweepy.TooManyRequests:
        logger.error("[🐦❌] Twitter API rate limit exceeded")
        return {
            'success': False,
            'error': 'Twitter API rate limit exceeded. Please try again later.'
        }
    except tweepy.Unauthorized:
        logger.error("[🐦❌] Twitter API unauthorized - check credentials")
        return {
            'success': False,
            'error': 'Twitter API unauthorized. Please check your API credentials.'
        }
    except tweepy.Forbidden:
        logger.error("[🐦❌] Twitter API forbidden - check permissions")
        return {
            'success': False,
            'error': 'Twitter API forbidden. Check your app permissions.'
        }
    except Exception as e:
        logger.error(f"[🐦❌] Unexpected error posting to X: {str(e)}")
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }

def post_thread_to_x(texts, media_paths_per_tweet=None):
    """
    Post a thread to X (Twitter)
    
    Args:
        texts (list): List of tweet texts
        media_paths_per_tweet (list): List of media paths for each tweet
    
    Returns:
        dict: Result with success status and thread info
    """
    try:
        logger.info(f"[🐦🧵] Starting thread post with {len(texts)} tweets")
        
        client, api_v1 = initialize_twitter_api()
        if not client or not api_v1:
            return {
                'success': False,
                'error': 'Failed to initialize Twitter API'
            }
        
        thread_tweet_ids = []
        reply_to_tweet_id = None
        
        for i, text in enumerate(texts):
            # Get media for this tweet
            media_paths = []
            if media_paths_per_tweet and i < len(media_paths_per_tweet):
                media_paths = media_paths_per_tweet[i] or []
            
            # Upload media for this tweet
            media_ids = []
            if media_paths:
                media_ids = upload_media_to_twitter(api_v1, media_paths)
            
            # Create tweet parameters
            tweet_params = {'text': text}
            if media_ids:
                tweet_params['media_ids'] = media_ids
            if reply_to_tweet_id:
                tweet_params['in_reply_to_tweet_id'] = reply_to_tweet_id
            
            # Post tweet
            response = client.create_tweet(**tweet_params)
            
            if response.data:
                tweet_id = response.data['id']
                thread_tweet_ids.append(tweet_id)
                reply_to_tweet_id = tweet_id
                logger.info(f"[🐦🧵✅] Posted tweet {i+1}/{len(texts)} with ID: {tweet_id}")
            else:
                logger.error(f"[🐦🧵❌] Failed to post tweet {i+1}/{len(texts)}")
                break
        
        if thread_tweet_ids:
            return {
                'success': True,
                'thread_tweet_ids': thread_tweet_ids,
                'main_tweet_id': thread_tweet_ids[0],
                'thread_url': f'https://twitter.com/i/web/status/{thread_tweet_ids[0]}'
            }
        else:
            return {
                'success': False,
                'error': 'Failed to post any tweets in thread'
            }
            
    except Exception as e:
        logger.error(f"[🐦🧵❌] Error posting thread: {str(e)}")
        return {
            'success': False,
            'error': f'Thread posting error: {str(e)}'
        }

# Test function
def test_twitter_connection():
    """Test Twitter API connection"""
    try:
        client, api_v1 = initialize_twitter_api()
        if client and api_v1:
            # Test with a simple API call
            user = client.get_me()
            if user.data:
                logger.info(f"[🐦✅] Twitter API connection successful. User: @{user.data.username}")
                return True
        return False
    except Exception as e:
        logger.error(f"[🐦❌] Twitter API connection test failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Test the connection
    print("Testing Twitter API connection...")
    if test_twitter_connection():
        print("✅ Twitter API connection successful!")
    else:
        print("❌ Twitter API connection failed!")