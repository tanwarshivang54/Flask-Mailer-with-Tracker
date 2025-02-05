import sqlite3
import hashlib
from functools import wraps
import os
from typing import Optional, Tuple

def get_db_connection():
    """Get database connection"""
    db_path = os.path.join(os.path.dirname(__file__), 'mailer.db')
    return sqlite3.connect(db_path)

def hash_password(password: str) -> str:
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(username: str, password: str) -> Optional[Tuple[int, bool]]:
    """
    Authenticate a user and return (user_id, is_admin) if successful, None if not
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            'SELECT id, is_admin FROM users WHERE username = ? AND password = ?',
            (username, hash_password(password))
        )
        result = cursor.fetchone()
        return result if result else None
    finally:
        conn.close()

def create_user(admin_username: str, admin_password: str, new_username: str, new_password: str) -> bool:
    """
    Create a new user (admin only)
    Returns True if successful, False otherwise
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verify admin credentials
        cursor.execute(
            'SELECT id FROM users WHERE username = ? AND password = ? AND is_admin = 1',
            (admin_username, hash_password(admin_password))
        )
        if not cursor.fetchone():
            return False
        
        # Create new user
        cursor.execute(
            'INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)',
            (new_username, hash_password(new_password), False)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Username already exists
        return False
    finally:
        conn.close()

def delete_user(admin_username: str, admin_password: str, username_to_delete: str) -> bool:
    """
    Delete a user (admin only)
    Returns True if successful, False otherwise
    """
    if username_to_delete == 'admin':
        return False  # Prevent deletion of admin account
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verify admin credentials
        cursor.execute(
            'SELECT id FROM users WHERE username = ? AND password = ? AND is_admin = 1',
            (admin_username, hash_password(admin_password))
        )
        if not cursor.fetchone():
            return False
        
        # Delete user
        cursor.execute('DELETE FROM users WHERE username = ? AND is_admin = 0', 
                      (username_to_delete,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()

def get_user_stats(user_id: int) -> dict:
    """Get statistics for a specific user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get total emails sent
        cursor.execute('SELECT COUNT(*) FROM email_logs WHERE user_id = ?', (user_id,))
        total_emails = cursor.fetchone()[0]
        
        # Get total email opens
        cursor.execute('''
            SELECT COUNT(DISTINCT t.id)
            FROM tracker_logs t
            JOIN email_logs e ON t.email_id = e.id
            WHERE e.user_id = ? AND t.event_type = 'open'
        ''', (user_id,))
        total_opens = cursor.fetchone()[0]
        
        return {
            'total_emails': total_emails,
            'total_opens': total_opens,
            'open_rate': (total_opens / total_emails * 100) if total_emails > 0 else 0
        }
    finally:
        conn.close()

def get_admin_stats() -> dict:
    """Get system-wide statistics (admin only)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get total emails sent
        cursor.execute('SELECT COUNT(*) FROM email_logs')
        total_emails = cursor.fetchone()[0]
        
        # Get total email opens
        cursor.execute('''
            SELECT COUNT(DISTINCT t.id)
            FROM tracker_logs t
            JOIN email_logs e ON t.email_id = e.id
            WHERE t.event_type = 'open'
        ''')
        total_opens = cursor.fetchone()[0]
        
        # Get user statistics
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 0')
        total_users = cursor.fetchone()[0]
        
        return {
            'total_emails': total_emails,
            'total_opens': total_opens,
            'open_rate': (total_opens / total_emails * 100) if total_emails > 0 else 0,
            'total_users': total_users
        }
    finally:
        conn.close()