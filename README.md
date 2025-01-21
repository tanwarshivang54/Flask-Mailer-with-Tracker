# Email Tracking System

## Overview
A comprehensive email tracking application built with Flask, SQLAlchemy, and Python 2.7, designed to monitor and analyze email campaign performance.

## Features
- 📧 Send personalized emails
- 📊 Real-time campaign tracking
- 🔍 Detailed campaign metrics dashboard
- 📈 Track email opens, unique recipients, and engagement

## Prerequisites
- Python 2.7.5+
- pip (Python package manager)

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/email-tracker.git
cd email-tracker
```

### 2. Create Virtual Environment (Optional but Recommended)
```bash
virtualenv -p python2.7 venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

## Configuration
1. Set tracking domain in `flask_app.py`:
```python
TRACKING_DOMAIN = os.environ.get('TRACKING_DOMAIN', 'http://your-domain.com')
```

2. Configure email settings in `mailer.py`

## Running the Application
```bash
python flask_app.py
```
- Access the application at `http://localhost:5000`

## Database
- Uses SQLite (`tracking.db`)
- Automatically creates database on first run
- Stores tracking information for email campaigns

## Tracking Workflow
1. Send emails through the web interface
2. Each email includes a unique tracking pixel
3. Opens are recorded with:
   - Timestamp
   - IP Address
   - Device Information
   - Campaign ID

## Dashboard Metrics
- Total Campaigns
- Total Unique Recipients
- Total Opens
- Average Open Rate
- Detailed Campaign Tracking

## Troubleshooting
- Ensure all dependencies are installed
- Check `requirements.txt` for specific package versions
- Verify Python 2.7 compatibility

## Security Considerations
- Use a strong, unique `secret_key` in Flask
- Do not expose tracking database
- Implement additional authentication for production

## Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request


## Contact
neehan@gmail.com

---

### Developed with ❤️ for Email Tracking Analytics
