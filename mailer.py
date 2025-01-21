import datetime
import smtplib
import os
import threading
import uuid
import json
import sys
import signal

# Debug print
print("Python Version:", sys.version)
print("Current Python Path:", sys.path)

try:
    import queue
except ImportError:
    import Queue as queue

from threading import Thread
import logging

# Attempt to import email MIME modules with fallback
try:
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.application import MIMEApplication
except ImportError:
    # Fallback for older Python versions
    from email.MIMEMultipart import MIMEMultipart
    from email.MIMEText import MIMEText
    from email.MIMEApplication import MIMEApplication

# Debug print
print("Modules imported successfully!")

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Global flag for interruption
STOP_THREADS = False

def signal_handler(signum, frame):
    """
    Handle keyboard interrupt and other signals
    """
    global STOP_THREADS
    STOP_THREADS = True
    print("\n\nInterrupt received. Stopping email sending...")
    sys.exit(0)

class EmailSender(object):
    def __init__(self, username, password, max_workers=5):
        """
        Initialize email sender with SMTP credentials
        
        :param username: Email address to send from
        :param password: Email account password
        :param max_workers: Maximum number of concurrent email threads
        """
        self.username = username.strip()
        self.password = password.strip()
        self.max_workers = max_workers
        self.sent_count = 0
        self.failed_count = 0
        self.lock = threading.Lock()
        self.queue = queue.Queue()
        self.results = []

    def _get_smtp_connection(self):
        """
        Determine SMTP settings based on email provider
        
        :return: SMTP connection object
        """
        smtp_provider = self.username.split("@")[1].lower()
        smtp_settings = {
            'gmail.com': ('smtp.gmail.com', 587),
            'yahoo.com': ('smtp.mail.yahoo.com', 587),
            'hotmail.com': ('smtp.live.com', 587),
            'outlook.com': ('smtp.live.com', 587),
            'aol.com': ('smtp.aol.com', 587)
        }

        # Find matching SMTP settings
        for domain, (host, port) in smtp_settings.items():
            if domain in smtp_provider:
                try:
                    smtp = smtplib.SMTP(host, port)
                    smtp.starttls()
                    smtp.login(self.username, self.password)
                    return smtp
                except Exception as e:
                    logging.error('SMTP connection error: {}'.format(e))
                    raise

        # Raise error if no matching SMTP settings found
        raise ValueError('SMTP settings not found for {}'.format(self.username))

    def send_single_email(self, recipient, subject, body, campaign_id, attachments=None):
        """
        Send a single email
        
        :param recipient: Email address of recipient
        :param subject: Email subject
        :param body: Email body text
        :param campaign_id: Unique campaign identifier
        :param attachments: List of file paths to attach
        :return: Tuple of (success, error_message)
        """
        global STOP_THREADS
        if STOP_THREADS:
            return False, "Sending interrupted"

        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = '"{}" <{}>'.format(self.username.split('@')[0].capitalize(), self.username)
            msg['To'] = recipient
            msg['Subject'] = subject

            # Attach body
            msg.attach(MIMEText(body, 'html'))

            # Attach files
            if attachments:
                for filepath in attachments:
                    if os.path.exists(filepath):
                        with open(filepath, 'rb') as file:
                            part = MIMEApplication(file.read(), Name=os.path.basename(filepath))
                            part['Content-Disposition'] = 'attachment; filename="{}"'.format(os.path.basename(filepath))
                            msg.attach(part)
                    else:
                        logging.warning('Attachment file not found - {}'.format(filepath))

            # Send email
            smtp = None
            try:
                # Get SMTP connection
                smtp = self._get_smtp_connection()
                
                # Send email
                smtp.sendmail(self.username, recipient, msg.as_string())
                
                # Thread-safe increment of sent count
                with self.lock:
                    self.sent_count += 1
                    logging.info('Email sent successfully to {}'.format(recipient))
                
                return True, None
            
            finally:
                # Always close the SMTP connection
                if smtp:
                    try:
                        smtp.quit()
                    except Exception:
                        pass

        except Exception as e:
            # Thread-safe increment of failed count
            with self.lock:
                self.failed_count += 1
                logging.error('Error sending email to {}: {}'.format(recipient, e))
            
            return False, str(e)

    def worker(self):
        """
        Worker thread to process email queue
        """
        global STOP_THREADS
        while not STOP_THREADS:
            try:
                email_details = self.queue.get(timeout=1)
                if email_details is None:
                    break
                result = self.send_single_email(*email_details)
                self.results.append(result)
                self.queue.task_done()
            except queue.Empty:
                continue
            except Exception:
                break

    def send_emails_threaded(self, email_list):
        """
        Send multiple emails using thread pool
        
        :param email_list: List of tuples (recipient, subject, body, campaign_id, attachments)
        """
        global STOP_THREADS
        STOP_THREADS = False

        # Reset counters and results
        self.sent_count = 0
        self.failed_count = 0
        self.results = []

        # Create worker threads
        threads = []
        for _ in range(self.max_workers):
            t = Thread(target=self.worker)
            t.daemon = True  # Allow thread to be killed
            t.start()
            threads.append(t)

        # Add emails to queue
        for email_details in email_list:
            if STOP_THREADS:
                break
            self.queue.put(email_details)

        # Add stop signals
        for _ in range(self.max_workers):
            self.queue.put(None)

        # Wait for all tasks to complete or interruption
        while not STOP_THREADS and not self.queue.empty():
            try:
                self.queue.join()
                break
            except KeyboardInterrupt:
                STOP_THREADS = True
                break

        # Stop worker threads
        for t in threads:
            t.join(timeout=2)

        # Log summary
        logging.info('Email sending completed. Sent: {}, Failed: {}'.format(
            self.sent_count, self.failed_count))
        return self.results

def read_file_lines(filepath):
    """
    Read lines from a file, stripping whitespace and removing empty lines
    
    :param filepath: Path to the file
    :return: List of non-empty, stripped lines
    """
    try:
        with open(filepath, 'r') as file:
            return [line.strip() for line in file if line.strip()]
    except Exception as e:
        logging.error('Error reading file {}: {}'.format(filepath, e))
        return []

def main():
    try:
        # Set up signal handling only in main thread
        signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Termination signal

        # Paths for input files
        accounts_file = input("Enter path to accounts file (username,password format): ").strip()
        recipients_file = input("Enter path to recipients file (one email per line): ").strip()
        
        # Read accounts
        accounts = []
        for line in read_file_lines(accounts_file):
            try:
                username, password = line.split(',', 1)
                accounts.append((username.strip(), password.strip()))
            except ValueError:
                logging.warning('Skipping invalid account line: {}'.format(line))
        
        if not accounts:
            print("No valid accounts found. Exiting.")
            return
        
        # Read recipients
        recipients = read_file_lines(recipients_file)
        
        if not recipients:
            print("No recipients found. Exiting.")
            return
        
        # Generate campaign ID based on current date
        campaign_id = datetime.datetime.now().strftime("%d %b %Y")
        
        # Prompt for email details
        subject = input("Enter email subject: ").strip()
        
        # Multiline body input
        print("Enter email body (type 'END' on a new line to finish):")
        body_lines = []
        while True:
            line = input()
            if line == 'END':
                break
            body_lines.append(line)
        body = '\n'.join(body_lines)
        
        # Get attachments
        attachments = []
        print("Enter attachment file paths (leave blank when done):")
        while True:
            attachment = input("Attachment path: ")
            if not attachment:
                break
            attachments.append(attachment)
        
        # Prepare tracking pixel
        tracking_pixel = '<img src="http://45.141.122.177:8080/track?campaign_id={}" width="1" height="1" style="display:none;">'.format(campaign_id)
        
        # Add tracking pixel to body
        full_body = body + '\n\n' + tracking_pixel
        
        # Prepare email list
        email_list = [(recipient, subject, full_body, campaign_id, attachments or None) for recipient in recipients]
        
        # Select accounts to use
        print("\nAvailable Accounts:")
        for i, (username, _) in enumerate(accounts, 1):
            print("{0}. {1}".format(i, username))
        
        # Get account selection
        while True:
            try:
                account_selection = input("\nEnter account numbers to use (comma-separated, e.g. 1,2,3): ")
                selected_accounts = [accounts[int(num.strip())-1] for num in account_selection.split(',')]
                break
            except (ValueError, IndexError):
                print("Invalid selection. Please try again.")
        
        # Send emails from selected accounts
        for username, password in selected_accounts:
            print("\nSending emails from {}".format(username))
            sender = EmailSender(username, password)
            sender.send_emails_threaded(email_list)

    except KeyboardInterrupt:
        print("\nEmail sending interrupted by user.")
    except Exception as e:
        logging.error('Unexpected error: {}'.format(e))

if __name__ == "__main__":
    main()
