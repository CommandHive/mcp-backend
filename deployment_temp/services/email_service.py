import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from datetime import datetime


class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.smtp_from = os.getenv("SMTP_FROM")
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        
    def send_magic_link(self, email: str, token: str, display_name: Optional[str] = None) -> bool:
        """Send magic link email to user."""
        try:
            # Create magic link URL
            magic_link = f"{self.frontend_url}/auth/verify?token={token}"
            
            # Create email content
            subject = "Sign in to CommandHive"
            
            # HTML email template
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Sign in to CommandHive</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #4f46e5; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                    .content {{ background-color: #f9fafb; padding: 30px; border-radius: 0 0 8px 8px; }}
                    .button {{ display: inline-block; padding: 12px 24px; background-color: #4f46e5; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 20px 0; }}
                    .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb; font-size: 14px; color: #6b7280; }}
                    .warning {{ background-color: #fef3c7; border: 1px solid #f59e0b; padding: 15px; border-radius: 6px; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Sign in to CommandHive</h1>
                    </div>
                    <div class="content">
                        <h2>Hello{" " + display_name if display_name else ""}!</h2>
                        <p>You requested to sign in to CommandHive. Click the button below to securely sign in:</p>
                        
                        <div style="text-align: center;">
                            <a href="{magic_link}" class="button">Sign In to CommandHive</a>
                        </div>
                        
                        <p>Or copy and paste this link into your browser:</p>
                        <p style="word-break: break-all; background-color: #f3f4f6; padding: 10px; border-radius: 4px; font-family: monospace;">
                            {magic_link}
                        </p>
                        
                        <div class="warning">
                            <p><strong>⚠️ Security Notice:</strong></p>
                            <ul>
                                <li>This link will expire in 15 minutes</li>
                                <li>It can only be used once</li>
                                <li>If you didn't request this, please ignore this email</li>
                            </ul>
                        </div>
                        
                        <div class="footer">
                            <p>This email was sent to {email} for CommandHive authentication.</p>
                            <p>If you have any questions, please contact our support team.</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Text fallback
            text_body = f"""
            Sign in to CommandHive
            
            Hello{" " + display_name if display_name else ""}!
            
            You requested to sign in to CommandHive. Click the link below to securely sign in:
            
            {magic_link}
            
            This link will expire in 15 minutes and can only be used once.
            
            If you didn't request this, please ignore this email.
            
            This email was sent to {email} for CommandHive authentication.
            """
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_from
            msg['To'] = email
            
            # Attach parts
            text_part = MIMEText(text_body, 'plain')
            html_part = MIMEText(html_body, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            print(f"📧 [EmailService] Sending magic link email to {email}")
            print(f"📧 [EmailService] SMTP Config: {self.smtp_host}:{self.smtp_port}")
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            print(f"✅ [EmailService] Magic link email sent successfully to {email}")
            return True
            
        except Exception as e:
            print(f"❌ [EmailService] Failed to send magic link email: {e}")
            import traceback
            print(f"❌ [EmailService] Traceback: {traceback.format_exc()}")
            return False
    
    def send_welcome_email(self, email: str, display_name: Optional[str] = None) -> bool:
        """Send welcome email to new users."""
        try:
            subject = "Welcome to CommandHive!"
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Welcome to CommandHive</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #4f46e5; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                    .content {{ background-color: #f9fafb; padding: 30px; border-radius: 0 0 8px 8px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Welcome to CommandHive!</h1>
                    </div>
                    <div class="content">
                        <h2>Hello{" " + display_name if display_name else ""}!</h2>
                        <p>Welcome to CommandHive - your platform for creating and managing MCP servers!</p>
                        <p>You can now start creating and deploying your own MCP servers, and explore servers created by the community.</p>
                        <p>Get started by visiting your dashboard and creating your first server.</p>
                        <p>Happy coding!</p>
                        <p>- The CommandHive Team</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_body = f"""
            Welcome to CommandHive!
            
            Hello{" " + display_name if display_name else ""}!
            
            Welcome to CommandHive - your platform for creating and managing MCP servers!
            
            You can now start creating and deploying your own MCP servers, and explore servers created by the community.
            
            Get started by visiting your dashboard and creating your first server.
            
            Happy coding!
            - The CommandHive Team
            """
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_from
            msg['To'] = email
            
            text_part = MIMEText(text_body, 'plain')
            html_part = MIMEText(html_body, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            print(f"✅ [EmailService] Welcome email sent to {email}")
            return True
            
        except Exception as e:
            print(f"❌ [EmailService] Failed to send welcome email: {e}")
            return False


email_service = EmailService()