import requests
import os

FB_PAGE_ID = "737124382808926"
FB_ACCESS_TOKEN = "EAAPCBbiv63YBO..."

def is_video(filename):
    return filename.lower().endswith(('mp4', 'mov', 'avi'))

def is_image(filename):
    return filename.lower().endswith(('png', 'jpg', 'jpeg'))

def post_single_image(path, caption):
    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
    with open(path, 'rb') as f:
        files = {'source': f}
        data = {'caption': caption, 'access_token': FB_ACCESS_TOKEN}
        return requests.post(url, files=files, data=data).json()

def post_single_video(path, caption):
    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/videos"
    with open(path, 'rb') as f:
        files = {'source': f}
        data = {'description': caption, 'access_token': FB_ACCESS_TOKEN}
        return requests.post(url, files=files, data=data).json()

def post_multiple_images(paths, caption):
    media_ids = []
    for path in paths:
        url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/photos"
        with open(path, 'rb') as f:
            files = {'source': f}
            data = {'published': 'false', 'access_token': FB_ACCESS_TOKEN}
            res = requests.post(url, files=files, data=data).json()
            if 'id' in res:
                media_ids.append({'media_fbid': res['id']})
    post_url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
    return requests.post(post_url, json={
        'message': caption,
        'attached_media': media_ids,
        'access_token': FB_ACCESS_TOKEN
    }).json()

def post_to_facebook(media_paths, caption):
    images = [p for p in media_paths if is_image(p)]
    videos = [p for p in media_paths if is_video(p)]
    results = []

    if len(images) > 1:
        results.append(post_multiple_images(images, caption))
    else:
        for img in images:
            results.append(post_single_image(img, caption))

    for vid in videos:
        results.append(post_single_video(vid, caption))

    return results
