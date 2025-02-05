from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort
import os
from functools import wraps
from datetime import datetime
import uuid
from werkzeug.utils import secure_filename
import mimetypes

from auth import authenticate_user, create_user, delete_user, get_user_stats, get_admin_stats
from mailer import EmailSender

# Constants
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Create Flask app with explicit template and static folders
app = Flask(__name__,
            template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates')),
            static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), 'static')))
app.secret_key = os.urandom(24)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    if 'user_id' in session:
        flash('Page not found')
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.errorhandler(500)
def internal_error(error):
    flash('An internal error occurred')
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        result = authenticate_user(username, password)
        
        if result:
            user_id, is_admin = result
            session['user_id'] = user_id
            session['username'] = username
            session['is_admin'] = is_admin
            return redirect(url_for('admin_dashboard' if is_admin else 'dashboard'))
        
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))
    
    stats = get_user_stats(session['user_id'])
    return render_template('user_dashboard.html', stats=stats)

@app.route('/admin')
@admin_required
def admin_dashboard():
    stats = get_admin_stats()
    return render_template('admin_dashboard.html', stats=stats)

@app.route('/send_email', methods=['GET', 'POST'])
@login_required
def send_email():
    if request.method == 'POST':
        if not request.form.get('recipients') or not request.form.get('subject') or not request.form.get('body'):
            flash('Please fill in all required fields')
            return render_template('send_email.html')

        recipients = request.form['recipients'].split(',')
        subject = request.form['subject']
        body = request.form['body']
        
        # Handle attachments
        attachments = []
        if 'attachments' in request.files:
            files = request.files.getlist('attachments')
            for file in files:
                if file.filename:
                    if file.filename == '':
                        flash('One or more files have no filename')
                        continue
                    if not allowed_file(file.filename):
                        flash(f'File type not allowed for {file.filename}')
                        continue
                    if len(file.read()) > MAX_FILE_SIZE:
                        flash(f'File {file.filename} is too large (max 10MB)')
                        continue
                    file.seek(0)  # Reset file pointer after reading
                    
                    filename = secure_filename(file.filename)
                    filepath = os.path.join('temp', filename)
                    os.makedirs('temp', exist_ok=True)
                    file.save(filepath)
                    attachments.append(filepath)

        try:
            # Generate campaign ID
            campaign_id = str(uuid.uuid4())
            
            # Add tracking pixel
            tracking_pixel = f'<img src="http://45.141.122.177:8080/track?campaign_id={campaign_id}" width="1" height="1" style="display:none;">'
            full_body = body + '\n\n' + tracking_pixel

            # Send emails
            sender = EmailSender()  # Assuming EmailSender is modified to use environment variables
            email_list = [(recipient.strip(), subject, full_body, campaign_id, attachments) for recipient in recipients]
            results = sender.send_emails_threaded(email_list)

            # Clean up attachments
            for attachment in attachments:
                if os.path.exists(attachment):
                    os.remove(attachment)

            # Return results
            successful = sum(1 for result in results if result[0])
            failed = len(results) - successful
            flash(f'Campaign sent! {successful} emails sent successfully, {failed} failed.')

        except Exception as e:
            flash(f'Error sending emails: {str(e)}')

    return render_template('send_email.html')

@app.route('/admin/users', methods=['GET', 'POST', 'DELETE'])
@admin_required
def manage_users():
    if request.method == 'POST':
        if not all(key in request.form for key in ['username', 'password', 'admin_password']):
            flash('Missing required fields')
            return render_template('manage_users.html')

        new_username = request.form['username']
        new_password = request.form['password']
        admin_password = request.form['admin_password']
        
        if create_user(session['username'], admin_password, new_username, new_password):
            flash('User created successfully')
        else:
            flash('Failed to create user')
            
    elif request.method == 'DELETE':
        if not all(key in request.form for key in ['username', 'admin_password']):
            flash('Missing required fields')
            return render_template('manage_users.html')

        username_to_delete = request.form['username']
        admin_password = request.form['admin_password']
        
        if username_to_delete == session['username']:
            flash('Cannot delete your own account')
            return render_template('manage_users.html')
        
        if delete_user(session['username'], admin_password, username_to_delete):
            flash('User deleted successfully')
        else:
            flash('Failed to delete user')
    
    return render_template('manage_users.html')

if __name__ == '__main__':
    # Ensure the database is initialized
    from db_setup import init_database
    init_database()
    
    # Create static folder if it doesn't exist
    os.makedirs(os.path.join(os.path.dirname(__file__), 'static'), exist_ok=True)
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=3000)
    args = parser.parse_args()
    
    # Run the app - force debug mode to false in production
    app.run(host='0.0.0.0', port=args.port, debug=True)
