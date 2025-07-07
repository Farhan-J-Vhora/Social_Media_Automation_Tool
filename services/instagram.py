import requests
import logging
import time

IG_USER_ID = "17841475715869894"  # Replace with your Instagram Business Account ID
ACCESS_TOKEN = "EAASRhUoV8BcBOZBx9PxlVa5MmOqJpzC8KhnxnZB1CIPZBfa9K1m0J4Mnrap12fqT0ZAcXzd7YayOZAMLKG5ZC5aEXl601kikVYpKFwOvb3lIl8B5uMHyaLAk6mSGFmJEZA6pak4OTVPTLDZCctzbNDqmKdtUjZCjTKZC6xWLExz11ArRLcbLyVEKPEby3FWLeSCweZCZBOMdtvd4"

def is_video(url):
    return url.lower().endswith(('mp4', 'mov', 'avi'))

def is_image(url):
    return url.lower().endswith(('png', 'jpg', 'jpeg'))

def check_media_status(creation_id):
    """Check if media is ready for publishing"""
    try:
        status_res = requests.get(
            f"https://graph.facebook.com/v19.0/{creation_id}",
            params={
                'fields': 'status_code',
                'access_token': ACCESS_TOKEN
            }
        ).json()
        
        if 'status_code' in status_res:
            return status_res['status_code'] == 'FINISHED'
        return False
    except Exception as e:
        logging.error(f"[❌] Error checking media status: {e}")
        return False

def publish_instagram_media(creation_id, max_retries=8):
    """Publish Instagram media with improved retry logic"""
    for attempt in range(max_retries):
        # Use exponential backoff: 10, 20, 30, 45, 60, 90, 120, 180 seconds
        # The original code's wait_time calculation was slightly off, adjusted for clarity
        wait_time = min(10 * (attempt + 1), 180) # Simple linear backoff up to 180s
        
        logging.info(f"[⏳] Waiting for Instagram to process video (attempt {attempt + 1}/{max_retries})...")
        logging.info(f"[⏰] Waiting {wait_time} seconds before retry...")
        time.sleep(wait_time)
        
        # Check media status first
        if check_media_status(creation_id):
            logging.info("[✅] Media processing completed, attempting to publish...")
        else:
            logging.info("[⏳] Media still processing...")
        
        publish_res = requests.post(
            f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish",
            data={
                'creation_id': creation_id,
                'access_token': ACCESS_TOKEN
            }
        ).json()
        
        if 'id' in publish_res:
            logging.info(f"[🎉] Video published successfully! Post ID: {publish_res['id']}")
            return publish_res
        elif 'error' in publish_res:
            error_code = publish_res['error'].get('code', 'Unknown')
            error_subcode = publish_res['error'].get('error_subcode', 'Unknown')
            error_msg = publish_res['error'].get('message', 'Unknown error')
            
            logging.warning(f"[⚠️] Attempt {attempt + 1} failed:")
            logging.warning(f"    Error Code: {error_code}")
            logging.warning(f"    Error Subcode: {error_subcode}")
            logging.warning(f"    Message: {error_msg}")
            
            # If it's a permanent error, don't retry
            if error_code in [100, 190, 200]:  # Invalid parameters, access token issues, permissions
                logging.error("[❌] Permanent error detected, stopping retries")
                return publish_res
            
            # If it's the last attempt, return the error
            if attempt == max_retries - 1:
                logging.error(f"[❌] All {max_retries} attempts failed")
                return publish_res
        else:
            logging.warning(f"[⚠️] Unexpected response: {publish_res}")
    
    return {'error': f'Failed to publish video after {max_retries} attempts'}

def post_to_instagram(media_urls, caption):
    images = [url for url in media_urls if is_image(url)]
    videos = [url for url in media_urls if is_video(url)]
    results = [] # This will always be a list of dictionaries

    # ✅ Case 1: Carousel Post with Multiple Images
    if len(images) >= 2 and len(videos) == 0:
        image_ids = []
        for url in images:
            logging.info(f"[📤] Uploading IMAGE for carousel to Instagram: {url}")
            create_res = requests.post(
                f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media",
                data={
                    'image_url': url,
                    'is_carousel_item': 'true',
                    'access_token': ACCESS_TOKEN
                }
            ).json()
            if 'id' in create_res:
                logging.info(f"[✅] Upload response for carousel item: {create_res}")
                image_ids.append(create_res['id'])
            else:
                logging.error(f"[❌] Failed to upload image for carousel: {url} - {create_res}")

        if 2 <= len(image_ids) <= 10:
            logging.info("[🧩] Creating Instagram carousel container with items: %s", image_ids)
            container_res = requests.post(
                f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media",
                data={
                    'media_type': 'CAROUSEL',
                    'children': ','.join(image_ids),
                    'caption': caption,
                    'access_token': ACCESS_TOKEN
                }
            ).json()

            logging.info(f"[✅] Container response: {container_res}")
            if 'id' in container_res:
                publish_res = requests.post(
                    f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish",
                    data={
                        'creation_id': container_res['id'],
                        'access_token': ACCESS_TOKEN
                    }
                ).json()
                results.append(publish_res)
                logging.info(f"[🎉] Carousel post published: {publish_res}")
            else:
                error_msg = container_res.get('error', {}).get('message', 'Unknown error')
                results.append({'error': f'Failed to create carousel container: {error_msg}'})
                logging.error(f"[❌] Failed to create carousel container: {container_res}")
        else:
            results.append({'error': f'Carousel must contain 2–10 images. Found {len(image_ids)} valid images.'})
            logging.warning(f"[⚠️] Carousel creation skipped: {results[-1]['error']}")

    # ✅ Case 2: Single Video -> Instagram Reel
    elif len(videos) == 1 and len(images) == 0:
        url = videos[0]
        logging.info(f"[📤] Uploading SINGLE VIDEO (REEL) to Instagram: {url}")
        
        # Add video validation (this is implicit in Instagram's API, but good to log)
        logging.info("[🔍] Preparing video for Instagram Reels...")
        
        create_res = requests.post(
            f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media",
            data={
                'media_type': 'REELS',
                'video_url': url,
                'caption': caption,
                'access_token': ACCESS_TOKEN
            }
        ).json()
        
        logging.info(f"[✅] Upload response for video creation: {create_res}")

        if 'id' in create_res:
            creation_id = create_res['id']
            logging.info(f"[📋] Media creation ID: {creation_id}")
            
            # Use improved retry mechanism
            publish_res = publish_instagram_media(creation_id)
            results.append(publish_res)
        else:
            error_msg = create_res.get('error', {}).get('message', 'Unknown error')
            logging.error(f"[❌] Failed to upload video: {url} - {error_msg}")
            results.append({'error': f'Failed to upload video: {error_msg}'})

    # ✅ Case 3: Single Image
    elif len(images) == 1 and len(videos) == 0:
        url = images[0]
        logging.info(f"[📤] Uploading SINGLE IMAGE to Instagram: {url}")
        create_res = requests.post(
            f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media",
            data={
                'image_url': url,
                'caption': caption,
                'access_token': ACCESS_TOKEN
            }
        ).json()
        
        if 'id' in create_res:
            logging.info(f"[✅] Upload response for image creation: {create_res}")
            publish_res = requests.post(
                f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish",
                data={
                    'creation_id': create_res['id'],
                    'access_token': ACCESS_TOKEN
                }
            ).json()
            results.append(publish_res)
            logging.info(f"[🎉] Single image published: {publish_res}")
        else:
            error_msg = create_res.get('error', {}).get('message', 'Unknown error')
            logging.error(f"[❌] Failed to upload image: {url} - {error_msg}")
            results.append({'error': f'Failed to upload image: {error_msg}'})

    # ❌ Case 4: Mixed Media or Multiple Videos (Not Supported)
    else:
        error_msg = 'Instagram does NOT support carousels with multiple videos or mixed types. Please provide 1 video, 1 image, or 2-10 images for a carousel.'
        results.append({'error': error_msg})
        logging.warning(f"[⚠️] Instagram posting skipped: {error_msg}")

    return results

# No test_instagram_posting or if __name__ == "__main__": block
# as per user's request to remove testing code.