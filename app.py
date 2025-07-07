# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
import os
import logging
import sqlite3
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
import json
import atexit
import cloudinary.uploader

# Import social media service modules
# Ensure these files (facebook.py, instagram.py, x.py) are in your 'services' directory
from services.facebook import post_to_facebook
from services.instagram import post_to_instagram
from services.linkedin import post_to_linkedin
from services.x import post_to_x # Assuming x.py is the name for your Twitter module

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_here' # !!! IMPORTANT: Change this to a strong, unique secret key in production!

UPLOAD_FOLDER = 'static/uploads'
# Added 'webp' and 'gif' to allowed extensions for more image flexibility
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'mov', 'avi', 'webp', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    logging.info(f"[📁] Created UPLOAD_FOLDER at: {UPLOAD_FOLDER}")
else:
    logging.info(f"[📁] UPLOAD_FOLDER already exists at: {UPLOAD_FOLDER}")

# Setup Cloudinary
cloudinary.config(
    cloud_name='dym0h1yft',
    api_key='228843369112734',
    api_secret='VPcN898j5tYol7VorJsRDbTi3eE'
)
logging.info("[☁️] Cloudinary configured.")

# --- X (Twitter) API Credentials ---
# These are your credentials provided in the previous turn.
# For production, consider using environment variables (e.g., python-dotenv)
X_CONSUMER_KEY = "wgFpPxuznODhBOscE7B71qbqB"
X_CONSUMER_SECRET = "iMJIH5LTAjfKJkdYYQ2MhF0JkFUcIAmoOSdU8sXMLvO2ZNEger" # Corrected based on your provided value
X_ACCESS_TOKEN = "1940284786201042946-sZKnnCHwfgSIKBtbax7ONYSa0xLI8h"
X_ACCESS_TOKEN_SECRET = "nfvE9Ppl2BS0eiC1Uz8xMALLoZDJZtCRLq3EifyMl5AMr" # Corrected based on your provided value
logging.info("[🔑] X (Twitter) API credentials loaded in app.py.")

# Configure logging for the Flask app
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
app_logger = logging.getLogger(__name__)
app_logger.info("[🚀] Flask app started and logging configured.")

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.start()
app_logger.info("[⏰] APScheduler started in background.")

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())
app_logger.info("[ graceful_shutdown] Registered scheduler shutdown with atexit.")

def init_db():
    """Initializes the SQLite database for scheduled posts."""
    conn = None
    try:
        conn = sqlite3.connect('scheduled_posts.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                media_files TEXT NOT NULL,           -- Local paths of uploaded media
                cloudinary_urls TEXT NOT NULL,       -- Cloudinary URLs of uploaded media
                caption_general TEXT,
                caption_twitter TEXT,
                platforms TEXT NOT NULL,             -- JSON array of platforms
                location TEXT,
                collaborators TEXT,
                scheduled_time DATETIME NOT NULL,
                status TEXT DEFAULT 'pending',       -- pending, processing, completed, failed
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                posted_at DATETIME,                  -- Actual time of posting
                error_message TEXT
            )
        ''')
        conn.commit()
        app_logger.info("[💾] Database 'scheduled_posts.db' initialized successfully.")
    except sqlite3.Error as e:
        app_logger.error(f"[❌ DB] Database initialization failed: {e}")
    finally:
        if conn:
            conn.close()

def allowed_file(filename):
    """Checks if a file's extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def execute_scheduled_post(post_id):
    """
    Function executed by the scheduler to post content to social media.
    This function runs in a background thread.
    """
    conn = sqlite3.connect('scheduled_posts.db')
    cursor = conn.cursor()
    try:
        app_logger.info(f"[📅] Attempting to execute scheduled post {post_id}.")
        cursor.execute('SELECT * FROM scheduled_posts WHERE id = ? AND status = "pending"', (post_id,))
        post = cursor.fetchone()

        if not post:
            app_logger.warning(f"[⚠️] Scheduled post {post_id} not found or no longer pending. Skipping execution.")
            return

        post_data = {
            'id': post[0],
            'media_files': json.loads(post[1]),
            'cloudinary_urls': json.loads(post[2]),
            'caption_general': post[3],
            'caption_twitter': post[4],
            'platforms': json.loads(post[5]),
            'location': post[6],
            'collaborators': post[7],
            'scheduled_time': post[8]
        }
        app_logger.info(f"[📅] Executing post {post_id} for platforms: {post_data['platforms']} (Scheduled: {post_data['scheduled_time']})")

        # Update status to processing
        cursor.execute('UPDATE scheduled_posts SET status = "processing" WHERE id = ?', (post_id,))
        conn.commit()
        app_logger.info(f"[🔄] Updated post {post_id} status to 'processing'.")

        results = {}
        overall_success = True
        error_messages = []

        # --- Facebook Post ---
        if 'facebook' in post_data['platforms']:
            try:
                app_logger.info(f"[📘] Posting to Facebook for post {post_id}...")
                fb_result = post_to_facebook(post_data['media_files'], post_data['caption_general'])
                results['facebook'] = fb_result
                
                # Facebook's post_to_facebook returns a dict with 'id' on success, or 'error' on failure
                if isinstance(fb_result, dict) and 'id' in fb_result:
                    app_logger.info(f"[✅📘] Facebook post for {post_id} successful: {fb_result.get('id')}")
                else:
                    overall_success = False
                    error_messages.append(f"Facebook: {fb_result.get('error', 'Unknown error or unexpected response')}")
                    app_logger.error(f"[❌📘] Facebook post for {post_id} failed: {fb_result}")
            except Exception as e:
                overall_success = False
                error_messages.append(f"Facebook: Exception - {str(e)}")
                app_logger.exception(f"[❌📘] Exception during Facebook post for {post_id}")

        # --- Instagram Post ---
        if 'instagram' in post_data['platforms']:
            try:
                app_logger.info(f"[📷] Posting to Instagram for post {post_id}...")
                ig_results_list = post_to_instagram(post_data['cloudinary_urls'], post_data['caption_general'])
                results['instagram'] = ig_results_list # Store the list of results
                
                # Instagram's post_to_instagram returns a LIST of dictionaries.
                # We need to check if any of the results indicate success.
                instagram_success = False
                instagram_errors = []
                if isinstance(ig_results_list, list):
                    for res in ig_results_list:
                        if isinstance(res, dict) and 'id' in res: # Success for a single item in list
                            instagram_success = True
                            app_logger.info(f"[✅📷] Instagram item published: {res.get('id')}")
                        elif isinstance(res, dict) and 'error' in res:
                            instagram_errors.append(res.get('error', 'Unknown error'))
                        else:
                            instagram_errors.append(f"Unexpected Instagram response item: {res}")
                else:
                    # This case should ideally not happen if instagram.py always returns a list
                    instagram_errors.append(f"Instagram returned unexpected type: {type(ig_results_list)}")

                if instagram_success:
                    app_logger.info(f"[✅📷] Instagram post for {post_id} successful.")
                else:
                    overall_success = False
                    error_messages.append(f"Instagram: {'; '.join(instagram_errors) if instagram_errors else 'No successful items'}")
                    app_logger.error(f"[❌📷] Instagram post for {post_id} failed: {'; '.join(instagram_errors)}")
            except Exception as e:
                overall_success = False
                error_messages.append(f"Instagram: Exception - {str(e)}")
                app_logger.exception(f"[❌📷] Exception during Instagram post for {post_id}")
        
        if 'linkedin' in post_data['platforms']:
            try:
                app_logger.info(f"[💼] Posting to LinkedIn for post {post_id}...")
                linkedin_result = post_to_linkedin(post_data['media_files'], post_data['caption_general'], post_data['location'], post_data['collaborators'])
                results['linkedin'] = linkedin_result
                
                # LinkedIn's post_to_linkedin returns a dict with 'success' boolean
                if isinstance(linkedin_result, dict) and linkedin_result.get('success'):
                    app_logger.info(f"[✅💼] LinkedIn post for {post_id} successful: {linkedin_result.get('post_type')}")
                else:
                    overall_success = False
                    error_messages.append(f"LinkedIn: {linkedin_result.get('error', 'Unknown error or unexpected response')}")
                    app_logger.error(f"[❌💼] LinkedIn post for {post_id} failed: {linkedin_result}")
            except Exception as e:
                overall_success = False
                error_messages.append(f"LinkedIn: Exception - {str(e)}")
                app_logger.exception(f"[❌💼] Exception during LinkedIn post for {post_id}")


        # --- X (Twitter) Post ---
        if 'x' in post_data['platforms']:
            try:
                app_logger.info(f"[🐦] Posting to X (Twitter) for post {post_id}...")
                x_result = post_to_x(text=post_data['caption_twitter'], media_paths=post_data['media_files'])
                results['x'] = x_result
                
                # X's post_to_x returns a dict with 'success' boolean
                if isinstance(x_result, dict) and x_result.get('success'):
                    app_logger.info(f"[✅🐦] X (Twitter) post for {post_id} successful: {x_result.get('tweet_id')}")
                else:
                    overall_success = False
                    error_messages.append(f"X (Twitter): {x_result.get('error', 'Unknown error or unexpected response')}")
                    app_logger.error(f"[❌🐦] X (Twitter) post for {post_id} failed: {x_result}")
            except Exception as e:
                overall_success = False
                error_messages.append(f"X (Twitter): Exception - {str(e)}")
                app_logger.exception(f"[❌🐦] Exception during X (Twitter) post for {post_id}")

        # --- Final Status Update ---
        if overall_success:
            cursor.execute('''
                UPDATE scheduled_posts
                SET status = "completed", posted_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (post_id,))
            app_logger.info(f"[✅] Scheduled post {post_id} completed successfully for all selected platforms.")
        else:
            final_error_msg = "; ".join(error_messages) if error_messages else "Unknown error during multi-platform post."
            cursor.execute('''
                UPDATE scheduled_posts
                SET status = "failed", error_message = ?, posted_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (final_error_msg, post_id))
            app_logger.error(f"[❌] Scheduled post {post_id} failed for one or more platforms: {final_error_msg}")
        conn.commit()
    except Exception as e:
        app_logger.exception(f"[❌] Critical error during execution of scheduled post {post_id}: {str(e)}")
        # Attempt to update status to failed even if there's an internal error
        try:
            cursor.execute('''
                UPDATE scheduled_posts
                SET status = "failed", error_message = ?, posted_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (f"System Error: {str(e)}", post_id))
            conn.commit()
        except Exception as db_e:
            app_logger.error(f"[❌ DB] Failed to update post {post_id} status after critical error: {db_e}")
    finally:
        if conn:
            conn.close()

@app.route('/')
def index():
    """Renders the main posting form page."""
    app_logger.info("[🌐] Serving index.html.")
    return render_template('index3.html')

@app.route('/privacy-policy')
def privacy_policy():
    """Renders the privacy policy page."""
    app_logger.info("[🌐] Serving privacy_policy.html.")
    return render_template('privacy_policy.html')

@app.route('/terms')
def terms_of_service():
    """Renders the terms of service page."""
    app_logger.info("[🌐] Serving terms.html.")
    return render_template('terms.html')

@app.route('/scheduled-posts')
def scheduled_posts():
    """Displays a list of all scheduled posts from the database."""
    app_logger.info("[🌐] Fetching scheduled posts for display.")
    conn = None
    posts_list = []
    try:
        conn = sqlite3.connect('scheduled_posts.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, platforms, caption_general, scheduled_time, status, created_at, posted_at, error_message
            FROM scheduled_posts
            ORDER BY scheduled_time DESC
        ''')
        posts = cursor.fetchall()

        for post in posts:
            posts_list.append({
                'id': post[0],
                'platforms': json.loads(post[1]),
                'caption': post[2][:100] + '...' if post[2] and len(post[2]) > 100 else post[2],
                'scheduled_time': post[3],
                'status': post[4],
                'created_at': post[5],
                'posted_at': post[6],
                'error_message': post[7]
            })
        app_logger.info(f"[💾] Retrieved {len(posts_list)} scheduled posts from DB.")
    except sqlite3.Error as e:
        app_logger.error(f"[❌ DB] Error fetching scheduled posts: {e}")
        flash('Error retrieving scheduled posts from database.')
    finally:
        if conn:
            conn.close()
    return render_template('scheduled_posts.html', posts=posts_list)

@app.route('/api/scheduled-posts-data')
def api_scheduled_posts_data():
    """Provides a JSON API endpoint for scheduled post data."""
    app_logger.info("[📊] API request for scheduled post data.") # Added log to confirm hit
    conn = None
    posts_list = []
    try:
        conn = sqlite3.connect('scheduled_posts.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, platforms, caption_general, scheduled_time, status, created_at, posted_at, error_message
            FROM scheduled_posts
            ORDER BY scheduled_time DESC
        ''')
        posts = cursor.fetchall()

        for post in posts:
            posts_list.append({
                'id': post[0],
                'platforms': json.loads(post[1]),
                'caption': post[2][:100] + '...' if post[2] and len(post[2]) > 100 else post[2],
                'scheduled_time': post[3],
                'status': post[4],
                'created_at': post[5],
                'posted_at': post[6],
                'error_message': post[7]
            })
        app_logger.info(f"[💾] Retrieved {len(posts_list)} scheduled posts from DB for API.")
    except sqlite3.Error as e:
        app_logger.error(f"[❌ DB] Error fetching API scheduled post data: {e}")
        # Return an empty list and an error status if something goes wrong
        return jsonify({'error': 'Error retrieving scheduled posts from database.', 'posts': []}), 500
    finally:
        if conn:
            conn.close()
    return jsonify({'posts': posts_list})


@app.route('/delete-scheduled-post/<int:post_id>')
def delete_scheduled_post(post_id):
    """Deletes a scheduled post and removes it from the scheduler."""
    app_logger.info(f"[🗑️] Attempting to delete scheduled post {post_id}.")
    conn = None
    try:
        conn = sqlite3.connect('scheduled_posts.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM scheduled_posts WHERE id = ? AND status = "pending"', (post_id,))
        post = cursor.fetchone()
        if post:
            try:
                scheduler.remove_job(f'post_{post_id}')
                app_logger.info(f"[🗑️] Successfully removed scheduler job 'post_{post_id}'.")
            except Exception as e:
                app_logger.warning(f"[⚠️] Could not remove scheduler job 'post_{post_id}': {e}. It might have already run or been removed.")
        else:
            app_logger.warning(f"[⚠️] Post {post_id} not found or not in 'pending' status. Cannot remove job from scheduler if not pending.")

        cursor.execute('DELETE FROM scheduled_posts WHERE id = ?', (post_id,))
        conn.commit()
        app_logger.info(f"[✅🗑️] Post {post_id} deleted from database.")
        flash('📅 Scheduled post deleted successfully!')
    except sqlite3.Error as e:
        app_logger.error(f"[❌ DB] Error deleting scheduled post {post_id}: {e}")
        flash('Error deleting scheduled post. Please try again.')
    except Exception as e:
        app_logger.exception(f"[❌] An unexpected error occurred while deleting post {post_id}")
        flash('An unexpected error occurred. Please check logs.')
    finally:
        if conn:
            conn.close()
    return redirect(url_for('scheduled_posts'))

@app.route('/post', methods=['POST'])
def post():
    """Handles both immediate and scheduled post submissions."""
    app_logger.info("[📥] Received new post request.")

    media_files = request.files.getlist('media')
    caption_general = request.form.get('caption_general', '')
    caption_twitter = request.form.get('caption_twitter', '')
    platforms = request.form.getlist('platforms')
    action = request.form.get('action') # 'post_now' or 'schedule'
    scheduled_time_str = request.form.get('scheduled_time') # String from datetime-local input
    location = request.form.get('location', '') # Not currently used in posting functions
    collaborators = request.form.get('collaborators', '') # Not currently used in posting functions

    response_messages = [] # List to store messages for frontend

    if not media_files or media_files[0].filename == '':
        response_messages.append({'platform': 'General', 'status': 'error', 'message': 'Please select at least one media file!'})
        app_logger.warning("[⚠️] No media files selected for post.")
        return jsonify({'success': False, 'messages': response_messages})

    if not platforms:
        response_messages.append({'platform': 'General', 'status': 'error', 'message': 'Please select at least one platform!'})
        app_logger.warning("[⚠️] No platforms selected for post.")
        return jsonify({'success': False, 'messages': response_messages})

    local_paths = []
    cloudinary_urls = []
    for media in media_files:
        if media and allowed_file(media.filename):
            filename = secure_filename(media.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                media.save(filepath)
                app_logger.info(f"[📤] Saved local file: {filepath} (MIME: {media.mimetype})")
                local_paths.append(filepath)

                # Upload to Cloudinary
                resource_type = "video" if media.mimetype.startswith('video') else "image"
                # Cloudinary transformation for images to fit 1:1 aspect ratio, if applicable
                transformation = [{"aspect_ratio": "1:1", "crop": "fill"}] if resource_type == "image" else []

                app_logger.info(f"[☁️] Uploading {filename} to Cloudinary as {resource_type}...")
                result = cloudinary.uploader.upload(
                    filepath,
                    resource_type=resource_type,
                    transformation=transformation
                )
                cloud_url = result.get("secure_url")
                if cloud_url:
                    cloudinary_urls.append(cloud_url)
                    app_logger.info(f"[✅☁️] Uploaded to Cloudinary: {cloud_url}")
                else:
                    app_logger.error(f"[❌☁️] Cloudinary upload failed for {filename}. Result: {json.dumps(result)}")
                    response_messages.append({'platform': 'Cloudinary', 'status': 'error', 'message': f'Failed to upload {filename} to Cloudinary.'})
            except Exception as e:
                app_logger.exception(f"[❌] Error processing media file {filename}: {e}")
                response_messages.append({'platform': 'Media Upload', 'status': 'error', 'message': f'Error processing {filename}.'})
        else:
            app_logger.warning(f"[⚠️] Skipped invalid file: {media.filename}")
            response_messages.append({'platform': 'Media Upload', 'status': 'warning', 'message': f'File {media.filename} has an unsupported format and was skipped.'})

    if not local_paths: # If no valid files were processed
        response_messages.append({'platform': 'General', 'status': 'error', 'message': 'No valid media files were uploaded. Please try again with supported formats.'})
        return jsonify({'success': False, 'messages': response_messages})

    if action == 'schedule':
        if not scheduled_time_str:
            response_messages.append({'platform': 'Scheduling', 'status': 'error', 'message': 'Please select a date and time for scheduling!'})
            app_logger.warning("[⚠️] No scheduled time provided for a scheduled post.")
            return jsonify({'success': False, 'messages': response_messages})
        try:
            schedule_dt = datetime.fromisoformat(scheduled_time_str)
            # Ensure scheduled time is in the future
            if schedule_dt <= datetime.now():
                response_messages.append({'platform': 'Scheduling', 'status': 'error', 'message': 'Please select a future date and time for scheduling!'})
                app_logger.warning(f"[⚠️] Attempted to schedule post in the past: {schedule_dt}")
                return jsonify({'success': False, 'messages': response_messages})

            conn = None
            try:
                conn = sqlite3.connect('scheduled_posts.db')
                cursor = conn.cursor()
                app_logger.info(f"[💾] Saving scheduled post to DB for {schedule_dt}.")
                cursor.execute('''
                    INSERT INTO scheduled_posts
                    (media_files, cloudinary_urls, caption_general, caption_twitter, platforms, location, collaborators, scheduled_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    json.dumps(local_paths),
                    json.dumps(cloudinary_urls),
                    caption_general,
                    caption_twitter,
                    json.dumps(platforms),
                    location,
                    collaborators,
                    schedule_dt.isoformat() # Store as ISO format string
                ))
                post_id = cursor.lastrowid
                conn.commit()
                app_logger.info(f"[✅💾] Scheduled post saved to DB with ID: {post_id}")

                # Schedule the job with APScheduler
                scheduler.add_job(
                    func=execute_scheduled_post,
                    trigger=DateTrigger(run_date=schedule_dt),
                    args=[post_id],
                    id=f'post_{post_id}', # Unique ID for the job
                    name=f'Scheduled Post {post_id} - {platforms}',
                    misfire_grace_time=300 # Allow job to run up to 5 minutes late if system is busy
                )
                app_logger.info(f"[✅⏰] Job 'post_{post_id}' scheduled for {schedule_dt}.")
                response_messages.append({'platform': 'Scheduling', 'status': 'success', 'message': f'Post scheduled successfully for {schedule_dt.strftime("%B %d, %Y at %I:%M %p")}!'})
                return jsonify({'success': True, 'messages': response_messages})
            except sqlite3.Error as db_e:
                app_logger.error(f"[❌ DB] Error saving scheduled post to database: {db_e}")
                response_messages.append({'platform': 'Database', 'status': 'error', 'message': 'Error saving post to database. Please try again.'})
                return jsonify({'success': False, 'messages': response_messages})
            except Exception as e:
                app_logger.exception(f"[❌⏰] Error adding job to scheduler for post ID {post_id if 'post_id' in locals() else 'N/A'}: {e}")
                response_messages.append({'platform': 'Scheduler', 'status': 'error', 'message': 'Error scheduling post. Please try again.'})
                return jsonify({'success': False, 'messages': response_messages})
            finally:
                if conn:
                    conn.close()

        except ValueError:
            response_messages.append({'platform': 'Scheduling', 'status': 'error', 'message': 'Invalid date and time format for scheduling!'})
            app_logger.error(f"[❌] Invalid datetime format received: {scheduled_time_str}")
            return jsonify({'success': False, 'messages': response_messages})
        except Exception as e:
            app_logger.exception(f"[❌] An unexpected error occurred during scheduling: {e}")
            response_messages.append({'platform': 'Scheduling', 'status': 'error', 'message': 'An unexpected error occurred while scheduling. Please try again.'})
            return jsonify({'success': False, 'messages': response_messages})

    else: # action == 'post_now'
        app_logger.info("[⚡] Executing immediate post.")
        
        # --- Facebook Immediate Post ---
        if 'facebook' in platforms:
            app_logger.info("[⚡📘] Attempting immediate post to Facebook...")
            fb_result = post_to_facebook(local_paths, caption_general)
            if isinstance(fb_result, dict) and 'id' in fb_result:
                response_messages.append({'platform': 'Facebook', 'status': 'success', 'message': f'Post successful (ID: {fb_result.get("id")})'})
                app_logger.info(f"[✅⚡📘] Facebook immediate post successful: {json.dumps(fb_result)}")
            else:
                response_messages.append({'platform': 'Facebook', 'status': 'error', 'message': f'Post failed ({fb_result.get("error", "Unknown error or unexpected response")})'})
                app_logger.error(f"[❌⚡📘] Facebook immediate post failed: {json.dumps(fb_result)}")

        # --- Instagram Immediate Post ---
        if 'instagram' in platforms:
            app_logger.info("[⚡📷] Attempting immediate post to Instagram...")
            ig_results_list = post_to_instagram(cloudinary_urls, caption_general)
            
            instagram_success = False
            instagram_platform_messages = [] # Use a separate list for Instagram specific messages
            if isinstance(ig_results_list, list):
                for res in ig_results_list:
                    if isinstance(res, dict) and 'id' in res:
                        instagram_success = True
                        instagram_platform_messages.append(f"Media ID: {res.get('id')}")
                    elif isinstance(res, dict) and 'error' in res:
                        instagram_platform_messages.append(f"Failed ({res.get('error', 'Unknown error')})")
                    else:
                        instagram_platform_messages.append(f"Unexpected response: {res}")
            else:
                instagram_platform_messages.append(f"Unexpected Instagram response type: {type(ig_results_list)}")

            if instagram_success:
                response_messages.append({'platform': 'Instagram', 'status': 'success', 'message': f'Post successful ({"; ".join(instagram_platform_messages)})'})
                app_logger.info(f"[✅⚡📷] Instagram immediate post successful: {json.dumps(ig_results_list)}")
            else:
                response_messages.append({'platform': 'Instagram', 'status': 'error', 'message': f'Post failed ({"; ".join(instagram_platform_messages)})'})
                app_logger.error(f"[❌⚡📷] Instagram immediate post failed: {json.dumps(ig_results_list)}")

        # --- LinkedIn Immediate Post ---
        if 'linkedin' in platforms:
            app_logger.info("[⚡💼] Attempting immediate post to LinkedIn...")
            linkedin_result = post_to_linkedin(local_paths, caption_general, location, collaborators)
            if linkedin_result.get("success"):
                response_messages.append({'platform': 'LinkedIn', 'status': 'success', 'message': f'Post successful (Type: {linkedin_result.get("post_type")})'})
                app_logger.info(f"[✅⚡💼] LinkedIn immediate post successful: {json.dumps(linkedin_result)}")
            else:
                response_messages.append({'platform': 'LinkedIn', 'status': 'error', 'message': f'Post failed ({linkedin_result.get("error", "Unknown error")})'})
                app_logger.error(f"[❌⚡💼] LinkedIn immediate post failed: {json.dumps(linkedin_result)}")

        # --- X (Twitter) Immediate Post ---
        if 'x' in platforms:
            app_logger.info("[⚡🐦] Attempting immediate post to X (Twitter)...")
            x_result = post_to_x(text=caption_twitter, media_paths=local_paths)
            if isinstance(x_result, dict) and x_result.get('success'):
                response_messages.append({'platform': 'X (Twitter)', 'status': 'success', 'message': f'Post successful (Tweet ID: {x_result.get("tweet_id")})'})
                app_logger.info(f"[✅⚡🐦] X (Twitter) immediate post successful: {json.dumps(x_result)}")
            else:
                response_messages.append({'platform': 'X (Twitter)', 'status': 'error', 'message': f'Post failed ({x_result.get("error", "Unknown error or unexpected response")})'})
                app_logger.error(f"[❌⚡🐦] X (Twitter) immediate post failed: {json.dumps(x_result)}")

        return jsonify({'success': True, 'messages': response_messages}) # Always return success=True if the request was processed, individual platform success is in messages

@app.route('/api/scheduled-posts')
def api_scheduled_posts():
    """Provides a JSON API endpoint for scheduled post statistics."""
    app_logger.info("[📊] API request for scheduled post statistics.")
    conn = None
    stats = (0, 0, 0, 0) # Default if no data or error
    try:
        conn = sqlite3.connect('scheduled_posts.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                   SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM scheduled_posts
        ''')
        stats = cursor.fetchone()
        app_logger.info(f"[📊] Retrieved stats: Total={stats[0]}, Pending={stats[1]}, Completed={stats[2]}, Failed={stats[3]}")
    except sqlite3.Error as e:
        app_logger.error(f"[❌ DB] Error fetching API scheduled post stats: {e}")
    finally:
        if conn:
            conn.close()
    return jsonify({
        'total': stats[0],
        'pending': stats[1],
        'completed': stats[2],
        'failed': stats[3]
    })

if __name__ == '__main__':
    init_db() # Ensure DB is initialized when app starts
    app_logger.info("[🖥️] Running Flask app in debug mode.")
    app.run(debug=True) # Run in debug mode for development. Set debug=False for production.
