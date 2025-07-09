import os
import logging
from flask_mail import Mail, Message
from flask import current_app

mail = Mail()

def init_mail(app):
    """Initialize Flask-Mail with the app"""
    try:
        # Email configuration with defaults for development
        app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'localhost')
        app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 1025))  # MailHog default
        app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'false').lower() in ['true', '1', 'yes']
        app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'false').lower() in ['true', '1', 'yes']
        app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
        app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
        app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@prepmycert.com')

        # For development without email server, disable mail
        app.config['MAIL_SUPPRESS_SEND'] = os.environ.get('MAIL_SUPPRESS_SEND', 'true').lower() in ['true', '1', 'yes']

        mail.init_app(app)
        logging.info("Email service initialized")

        if app.config['MAIL_SUPPRESS_SEND']:
            logging.info("Email sending is suppressed for development")

    except Exception as e:
        logging.error(f"Failed to initialize email service: {e}")

def is_email_configured():
    """Check if email is properly configured for production"""
    try:
        # In development mode, consider it configured even if suppressed
        if current_app.config.get('MAIL_SUPPRESS_SEND'):
            return True

        required_settings = ['MAIL_SERVER', 'MAIL_DEFAULT_SENDER']
        return all(current_app.config.get(setting) for setting in required_settings)
    except:
        return False

def test_email_configuration():
    """Test email configuration"""
    try:
        config = current_app.config

        if config.get('MAIL_SUPPRESS_SEND'):
            return {'success': True, 'message': 'Email sending suppressed for development'}

        if not config.get('MAIL_SERVER'):
            return {'success': False, 'error': 'MAIL_SERVER not set'}
        if not config.get('MAIL_DEFAULT_SENDER'):
            return {'success': False, 'error': 'MAIL_DEFAULT_SENDER not set'}

        return {'success': True, 'message': 'Email configuration looks valid'}

    except Exception as e:
        return {'success': False, 'error': str(e)}

def send_otp_email(email, otp_code, purpose):
    """Send OTP email to user"""
    try:
        # In development mode, just log the OTP instead of sending email
        if current_app.config.get('MAIL_SUPPRESS_SEND'):
            logging.info(f"[DEV MODE] OTP for {email}: {otp_code} (purpose: {purpose})")
            return True

        if not is_email_configured():
            logging.error("Email not configured - cannot send OTP")
            return False

        subject_map = {
            'login': 'Your Login Code - PrepMyCert',
            'verification': 'Verify Your Email - PrepMyCert', 
            'password_reset': 'Password Reset Code - PrepMyCert'
        }

        subject = subject_map.get(purpose, 'Your Verification Code - PrepMyCert')

        body = f"""
Hello,

Your verification code for PrepMyCert is: {otp_code}

This code will expire in 10 minutes.

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
        # In development, still return True to allow testing
        if current_app.config.get('MAIL_SUPPRESS_SEND'):
            return True
        return False

def send_welcome_email(email, first_name):
    """Send welcome email to new user"""
    try:
        if current_app.config.get('MAIL_SUPPRESS_SEND'):
            logging.info(f"[DEV MODE] Welcome email would be sent to {email}")
            return True

        if not is_email_configured():
            logging.warning("Email not configured - skipping welcome email")
            return False

        msg = Message(
            subject='Welcome to PrepMyCert!',
            recipients=[email],
            body=f"""
Hello {first_name},

Welcome to PrepMyCert! Your account has been successfully created and verified.

You can now:
- Browse our test packages
- Purchase lifetime access to certification practice tests
- Track your progress and performance

Start your certification journey today!

Best regards,
PrepMyCert Team
"""
        )

        mail.send(msg)
        logging.info(f"Welcome email sent to {email}")
        return True

    except Exception as e:
        logging.error(f"Failed to send welcome email to {email}: {str(e)}")
        return False

def send_notification_email(email, subject, body):
    """Send a general notification email"""
    try:
        if current_app.config.get('MAIL_SUPPRESS_SEND'):
            logging.info(f"[DEV MODE] Notification email to {email}: {subject}")
            return True

        if not is_email_configured():
            logging.warning("Email not configured - cannot send notification")
            return False

        msg = Message(
            subject=subject,
            recipients=[email],
            body=body
        )

        mail.send(msg)
        logging.info(f"Notification email sent to {email}")
        return True

    except Exception as e:
        logging.error(f"Failed to send notification email to {email}: {str(e)}")
        return False