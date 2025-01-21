import streamlit as st
import datetime
import uuid
import pandas as pd
import sqlite3
import os
import sys

# Ensure the current directory is in Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import custom modules
from mailer import EmailSender, read_file_lines

# Verify imports
print("Current Python Path:", sys.path)
print("Mailer module path:", os.path.abspath(os.path.join(current_dir, 'mailer.py')))

def load_tracking_data():
    """
    Load tracking data from SQLite database
    """
    try:
        conn = sqlite3.connect('tracking.db')
        
        # Check if table exists
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pixel_tracks'")
        if not cursor.fetchone():
            st.warning("No tracking data table found.")
            return pd.DataFrame()

        # Try to read data with error handling
        try:
            df = pd.read_sql_query("SELECT * FROM pixel_tracks", conn)
            conn.close()
            return df
        except Exception as e:
            st.error(f"Error reading tracking data: {e}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return pd.DataFrame()

def send_emails_page():
    """
    Streamlit page for sending emails
    """
    st.title("📧 Email Campaign Sender")

    # Account file selection
    accounts_file = st.file_uploader("Upload Accounts File", type=['txt'])
    recipients_file = st.file_uploader("Upload Recipients File", type=['txt'])

    # Email details
    subject = st.text_input("Email Subject")
    body = st.text_area("Email Body")

    # Attachments
    attachments = st.file_uploader("Upload Attachments", accept_multiple_files=True)

    # Account selection
    if accounts_file:
        # Read accounts - handle both bytes and string
        accounts_content = accounts_file.getvalue()
        if isinstance(accounts_content, bytes):
            accounts_content = accounts_content.decode('utf-8')
        
        accounts_content = accounts_content.splitlines()
        accounts = [line.strip().split(',') for line in accounts_content if line.strip()]
        selected_account = st.selectbox("Select Sending Account", 
            [account[0] for account in accounts])

    # Send button
    if st.button("Send Emails"):
        if not all([accounts_file, recipients_file, subject, body]):
            st.error("Please fill in all required fields")
            return

        # Save temporary files
        with open('temp_accounts.txt', 'w') as f:
            f.write('\n'.join(','.join(account) for account in accounts))
        
        # Handle recipients file - similar conversion
        recipients_bytes = recipients_file.getvalue()
        if isinstance(recipients_bytes, bytes):
            recipients = recipients_bytes.decode('utf-8').splitlines()
        else:
            recipients = recipients_bytes.splitlines()
        
        with open('temp_recipients.txt', 'w') as f:
            f.write('\n'.join(recipients))

        # Prepare attachments
        attachment_paths = []
        if attachments:
            for uploaded_file in attachments:
                with open(uploaded_file.name, 'wb') as f:
                    f.write(uploaded_file.getvalue())
                attachment_paths.append(uploaded_file.name)

        # Find account credentials
        account_creds = next((account for account in accounts if account[0] == selected_account), None)
        
        if account_creds:
            try:
                # Generate campaign ID
                campaign_id = datetime.datetime.now().strftime("%d %b %Y")
                
                # Prepare tracking pixel
                tracking_pixel = '<img src="http://45.141.122.177:8080/track?campaign_id={}" width="1" height="1" style="display:none;">'.format(campaign_id)
                full_body = body + '\n\n' + tracking_pixel

                # Send emails
                sender = EmailSender(account_creds[0], account_creds[1])
                email_list = [(recipient, subject, full_body, campaign_id, attachment_paths or None) for recipient in recipients]
                results = sender.send_emails_threaded(email_list)

                # Clean up temporary files
                os.remove('temp_accounts.txt')
                os.remove('temp_recipients.txt')
                for path in attachment_paths:
                    os.remove(path)

                # Display results
                successful = sum(1 for result in results if result[0])
                failed = len(results) - successful
                st.success("Campaign sent! {} emails sent successfully, {} failed.".format(successful, failed))

            except Exception as e:
                st.error('Error sending emails: {}'.format(e))
        else:
            st.error("Selected account not found")

def dashboard_page():
    """
    Streamlit page for email tracking dashboard
    """
    st.title("📊 Email Campaign Dashboard")

    # Load tracking data
    tracking_df = load_tracking_data()

    if not tracking_df.empty:
        # Display raw data for debugging
        st.subheader("Raw Tracking Data")
        st.dataframe(tracking_df)

        # Check available columns
        st.subheader("Available Columns")
        st.write(tracking_df.columns.tolist())

        # Campaign overview with flexible column handling
        st.subheader("Campaign Performance")
        try:
            # Use columns that definitely exist
            campaign_columns = ['campaign_id']
            
            # Add optional columns if they exist
            optional_columns = ['recipient', 'timestamp', 'ip_address']
            for col in optional_columns:
                if col in tracking_df.columns:
                    campaign_columns.append(col)

            # Perform aggregation with available columns
            campaign_metrics = tracking_df.groupby('campaign_id').agg({
                col: 'count' if col == 'recipient' else 
                     'min' if col == 'timestamp' else 
                     'nunique' if col == 'ip_address' else 'first'
                for col in campaign_columns
            })

            # Rename columns for clarity
            column_names = {
                'recipient': 'Total Emails',
                'timestamp': 'First Tracked',
                'ip_address': 'Unique IPs'
            }
            campaign_metrics.rename(columns=column_names, inplace=True)
            
            st.dataframe(campaign_metrics)

        except Exception as e:
            st.error(f"Error processing campaign metrics: {e}")

    else:
        st.warning("No tracking data available. Ensure tracking database is set up correctly.")

def main():
    """
    Main Streamlit app
    """
    st.sidebar.title("Email Tracker")
    page = st.sidebar.radio("Navigate", ["Send Emails", "Dashboard"])

    if page == "Send Emails":
        send_emails_page()
    else:
        dashboard_page()

if __name__ == "__main__":
    main()
