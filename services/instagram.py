import requests
import os

IG_USER_ID = "17841475715869894"  # from /{page-id}?fields=instagram_business_account
ACCESS_TOKEN = "EAAPCBbiv63YBO..."

def is_video(filename):
    return filename.lower().endswith(('mp4', 'mov', 'avi'))

def is_image(filename):
    return filename.lower().endswith(('png', 'jpg', 'jpeg'))

def upload_image(filepath, caption):
    image_url = f"https://your-domain.com/{filepath.replace('static/', '')}"  # Host required
    creation_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media"
    publish_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish"

    create_res = requests.post(creation_url, data={
        'image_url': image_url,
        'caption': caption,
        'access_token': ACCESS_TOKEN
    }).json()

    if 'id' in create_res:
        return requests.post(publish_url, data={
            'creation_id': create_res['id'],
            'access_token': ACCESS_TOKEN
        }).json()
    return create_res

def upload_video(filepath, caption):
    video_url = f"https://your-domain.com/{filepath.replace('static/', '')}"
    creation_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media"
    publish_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish"

    create_res = requests.post(creation_url, data={
        'media_type': 'VIDEO',
        'video_url': video_url,
        'caption': caption,
        'access_token': ACCESS_TOKEN
    }).json()

    if 'id' in create_res:
        return requests.post(publish_url, data={
            'creation_id': create_res['id'],
            'access_token': ACCESS_TOKEN
        }).json()
    return create_res

def post_to_instagram(media_paths, caption):
    results = []
    for path in media_paths:
        if is_image(path):
            results.append(upload_image(path, caption))
        elif is_video(path):
            results.append(upload_video(path, caption))
    return results
