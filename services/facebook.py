import requests
import os
import mimetypes
import logging

FB_PAGE_ID = "737124382808926"
FB_ACCESS_TOKEN = "EAASRhUoV8BcBOZBx9PxlVa5MmOqJpzC8KhnxnZB1CIPZBfa9K1m0J4Mnrap12fqT0ZAcXzd7YayOZAMLKG5ZC5aEXl601kikVYpKFwOvb3lIl8B5uMHyaLAk6mSGFmJEZA6pak4OTVPTLDZCctzbNDqmKdtUjZCjTKZC6xWLExz11ArRLcbLyVEKPEby3FWLeSCweZCZBOMdtvd4"

def is_video(path):
    mime_type = mimetypes.guess_type(path)[0]
    return mime_type and mime_type.startswith('video')

def is_image(path):
    mime_type = mimetypes.guess_type(path)[0]
    return mime_type and mime_type.startswith('image')

def post_video_to_facebook(video_path, caption):
    """
    Post video directly to Facebook with caption
    This is the method that works with your current token
    """
    try:
        logging.info(f"[📤] Uploading video to Facebook: {video_path}")
        
        # Check if file exists
        if not os.path.exists(video_path):
            logging.error(f"[❌] Video file not found: {video_path}")
            return {"error": "Video file not found"}
        
        # Get file size
        file_size = os.path.getsize(video_path)
        logging.info(f"[📊] Video file size: {file_size / (1024*1024):.2f} MB")
        
        # Upload video directly with caption
        with open(video_path, 'rb') as video_file:
            response = requests.post(
                f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/videos",
                files={'source': video_file},
                data={
                    'description': caption,
                    'access_token': FB_ACCESS_TOKEN
                },
                timeout=300  # 5 minute timeout for large videos
            )
        
        result = response.json()
        logging.info(f"[✅] Video upload response: {result}")
        
        if 'error' in result:
            logging.error(f"[❌] Video upload error: {result['error']}")
            return result
        
        if 'id' in result:
            logging.info(f"[🎉] Video uploaded successfully! ID: {result['id']}")
            return result
        else:
            logging.error(f"[❌] Unexpected response: {result}")
            return {"error": "Unexpected response format"}
            
    except requests.exceptions.Timeout:
        logging.error("[❌] Upload timed out - video might be too large")
        return {"error": "Upload timeout"}
    except Exception as e:
        logging.error(f"[❌] Exception during video upload: {str(e)}")
        return {"error": str(e)}

def post_image_to_facebook(image_path, caption):
    """Post image directly to Facebook with caption"""
    try:
        logging.info(f"[📤] Uploading image to Facebook: {image_path}")
        
        if not os.path.exists(image_path):
            logging.error(f"[❌] Image file not found: {image_path}")
            return {"error": "Image file not found"}
        
        with open(image_path, 'rb') as image_file:
            response = requests.post(
                f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos",
                files={'source': image_file},
                data={
                    'message': caption,
                    'access_token': FB_ACCESS_TOKEN
                }
            )
        
        result = response.json()
        logging.info(f"[✅] Image upload response: {result}")
        
        if 'error' in result:
            logging.error(f"[❌] Image upload error: {result['error']}")
            return result
        
        if 'id' in result:
            logging.info(f"[🎉] Image uploaded successfully! ID: {result['id']}")
            return result
        else:
            logging.error(f"[❌] Unexpected response: {result}")
            return {"error": "Unexpected response format"}
            
    except Exception as e:
        logging.error(f"[❌] Exception during image upload: {str(e)}")
        return {"error": str(e)}

def post_to_facebook(media_paths, caption):
    """
    Main function to post media to Facebook
    Simplified version that works with your current token
    """
    if not media_paths:
        logging.error("[❌] No media files provided")
        return {"error": "No media files provided"}
    
    # Handle single media file (most common case)
    if len(media_paths) == 1:
        media_path = media_paths[0]
        
        if is_video(media_path):
            return post_video_to_facebook(media_path, caption)
        elif is_image(media_path):
            return post_image_to_facebook(media_path, caption)
        else:
            logging.error(f"[❌] Unsupported media type: {media_path}")
            return {"error": "Unsupported media type"}
    
    # Handle multiple media files
    else:
        logging.info(f"[📤] Uploading {len(media_paths)} media files")
        return post_multiple_media_to_facebook(media_paths, caption)

def post_multiple_media_to_facebook(media_paths, caption):
    """
    Handle multiple media files by uploading them unpublished first,
    then creating a post with all attached media
    """
    try:
        media_ids = []
        
        for media_path in media_paths:
            if is_image(media_path):
                logging.info(f"[📤] Uploading image for multi-post: {media_path}")
                with open(media_path, 'rb') as f:
                    response = requests.post(
                        f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos",
                        files={'source': f},
                        data={
                            'published': 'false',
                            'access_token': FB_ACCESS_TOKEN
                        }
                    )
                
                result = response.json()
                if 'id' in result:
                    media_ids.append({'media_fbid': result['id']})
                    logging.info(f"[✅] Image uploaded for multi-post: {result['id']}")
                else:
                    logging.error(f"[❌] Failed to upload image: {result}")
            
            elif is_video(media_path):
                logging.info(f"[📤] Uploading video for multi-post: {media_path}")
                with open(media_path, 'rb') as f:
                    response = requests.post(
                        f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/videos",
                        files={'source': f},
                        data={
                            'published': 'false',
                            'access_token': FB_ACCESS_TOKEN
                        }
                    )
                
                result = response.json()
                if 'id' in result:
                    media_ids.append({'media_fbid': result['id']})
                    logging.info(f"[✅] Video uploaded for multi-post: {result['id']}")
                else:
                    logging.error(f"[❌] Failed to upload video: {result}")
        
        # Create post with all media
        if media_ids:
            logging.info(f"[📎] Creating post with {len(media_ids)} media items")
            post_response = requests.post(
                f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed",
                json={
                    'message': caption,
                    'attached_media': media_ids,
                    'access_token': FB_ACCESS_TOKEN
                }
            )
            
            result = post_response.json()
            logging.info(f"[✅] Multi-media post response: {result}")
            return result
        else:
            return {"error": "Failed to upload any media files"}
            
    except Exception as e:
        logging.error(f"[❌] Exception during multi-media upload: {str(e)}")
        return {"error": str(e)}

# No test_facebook_posting or if __name__ == "__main__": block
# as per user's request to remove testing code.