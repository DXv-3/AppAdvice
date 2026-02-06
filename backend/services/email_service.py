"""Email service for sending daily digests and notifications"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from jinja2 import Template

from core.config import settings


# HTML Email Templates
DAILY_DIGEST_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); padding: 30px; text-align: center; }
        .header h1 { color: white; margin: 0; font-size: 24px; }
        .header p { color: rgba(255,255,255,0.8); margin: 10px 0 0 0; }
        .content { padding: 30px; }
        .section { margin-bottom: 30px; }
        .section-title { font-size: 18px; font-weight: 600; color: #1f2937; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #e5e7eb; }
        .app-card { display: flex; align-items: center; padding: 15px; background: #f9fafb; border-radius: 8px; margin-bottom: 10px; }
        .app-icon { width: 60px; height: 60px; border-radius: 12px; margin-right: 15px; }
        .app-info { flex: 1; }
        .app-name { font-weight: 600; color: #1f2937; margin-bottom: 4px; }
        .app-developer { font-size: 14px; color: #6b7280; }
        .app-price { text-align: right; }
        .price-free { color: #10b981; font-weight: 700; font-size: 18px; }
        .price-drop { color: #f59e0b; font-weight: 700; font-size: 18px; }
        .price-original { text-decoration: line-through; color: #9ca3af; font-size: 14px; }
        .badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; margin-left: 8px; }
        .badge-free { background: #d1fae5; color: #065f46; }
        .badge-drop { background: #fef3c7; color: #92400e; }
        .footer { background: #f9fafb; padding: 20px; text-align: center; font-size: 14px; color: #6b7280; }
        .button { display: inline-block; padding: 12px 24px; background: #6366f1; color: white; text-decoration: none; border-radius: 6px; font-weight: 600; margin-top: 20px; }
        .stats { display: flex; justify-content: space-around; padding: 20px; background: #f3f4f6; border-radius: 8px; margin-bottom: 20px; }
        .stat { text-align: center; }
        .stat-value { font-size: 24px; font-weight: 700; color: #6366f1; }
        .stat-label { font-size: 12px; color: #6b7280; text-transform: uppercase; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📱 AppVault Daily Digest</h1>
            <p>Your daily dose of the best app deals - {{ date }}</p>
        </div>
        
        <div class="content">
            <div class="stats">
                <div class="stat">
                    <div class="stat-value">{{ stats.free_apps }}</div>
                    <div class="stat-label">Free Apps</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{{ stats.price_drops }}</div>
                    <div class="stat-label">Price Drops</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{{ stats.total_savings }}</div>
                    <div class="stat-label">Total Savings</div>
                </div>
            </div>
            
            {% if free_apps %}
            <div class="section">
                <div class="section-title">🎉 Apps Gone Free</div>
                {% for app in free_apps %}
                <div class="app-card">
                    <img src="{{ app.icon_url }}" alt="{{ app.name }}" class="app-icon">
                    <div class="app-info">
                        <div class="app-name">{{ app.name }} <span class="badge badge-free">FREE</span></div>
                        <div class="app-developer">{{ app.developer }}</div>
                    </div>
                    <div class="app-price">
                        <div class="price-free">FREE</div>
                        <div class="price-original">${{ app.original_price }}</div>
                    </div>
                </div>
                {% endfor %}
            </div>
            {% endif %}
            
            {% if price_drops %}
            <div class="section">
                <div class="section-title">📉 Biggest Price Drops</div>
                {% for app in price_drops %}
                <div class="app-card">
                    <img src="{{ app.icon_url }}" alt="{{ app.name }}" class="app-icon">
                    <div class="app-info">
                        <div class="app-name">{{ app.name }} <span class="badge badge-drop">-{{ app.discount }}%</span></div>
                        <div class="app-developer">{{ app.developer }}</div>
                    </div>
                    <div class="app-price">
                        <div class="price-drop">${{ app.price }}</div>
                        <div class="price-original">${{ app.original_price }}</div>
                    </div>
                </div>
                {% endfor %}
            </div>
            {% endif %}
            
            <div style="text-align: center;">
                <a href="https://appvault.com/deals" class="button">View All Deals</a>
            </div>
        </div>
        
        <div class="footer">
            <p>You're receiving this because you subscribed to AppVault daily digests.</p>
            <p><a href="{{ unsubscribe_url }}">Unsubscribe</a> | <a href="https://appvault.com/preferences">Preferences</a></p>
        </div>
    </div>
</body>
</html>
"""

SIMPLE_NOTIFICATION_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 500px; margin: 0 auto; background: white; border-radius: 12px; padding: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .icon { font-size: 48px; text-align: center; margin-bottom: 20px; }
        h1 { color: #1f2937; font-size: 20px; margin-bottom: 10px; }
        p { color: #6b7280; line-height: 1.6; }
        .app-box { background: #f9fafb; border-radius: 8px; padding: 15px; margin: 20px 0; display: flex; align-items: center; }
        .app-box img { width: 50px; height: 50px; border-radius: 10px; margin-right: 15px; }
        .button { display: inline-block; padding: 12px 24px; background: #6366f1; color: white; text-decoration: none; border-radius: 6px; font-weight: 600; }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">{{ icon }}</div>
        <h1>{{ title }}</h1>
        <p>{{ message }}</p>
        
        {% if app %}
        <div class="app-box">
            <img src="{{ app.icon_url }}" alt="{{ app.name }}">
            <div>
                <strong>{{ app.name }}</strong><br>
                <span style="color: #6b7280;">{{ app.developer }}</span>
            </div>
        </div>
        {% endif %}
        
        <a href="{{ action_url }}" class="button">{{ action_text }}</a>
    </div>
</body>
</html>
"""


class EmailService:
    """Service for sending email notifications and digests"""
    
    def __init__(self):
        self.daily_digest_template = Template(DAILY_DIGEST_TEMPLATE)
        self.notification_template = Template(SIMPLE_NOTIFICATION_TEMPLATE)
    
    async def send_daily_digest(
        self,
        to_email: str,
        free_apps: List[Dict[str, Any]],
        price_drops: List[Dict[str, Any]],
        stats: Dict[str, Any]
    ) -> bool:
        """
        Send daily digest email with app deals.
        
        In production, integrate with:
        - Resend (recommended for transactional emails)
        - SendGrid
        - AWS SES
        - Mailgun
        """
        
        html_content = self.daily_digest_template.render(
            date=datetime.now().strftime("%B %d, %Y"),
            free_apps=free_apps,
            price_drops=price_drops,
            stats=stats,
            unsubscribe_url=f"https://appvault.com/unsubscribe?email={to_email}"
        )
        
        # TODO: Integrate with actual email service
        # For now, just log the email
        print(f"\n{'='*60}")
        print(f"📧 DAILY DIGEST EMAIL TO: {to_email}")
        print(f"{'='*60}")
        print(f"Free apps: {len(free_apps)}")
        print(f"Price drops: {len(price_drops)}")
        print(f"Stats: {stats}")
        print(f"{'='*60}\n")
        
        # Example integration with Resend (when ready):
        # import resend
        # resend.api_key = settings.RESEND_API_KEY
        # response = resend.Emails.send({
        #     "from": "AppVault <alerts@appvault.com>",
        #     "to": to_email,
        #     "subject": f"📱 {len(free_apps)} Free Apps + {len(price_drops)} Price Drops Today!",
        #     "html": html_content
        # })
        
        return True
    
    async def send_price_alert(
        self,
        to_email: str,
        app: Dict[str, Any],
        old_price: float,
        new_price: float,
        alert_type: str = "price_drop"
    ) -> bool:
        """Send immediate price alert notification"""
        
        if alert_type == "goes_free":
            title = f"🎉 {app['name']} is now FREE!"
            message = f"Great news! {app['name']} just went from ${old_price} to FREE. Grab it now!"
            icon = "🎉"
            action_text = "Get It Free"
        elif alert_type == "target_price":
            title = f"🎯 Target price reached for {app['name']}"
            message = f"{app['name']} has reached your target price of ${new_price}!"
            icon = "🎯"
            action_text = "View App"
        else:
            discount = round(((old_price - new_price) / old_price) * 100)
            title = f"📉 {app['name']} dropped {discount}%!"
            message = f"Price dropped from ${old_price} to ${new_price}"
            icon = "📉"
            action_text = "View Deal"
        
        html_content = self.notification_template.render(
            icon=icon,
            title=title,
            message=message,
            app=app,
            action_url=app.get('app_store_url', f"https://appvault.com/app/{app['id']}"),
            action_text=action_text
        )
        
        print(f"\n{'='*60}")
        print(f"🔔 PRICE ALERT EMAIL TO: {to_email}")
        print(f"{'='*60}")
        print(f"Subject: {title}")
        print(f"App: {app['name']}")
        print(f"Price: ${old_price} → ${new_price}")
        print(f"{'='*60}\n")
        
        return True
    
    async def send_welcome_email(self, to_email: str, name: str) -> bool:
        """Send welcome email to new users"""
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 500px; margin: 0 auto; background: white; border-radius: 12px; padding: 30px; text-align: center; }}
                h1 {{ color: #6366f1; }}
                .button {{ display: inline-block; padding: 12px 24px; background: #6366f1; color: white; text-decoration: none; border-radius: 6px; font-weight: 600; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎉 Welcome to AppVault, {name}!</h1>
                <p>You're now part of a community that never misses a great app deal.</p>
                <p>Here's what you can do:</p>
                <ul style="text-align: left; color: #6b7280;">
                    <li>🔍 Discover apps gone free</li>
                    <li>📉 Track price drops</li>
                    <li>⭐ Save favorites</li>
                    <li>🔔 Set price alerts</li>
                </ul>
                <a href="https://appvault.com/deals" class="button">Start Exploring</a>
            </div>
        </body>
        </html>
        """
        
        print(f"\n{'='*60}")
        print(f"👋 WELCOME EMAIL TO: {to_email}")
        print(f"{'='*60}\n")
        
        return True


# Global instance
email_service = EmailService()
