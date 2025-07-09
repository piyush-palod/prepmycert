
import os
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db, limiter
from models import User, OTPToken
from email_service import send_otp_email, send_welcome_email
from werkzeug.security import generate_password_hash

@app.route('/auth/request-otp', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def request_otp():
    """Request OTP for login"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Email is required.', 'error')
            return render_template('auth/request_otp.html')
        
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # For security, don't reveal if email exists
            flash('If the email exists in our system, an OTP has been sent.', 'info')
            return render_template('auth/request_otp.html')
        
        # Check if account is locked
        if user.is_account_locked():
            flash('Account is temporarily locked due to multiple failed attempts. Please try again later.', 'error')
            return render_template('auth/request_otp.html')
        
        # Clean up old tokens for this user
        old_tokens = OTPToken.query.filter_by(user_id=user.id, purpose='login').all()
        for token in old_tokens:
            db.session.delete(token)
        
        # Create new OTP token
        otp_token = OTPToken(
            user_id=user.id,
            purpose='login',
            duration_minutes=10,
            ip_address=request.remote_addr
        )
        db.session.add(otp_token)
        db.session.commit()
        
        # Send OTP email
        if send_otp_email(user.email, otp_token.token, 'login'):
            session['otp_email'] = email
            flash('OTP sent to your email. Please check and enter the code.', 'success')
            return redirect(url_for('verify_otp_login'))
        else:
            flash('Failed to send OTP. Please try again.', 'error')
    
    return render_template('auth/request_otp.html')

@app.route('/auth/verify-otp', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def verify_otp_login():
    """Verify OTP and login user"""
    email = session.get('otp_email')
    if not email:
        flash('Please request an OTP first.', 'error')
        return redirect(url_for('request_otp'))
    
    if request.method == 'POST':
        otp_code = request.form.get('otp_code', '').strip()
        
        if not otp_code:
            flash('OTP code is required.', 'error')
            return render_template('auth/verify_otp.html')
        
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('Invalid session. Please try again.', 'error')
            session.pop('otp_email', None)
            return redirect(url_for('request_otp'))
        
        # Check if account is locked
        if user.is_account_locked():
            flash('Account is temporarily locked. Please try again later.', 'error')
            session.pop('otp_email', None)
            return redirect(url_for('request_otp'))
        
        # Find valid OTP token
        otp_token = OTPToken.query.filter_by(
            user_id=user.id,
            purpose='login',
            is_used=False
        ).filter(OTPToken.expires_at > datetime.utcnow()).first()
        
        if not otp_token:
            user.increment_login_attempts()
            flash('No valid OTP found. Please request a new one.', 'error')
            session.pop('otp_email', None)
            return redirect(url_for('request_otp'))
        
        # Verify OTP
        if otp_token.verify_token(otp_code):
            # Successful login
            user.reset_login_attempts()
            user.is_email_verified = True
            db.session.commit()
            
            login_user(user)
            session.pop('otp_email', None)
            
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            user.increment_login_attempts()
            flash('Invalid OTP code. Please try again.', 'error')
    
    return render_template('auth/verify_otp.html')

@app.route('/auth/register-otp', methods=['GET', 'POST'])
@limiter.limit("3 per minute")
def register_otp():
    """Register new user with OTP verification"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        password = request.form.get('password', '').strip()
        
        # Validation
        if not all([email, first_name, last_name]):
            flash('All fields are required.', 'error')
            return render_template('auth/register_otp.html')
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please use a different email or try logging in.', 'error')
            return render_template('auth/register_otp.html')
        
        # Create new user
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_email_verified=False
        )
        
        # Set password if provided (optional for OTP-only users)
        if password:
            user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Create OTP token for email verification
        otp_token = OTPToken(
            user_id=user.id,
            purpose='verification',
            duration_minutes=15,
            ip_address=request.remote_addr
        )
        db.session.add(otp_token)
        db.session.commit()
        
        # Send OTP email
        if send_otp_email(user.email, otp_token.token, 'verification'):
            session['verification_email'] = email
            flash('Registration successful! Please check your email for verification code.', 'success')
            return redirect(url_for('verify_registration'))
        else:
            flash('Failed to send verification email. Please try again.', 'error')
    
    return render_template('auth/register_otp.html')

@app.route('/auth/verify-registration', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def verify_registration():
    """Verify email during registration"""
    email = session.get('verification_email')
    if not email:
        flash('Please register first.', 'error')
        return redirect(url_for('register_otp'))
    
    if request.method == 'POST':
        otp_code = request.form.get('otp_code', '').strip()
        
        if not otp_code:
            flash('Verification code is required.', 'error')
            return render_template('auth/verify_registration.html')
        
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('Invalid session. Please try again.', 'error')
            session.pop('verification_email', None)
            return redirect(url_for('register_otp'))
        
        # Find valid OTP token
        otp_token = OTPToken.query.filter_by(
            user_id=user.id,
            purpose='verification',
            is_used=False
        ).filter(OTPToken.expires_at > datetime.utcnow()).first()
        
        if not otp_token:
            flash('No valid verification code found. Please request a new one.', 'error')
            return render_template('auth/verify_registration.html')
        
        # Verify OTP
        if otp_token.verify_token(otp_code):
            # Email verified successfully
            user.is_email_verified = True
            db.session.commit()
            
            # Send welcome email
            send_welcome_email(user.email, user.first_name)
            
            session.pop('verification_email', None)
            flash('Email verified successfully! You can now log in.', 'success')
            return redirect(url_for('request_otp'))
        else:
            flash('Invalid verification code. Please try again.', 'error')
    
    return render_template('auth/verify_registration.html')

@app.route('/auth/forgot-password', methods=['GET', 'POST'])
@limiter.limit("3 per minute")
def forgot_password():
    """Request password reset OTP"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Email is required.', 'error')
            return render_template('auth/forgot_password.html')
        
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # For security, don't reveal if email exists
            flash('If the email exists in our system, a password reset code has been sent.', 'info')
            return render_template('auth/forgot_password.html')
        
        # Clean up old password reset tokens
        old_tokens = OTPToken.query.filter_by(user_id=user.id, purpose='password_reset').all()
        for token in old_tokens:
            db.session.delete(token)
        
        # Create new OTP token for password reset
        otp_token = OTPToken(
            user_id=user.id,
            purpose='password_reset',
            duration_minutes=15,
            ip_address=request.remote_addr
        )
        db.session.add(otp_token)
        db.session.commit()
        
        # Send OTP email
        if send_otp_email(user.email, otp_token.token, 'password_reset'):
            session['reset_email'] = email
            flash('Password reset code sent to your email.', 'success')
            return redirect(url_for('reset_password'))
        else:
            flash('Failed to send reset code. Please try again.', 'error')
    
    return render_template('auth/forgot_password.html')

@app.route('/auth/reset-password', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def reset_password():
    """Reset password with OTP verification"""
    email = session.get('reset_email')
    if not email:
        flash('Please request a password reset first.', 'error')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        otp_code = request.form.get('otp_code', '').strip()
        new_password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        if not all([otp_code, new_password, confirm_password]):
            flash('All fields are required.', 'error')
            return render_template('auth/reset_password.html')
        
        if new_password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('auth/reset_password.html')
        
        if len(new_password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('auth/reset_password.html')
        
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('Invalid session. Please try again.', 'error')
            session.pop('reset_email', None)
            return redirect(url_for('forgot_password'))
        
        # Find valid OTP token
        otp_token = OTPToken.query.filter_by(
            user_id=user.id,
            purpose='password_reset',
            is_used=False
        ).filter(OTPToken.expires_at > datetime.utcnow()).first()
        
        if not otp_token:
            flash('No valid reset code found. Please request a new one.', 'error')
            session.pop('reset_email', None)
            return redirect(url_for('forgot_password'))
        
        # Verify OTP
        if otp_token.verify_token(otp_code):
            # Reset password
            user.set_password(new_password)
            user.reset_login_attempts()  # Reset any lockouts
            db.session.commit()
            
            session.pop('reset_email', None)
            flash('Password reset successful! You can now log in.', 'success')
            return redirect(url_for('request_otp'))
        else:
            flash('Invalid reset code. Please try again.', 'error')
    
    return render_template('auth/reset_password.html')

@app.route('/auth/resend-otp', methods=['POST'])
@limiter.limit("3 per minute")
def resend_otp():
    """Resend OTP for various purposes"""
    purpose = request.form.get('purpose')  # 'login', 'verification', 'password_reset'
    
    if purpose == 'login':
        email = session.get('otp_email')
        redirect_route = 'verify_otp_login'
    elif purpose == 'verification':
        email = session.get('verification_email')
        redirect_route = 'verify_registration'
    elif purpose == 'password_reset':
        email = session.get('reset_email')
        redirect_route = 'reset_password'
    else:
        flash('Invalid request.', 'error')
        return redirect(url_for('request_otp'))
    
    if not email:
        flash('Session expired. Please start over.', 'error')
        return redirect(url_for('request_otp'))
    
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('request_otp'))
    
    # Clean up old tokens
    old_tokens = OTPToken.query.filter_by(user_id=user.id, purpose=purpose).all()
    for token in old_tokens:
        db.session.delete(token)
    
    # Create new OTP token
    duration = 15 if purpose == 'password_reset' else 10
    otp_token = OTPToken(
        user_id=user.id,
        purpose=purpose,
        duration_minutes=duration,
        ip_address=request.remote_addr
    )
    db.session.add(otp_token)
    db.session.commit()
    
    # Send new OTP
    if send_otp_email(user.email, otp_token.token, purpose.replace('_', ' ')):
        flash('New OTP sent to your email.', 'success')
    else:
        flash('Failed to send OTP. Please try again.', 'error')
    
    return redirect(url_for(redirect_route))

# Background task to clean up expired tokens
@app.before_request
def cleanup_expired_tokens():
    """Clean up expired OTP tokens periodically"""
    # Only run cleanup occasionally to avoid performance impact
    import random
    if random.randint(1, 100) == 1:  # 1% chance
        OTPToken.cleanup_expired_tokens()
