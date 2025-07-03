import requests
import logging
import time

IG_USER_ID = "17841475715869894"  # Replace with your Instagram Business Account ID
ACCESS_TOKEN = "EAASRhUoV8BcBOZBx9PxlVa5MmOqJpzC8KhnxnZB1CIPZBfa9K1m0J4Mnrap12fqT0ZAcXzd7YayOZAMLKG5ZC5aEXl601kikVYpKFwOvb3lIl8B5uMHyaLAk6mSGFmJEZA6pak4OTVPTLDZCctzbNDqmKdtUjZCjTKZC6xWLExz11ArRLcbLyVEKPEby3FWLeSCweZCZBOMdtvd4"

def is_video(url):
    return url.lower().endswith(('mp4', 'mov', 'avi'))

def is_image(url):
    return url.lower().endswith(('png', 'jpg', 'jpeg'))

def post_to_instagram(media_urls, caption):
    images = [url for url in media_urls if is_image(url)]
    videos = [url for url in media_urls if is_video(url)]
    results = []

    # ✅ Case 1: Carousel Post with Multiple Images
    if len(images) >= 2 and len(videos) == 0:
        image_ids = []
        for url in images:
            logging.info(f"[📤] Uploading IMAGE to Instagram: {url}")
            create_res = requests.post(
                f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media",
                data={
                    'image_url': url,
                    'is_carousel_item': 'true',
                    'access_token': ACCESS_TOKEN
                }
            ).json()
            if 'id' in create_res:
                logging.info(f"[✅] Upload response: {create_res}")
                image_ids.append(create_res['id'])
            else:
                logging.error(f"[❌] Failed to upload image: {url} - {create_res}")

        if 2 <= len(image_ids) <= 10:
            logging.info("[🧩] Creating Instagram carousel container...")
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
            else:
                results.append({'error': 'Failed to create carousel container.'})
        else:
            results.append({'error': 'Carousel must contain 2–10 images only.'})

    # ✅ Case 2: Single Video -> Instagram Reel
    elif len(videos) == 1 and len(images) == 0:
        url = videos[0]
        logging.info(f"[📤] Uploading VIDEO (REEL) to Instagram: {url}")
        create_res = requests.post(
            f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media",
            data={
                'media_type': 'REELS',
                'video_url': url,
                'caption': caption,
                'access_token': ACCESS_TOKEN
            }
        ).json()
        logging.info(f"[✅] Upload response: {create_res}")

        if 'id' in create_res:
            creation_id = create_res['id']
            publish_res = None

            # Retry loop for up to 5 attempts
            for attempt in range(5):
                logging.info(f"[⏳] Waiting for Instagram to process video (attempt {attempt + 1})...")
                time.sleep(3)

                publish_res = requests.post(
                    f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish",
                    data={
                        'creation_id': creation_id,
                        'access_token': ACCESS_TOKEN
                    }
                ).json()

                if 'id' in publish_res:
                    logging.info(f"[✅] Publish success: {publish_res}")
                    break
                else:
                    logging.warning(f"[⚠️] Retry due to: {publish_res}")

            results.append(publish_res or {'error': 'Failed to publish video after retries.'})
        else:
            results.append({'error': f'Failed to upload video: {url}'})

    # ❌ Case 3: Mixed Media or Multiple Videos (Not Supported)
    else:
        results.append({'error': 'Instagram does NOT support carousels with multiple videos or mixed types.'})

    return results
