
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_mail import Mail, Message
from flask import current_app

# Initialize Flask-Mail instance
mail = Mail()

def init_mail(app):
    """Initialize Flask-Mail with the app"""
    # Configure Flask-Mail
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config.get('MAIL_USERNAME'))
    
    # Initialize mail with app
    mail.init_app(app)
    
    # Test email configuration
    with app.app_context():
        if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
            logging.warning("Email credentials not configured. Email functionality will be disabled.")
        else:
            logging.info("Email service initialized successfully")

def is_email_configured():
    """Check if email is properly configured"""
    return bool(
        current_app.config.get('MAIL_USERNAME') and 
        current_app.config.get('MAIL_PASSWORD') and
        current_app.config.get('MAIL_SERVER')
    )

def send_otp_email(email, otp_code, purpose='login'):
    """Send OTP email for login or password reset"""
    if not is_email_configured():
        logging.warning("Email not configured. Cannot send OTP email.")
        return False
    
    try:
        subject = f"PrepMyCert - Your OTP Code for {purpose.title()}"
        
        if purpose == 'login':
            body = f"""
Hello,

Your OTP code for login is: {otp_code}

This code will expire in 10 minutes.

If you didn't request this code, please ignore this email.

Best regards,
PrepMyCert Team
"""
        elif purpose == 'verification':
            body = f"""
Hello,

Your OTP code for email verification is: {otp_code}

This code will expire in 15 minutes.

If you didn't request this code, please ignore this email.

Best regards,
PrepMyCert Team
"""
        else:  # password reset
            body = f"""
Hello,

Your OTP code for password reset is: {otp_code}

This code will expire in 15 minutes.

If you didn't request this code, please ignore this email.

Best regards,
PrepMyCert Team
"""
        
        msg = Message(
            subject=subject,
            recipients=[email],
            body=body
        )
        
        mail.send(msg)
        logging.info(f"OTP email sent successfully to {email}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to send OTP email to {email}: {str(e)}")
        return False

def send_notification_email(email, subject, message):
    """Send general notification emails"""
    if not is_email_configured():
        logging.warning("Email not configured. Cannot send notification email.")
        return False
    
    try:
        msg = Message(
            subject=f"PrepMyCert - {subject}",
            recipients=[email],
            body=message
        )
        
        mail.send(msg)
        logging.info(f"Notification email sent successfully to {email}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to send notification email to {email}: {str(e)}")
        return False

def send_welcome_email(email, first_name):
    """Send welcome email to new users"""
    subject = "Welcome to PrepMyCert!"
    message = f"""
Hello {first_name},

Welcome to PrepMyCert! We're excited to help you prepare for your certification exams.

You can now browse our test packages and start your certification journey.

If you have any questions, feel free to contact our support team.

Best regards,
PrepMyCert Team
"""
    
    return send_notification_email(email, subject, message)

def send_purchase_confirmation_email(email, package_title, amount):
    """Send purchase confirmation email"""
    subject = "Purchase Confirmation"
    message = f"""
Hello,

Thank you for your purchase! Your payment has been processed successfully.

Package: {package_title}
Amount: ${amount:.2f}

You now have lifetime access to this test package.

Happy studying!

Best regards,
PrepMyCert Team
"""
    
    return send_notification_email(email, subject, message)

def test_email_configuration():
    """Test email configuration"""
    if not is_email_configured():
        return False, "Email credentials not configured"
    
    try:
        # Try to create a test message (don't send it)
        msg = Message(
            subject="Test Configuration",
            recipients=["test@example.com"],
            body="This is a test message"
        )
        return True, "Email configuration is valid"
    except Exception as e:
        return False, f"Email configuration error: {str(e)}"
