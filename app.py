from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from services.facebook import post_to_facebook
from services.instagram import post_to_instagram
import cloudinary.uploader
import os
import logging

app = Flask(__name__)
app.secret_key = 'secure_secret_key'
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'mov', 'avi'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Setup Cloudinary
cloudinary.config(
    cloud_name='dym0h1yft',
    api_key='228843369112734',
    api_secret='VPcN898j5tYol7VorJsRDbTi3eE'
)

logging.basicConfig(level=logging.INFO)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/terms')
def terms_of_service():
    return render_template('terms.html')

@app.route('/post', methods=['POST'])
def post():
    media_files = request.files.getlist('media')
    caption = request.form.get('caption_general', '')
    platforms = request.form.getlist('platforms')
    action = request.form.get('action')

    if not media_files or media_files[0].filename == '':
        flash('No media selected!')
        return redirect(url_for('index'))

    local_paths = []
    cloudinary_urls = []

    for media in media_files:
        if media and allowed_file(media.filename):
            filename = secure_filename(media.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            media.save(filepath)
            logging.info(f"[📤] Uploading: {filename} | Type: {media.mimetype}")
            local_paths.append(filepath)

            # Upload to Cloudinary only for Instagram
            result = cloudinary.uploader.upload(
                filepath,
                resource_type="auto",
                transformation=[{"aspect_ratio": "1:1", "crop": "fill"}] if "image" in media.mimetype else {}
            )
            cloud_url = result["secure_url"]
            cloudinary_urls.append(cloud_url)
            logging.info(f"[🌐] Uploaded to Cloudinary: {cloud_url}")

    results = {}

    if action == 'schedule':
        flash('📅 Post scheduled (demo only)')
    else:
        if 'facebook' in platforms:
            fb_result = post_to_facebook(local_paths, caption)
            results['facebook'] = fb_result
            logging.info("Facebook Result: %s", fb_result)

        if 'instagram' in platforms:
            ig_result = post_to_instagram(cloudinary_urls, caption)
            results['instagram'] = ig_result
            logging.info("Instagram Result: %s", ig_result)

        flash('✅ Post attempted. Check logs for results.')

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
