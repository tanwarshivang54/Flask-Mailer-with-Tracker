import streamlit as st
import sqlalchemy as sa
import pandas as pd
from sqlalchemy.orm import sessionmaker
from pixel_tracker_py2 import Base, PixelTrack
from datetime import datetime, timedelta

class EmailTrackingDashboard:
    def __init__(self, db_path='tracking.db'):
        self.engine = sa.create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def get_comprehensive_tracking_summary(self):
        session = self.Session()
        try:
            # Comprehensive campaign tracking query
            campaign_stats = session.query(
                PixelTrack.campaign_id,
                PixelTrack.sender_email,
                sa.func.count(sa.distinct(PixelTrack.recipient)).label('unique_recipients'),
                sa.func.count(PixelTrack.id).label('total_opens'),
                sa.func.min(PixelTrack.timestamp).label('first_open'),
                sa.func.max(PixelTrack.timestamp).label('last_open')
            ).group_by(
                PixelTrack.campaign_id, 
                PixelTrack.sender_email
            ).all()
            
            # Prepare DataFrame
            campaign_data = []
            for stat in campaign_stats:
                campaign_data.append({
                    'Campaign ID': stat[0] or 'Unknown',
                    'Sender Email': stat[1] or 'Unknown',
                    'Unique Recipients': stat[2],
                    'Total Opens': stat[3],
                    'Open Rate (%)': round((stat[2] / max(stat[3], 1)) * 100, 2) if stat[3] > 0 else 0,
                    'First Open': stat[4],
                    'Last Open': stat[5],
                    'Campaign Duration (Hours)': round((stat[5] - stat[4]).total_seconds() / 3600, 2) if stat[5] and stat[4] else 0
                })
            
            # Detailed tracking data
            detailed_tracking = session.query(
                PixelTrack.campaign_id,
                PixelTrack.recipient,
                PixelTrack.timestamp,
                PixelTrack.ip_address
            ).order_by(PixelTrack.timestamp.desc()).limit(100).all()
            
            detailed_data = [
                {
                    'Campaign ID': stat[0] or 'Unknown',
                    'Recipient': stat[1] or 'Unknown',
                    'Timestamp': stat[2],
                    'IP Address': stat[3]
                } for stat in detailed_tracking
            ]
            
            # Overall campaign metrics
            total_campaigns = len(campaign_data)
            total_unique_recipients = sum(data['Unique Recipients'] for data in campaign_data)
            total_opens = sum(data['Total Opens'] for data in campaign_data)
            avg_open_rate = sum(data['Open Rate (%)'] for data in campaign_data) / max(total_campaigns, 1)
            
            return (
                pd.DataFrame(campaign_data), 
                pd.DataFrame(detailed_data),
                {
                    'Total Campaigns': total_campaigns,
                    'Total Unique Recipients': total_unique_recipients,
                    'Total Opens': total_opens,
                    'Average Open Rate (%)': round(avg_open_rate, 2)
                }
            )
        finally:
            session.close()

    def render_dashboard(self):
        st.set_page_config(layout="wide", page_title="Email Tracking Dashboard")
        
        st.title('📧 Comprehensive Email Tracking Dashboard')
        
        # Get tracking data
        campaign_df, detailed_df, overall_metrics = self.get_comprehensive_tracking_summary()
        
        # Overall Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Campaigns", overall_metrics['Total Campaigns'])
        col2.metric("Total Unique Recipients", overall_metrics['Total Unique Recipients'])
        col3.metric("Total Opens", overall_metrics['Total Opens'])
        col4.metric("Avg Open Rate", f"{overall_metrics['Average Open Rate (%)']}%")
        
        # Campaign Performance
        st.header('Campaign Performance')
        st.dataframe(campaign_df)
        
        # Visualizations
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            st.subheader('Unique Recipients by Campaign')
            st.bar_chart(campaign_df.set_index('Campaign ID')['Unique Recipients'])
        
        with col_chart2:
            st.subheader('Open Rates by Campaign')
            st.bar_chart(campaign_df.set_index('Campaign ID')['Open Rate (%)'])
        
        # Detailed Tracking
        st.header('Detailed Tracking Data')
        st.dataframe(detailed_df)

def main():
    dashboard = EmailTrackingDashboard()
    dashboard.render_dashboard()

if __name__ == "__main__":
    main()
