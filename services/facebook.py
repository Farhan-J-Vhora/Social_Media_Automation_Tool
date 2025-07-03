import requests
import os
import mimetypes
import logging

FB_PAGE_ID = "737124382808926"
FB_ACCESS_TOKEN = "EAASRhUoV8BcBOZBx9PxlVa5MmOqJpzC8KhnxnZB1CIPZBfa9K1m0J4Mnrap12fqT0ZAcXzd7YayOZAMLKG5ZC5aEXl601kikVYpKFwOvb3lIl8B5uMHyaLAk6mSGFmJEZA6pak4OTVPTLDZCctzbNDqmKdtUjZCjTKZC6xWLExz11ArRLcbLyVEKPEby3FWLeSCweZCZBOMdtvd4"

def is_video(path):
    return mimetypes.guess_type(path)[0].startswith('video')

def is_image(path):
    return mimetypes.guess_type(path)[0].startswith('image')

def post_to_facebook(media_paths, caption):
    image_ids = []
    for path in media_paths:
        try:
            if is_image(path):
                logging.info(f"[📤] Uploading image to Facebook: {path}")
                with open(path, 'rb') as f:
                    res = requests.post(
                        f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos",
                        files={'source': f},
                        data={'published': 'false', 'access_token': FB_ACCESS_TOKEN}
                    ).json()
                    logging.info(f"[✅] Upload response: {res}")
                    if 'id' in res:
                        image_ids.append({'media_fbid': res['id']})

            elif is_video(path):
                logging.info(f"[📤] Uploading video to Facebook: {path}")
                with open(path, 'rb') as f:
                    res = requests.post(
                        f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/videos",
                        files={'source': f},
                        data={'published': 'false', 'access_token': FB_ACCESS_TOKEN}
                    ).json()
                    logging.info(f"[✅] Upload response: {res}")
                    if 'id' in res:
                        image_ids.append({'media_fbid': res['id']})
                    else:
                        logging.error(f"[❌] Failed to upload media: {path}")
        except Exception as e:
            logging.error(f"[❌] Error uploading to Facebook: {e}")

    if image_ids:
        logging.info(f"[📎] Attaching media to a post: {image_ids}")
        post_url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
        post_res = requests.post(post_url, json={
            'message': caption,
            'attached_media': image_ids,
            'access_token': FB_ACCESS_TOKEN
        }).json()
        logging.info(f"[✅] Final post response: {post_res}")
        return post_res

    return {"error": "Failed to create Facebook post"}
