import os
import json
import requests
import logging
import mimetypes
import cloudinary.uploader

# Setup logging
logger = logging.getLogger("LinkedIn")
logger.setLevel(logging.INFO)

# Webhook URL for Make.com
LINKEDIN_WEBHOOK_URL = "https://hook.eu2.make.com/8zs59dsswt9pjevr79uy220lxiq6jfxn"

def determine_media_type(file_path):
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type:
        if mime_type.startswith("image/"):
            return "image"
        elif mime_type.startswith("video/"):
            return "video"
    return "unknown"

def get_file_info(file_path):
    if not os.path.exists(file_path):
        logger.warning(f"[⚠️] File not found: {file_path}")
        return None
    size = os.path.getsize(file_path)
    mime_type, _ = mimetypes.guess_type(file_path)
    return {
        "filename": os.path.basename(file_path),
        "filepath": file_path,
        "size": size,
        "mime_type": mime_type,
        "media_type": determine_media_type(file_path)
    }

def upload_to_cloudinary(file_path):
    if not file_path or not os.path.exists(file_path):
        logger.error(f"[❌] Skipping Cloudinary upload, invalid file path: {file_path}")
        return None

    try:
        logger.info(f"[☁️] Uploading to Cloudinary: {file_path}")
        response = cloudinary.uploader.upload(file_path, resource_type="auto")
        url = response.get("secure_url")
        if url:
            logger.info(f"[✅☁️] Upload successful: {url}")
        else:
            logger.warning(f"[⚠️] Cloudinary response missing URL: {response}")
        return url
    except Exception as e:
        logger.error(f"[❌] Cloudinary upload failed for {file_path}: {e}")
        return None

def prepare_media_data(media_paths):
    media_data = []
    for path in media_paths:
        file_info = get_file_info(path)
        if not file_info:
            continue

        public_url = upload_to_cloudinary(path)
        if not public_url:
            continue

        media_data.append({
            "filename": file_info["filename"],
            "size": file_info["size"],
            "mime_type": file_info["mime_type"],
            "media_type": file_info["media_type"],
            "url": public_url
        })
        logger.info(f"[✅] Uploaded: {file_info['filename']} → {public_url}")
    return media_data

def determine_post_type(media_data):
    image_count = sum(1 for item in media_data if item["media_type"] == "image")
    video_count = sum(1 for item in media_data if item["media_type"] == "video")

    if image_count > 0 and video_count > 0:
        return "mixed_media"
    elif video_count > 1:
        return "multiple_videos"
    elif video_count == 1:
        return "single_video"
    elif image_count > 1:
        return "multiple_images"
    elif image_count == 1:
        return "single_image"
    else:
        return "text_only"

def post_to_linkedin(media_paths, caption, location=None, collaborators=None):
    if not caption or not caption.strip():
        return {"success": False, "error": "Caption is required"}

    logger.info(f"[💼] Preparing LinkedIn post with caption: {caption}")
    media_data = prepare_media_data(media_paths) if media_paths else []
    post_type = determine_post_type(media_data)

    if post_type == "mixed_media":
        logger.error("[❌] Cannot post mixed media (image + video) to LinkedIn")
        return {"success": False, "error": "Mixed media (image + video) not supported"}

    payload = {
        "platform": "linkedin",
        "action": "create_post",
        "post_type": post_type,
        "content": {
            "text": caption,
            "media_count": len(media_data),
            "media_data": media_data
        },
        "metadata": {
            "location": location,
            "collaborators": collaborators,
            "timestamp": None
        },
        "instructions": {
            "type": f"{post_type}_post",
            "description": f"Post LinkedIn content type: {post_type}"
        }
    }

    logger.info(f"[📡] Sending payload to Make.com webhook (type: {post_type})")
    try:
        response = requests.post(
            LINKEDIN_WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        if response.status_code == 200:
            logger.info("[✅] Webhook POST successful")
            try:
                return {
                    "success": True,
                    "status_code": 200,
                    "response": response.json(),
                    "post_type": post_type
                }
            except Exception:
                return {
                    "success": True,
                    "status_code": 200,
                    "response": response.text,
                    "post_type": post_type
                }
        else:
            logger.error(f"[❌] Webhook failed: {response.status_code}")
            return {
                "success": False,
                "error": response.text,
                "status_code": response.status_code
            }
    except Exception as e:
        logger.error(f"[❌] Webhook request error: {e}")
        return {"success": False, "error": str(e)}

def test_linkedin_webhook():
    logger.info("[🔁] Testing LinkedIn webhook...")
    try:
        response = requests.post(
            LINKEDIN_WEBHOOK_URL,
            json={"platform": "linkedin", "action": "test_connection"},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        logger.error(f"[❌] Webhook test failed: {e}")
        return False

if __name__ == "__main__":
    test_result = test_linkedin_webhook()
    print("✅ Webhook is working!" if test_result else "❌ Webhook test failed.")
