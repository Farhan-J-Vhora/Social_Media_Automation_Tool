from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from services.facebook import post_to_facebook
from services.instagram import post_to_instagram
import os
import logging

app = Flask(__name__)
app.secret_key = 'demo_secret_key'

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'mov', 'avi'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

logging.basicConfig(level=logging.INFO)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_video(filename):
    return filename.lower().endswith(('mp4', 'mov', 'avi'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/post', methods=['POST'])
def post():
    media_files = request.files.getlist('media')
    caption = request.form.get('caption_general', '')
    platforms = request.form.getlist('platforms')
    action = request.form.get('action')

    if not media_files or media_files[0].filename == '':
        flash('No media selected!')
        return redirect(url_for('index'))

    image_paths, video_paths = [], []

    for media in media_files:
        if media and allowed_file(media.filename):
            filename = secure_filename(media.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            media.save(filepath)
            if is_video(filename):
                video_paths.append(filepath)
            else:
                image_paths.append(filepath)

    all_media = image_paths + video_paths

    results = {}

    if action == 'schedule':
        flash('📅 Post scheduled (demo only)')
    else:
        if 'facebook' in platforms:
            fb_result = post_to_facebook(all_media, caption)
            results['facebook'] = fb_result
            logging.info("Facebook Result: %s", fb_result)

        if 'instagram' in platforms:
            ig_result = post_to_instagram(all_media, caption)
            results['instagram'] = ig_result
            logging.info("Instagram Result: %s", ig_result)

        flash('✅ Posted successfully!')

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
