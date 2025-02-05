# Flask Mailer System Architecture

## System Overview

This document outlines the architecture and planned changes for the Flask Mailer system, focusing on user management, statistics tracking, and UI improvements.

## Architecture Components

### 1. Database Schema

```sql
-- Users Table
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE
);

-- Email Logs Table
CREATE TABLE email_logs (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Tracker Data Table
CREATE TABLE tracker_logs (
    id INTEGER PRIMARY KEY,
    email_id INTEGER,
    event_type TEXT NOT NULL,  -- 'open' or 'click'
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (email_id) REFERENCES email_logs(id)
);
```

### 2. Backend Components

#### User Management Module
- Location: `Mailer2/app.py`
- Functions:
  - `create_user(username, password)` - Admin only
  - `delete_user(username)` - Admin only
  - `user_login(username, password)`
  - `is_admin(user_id)`

#### Statistics Module
- Universal Stats (Admin)
  - Total emails sent
  - Overall open/click rates
  - User activity summary
  
- Individual Stats (Per User)
  - Personal email count
  - Individual open/click rates
  - Recent activity log

#### Authentication System
- Session-based authentication
- Admin privileges verification
- User session management

### 3. Frontend Structure

#### Theme Configuration
- Primary Color: #E6A912 (Yellow)
- Supporting Colors:
  - Background: Light neutral
  - Text: Dark gray
  - Accents: Complementary to primary

#### UI Components
1. **Admin Dashboard**
   - User management interface
   - Universal statistics display
   - System-wide tracker data
   - User activity overview

2. **User Dashboard**
   - Personal statistics
   - Email history
   - Individual tracker data

3. **Mailer Interface**
   - Enhanced with Tailwind CSS
   - Responsive design
   - Animated components

### 4. API Endpoints

```
POST /api/auth/login
POST /api/auth/logout

# Admin Only
POST /api/admin/users/create
DELETE /api/admin/users/{username}
GET /api/admin/stats/universal
GET /api/admin/tracker/all

# User Endpoints
GET /api/user/stats
GET /api/user/emails
GET /api/user/tracker
POST /api/user/send-email
```

## Implementation Notes

### Database Setup
1. Initialize tables with admin user
2. Set up foreign key relationships
3. Create indexes for frequent queries

### Security Measures
1. Password hashing for user credentials
2. Session management
3. Admin route protection

### UI Implementation
1. Integrate Tailwind CSS
2. Apply yellow theme consistently
3. Add smooth transitions and effects
4. Ensure responsive layouts

## Feature Implementation Order

1. Database Schema Setup
2. User Authentication System
3. Admin Features
4. User-specific Features
5. Statistics Collection
6. UI Enhancements

## Requirements

- Flask
- SQLite/PostgreSQL
- Tailwind CSS
- Python 3.x
- Additional requirements in requirements.txt