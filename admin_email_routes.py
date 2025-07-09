
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import app, db
from models import OTPToken, User
from email_service import send_notification_email

@app.route('/admin/email-settings')
@login_required
def admin_email_settings():
    """Admin email settings page"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get OTP statistics for last 24 hours
    yesterday = datetime.utcnow() - timedelta(days=1)
    otp_stats = {
        'login': OTPToken.query.filter(
            OTPToken.purpose == 'login',
            OTPToken.created_at >= yesterday
        ).count(),
        'verification': OTPToken.query.filter(
            OTPToken.purpose == 'verification',
            OTPToken.created_at >= yesterday
        ).count(),
        'password_reset': OTPToken.query.filter(
            OTPToken.purpose == 'password_reset',
            OTPToken.created_at >= yesterday
        ).count(),
    }
    
    return render_template('admin/email_settings.html', 
                         otp_stats=otp_stats,
                         config=app.config)

@app.route('/admin/test-email', methods=['POST'])
@login_required
def test_email_system():
    """Test email system functionality"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    test_email = request.form.get('test_email')
    if not test_email:
        flash('Test email is required.', 'error')
        return redirect(url_for('admin_email_settings'))
    
    # Send test email
    success = send_notification_email(
        test_email,
        "Email System Test",
        f"""Hello,

This is a test email from PrepMyCert to verify that the email system is working correctly.

Test details:
- Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
- Sent by: {current_user.email}
- Test email: {test_email}

If you received this email, the email system is functioning properly!

Best regards,
PrepMyCert System
"""
    )
    
    if success:
        flash(f'Test email sent successfully to {test_email}!', 'success')
    else:
        flash('Failed to send test email. Please check email configuration.', 'error')
    
    return redirect(url_for('admin_email_settings'))

@app.route('/admin/cleanup-otp', methods=['POST'])
@login_required
def cleanup_otp_tokens():
    """Cleanup expired OTP tokens"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    cleaned_count = OTPToken.cleanup_expired_tokens()
    flash(f'Cleaned up {cleaned_count} expired OTP tokens.', 'success')
    
    return redirect(url_for('admin_email_settings'))

@app.route('/admin/user-stats')
@login_required
def admin_user_stats():
    """Show user authentication statistics"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get user statistics
    total_users = User.query.count()
    verified_users = User.query.filter_by(is_email_verified=True).count()
    locked_users = User.query.filter_by(is_locked=True).count()
    
    # Recent registrations (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_registrations = User.query.filter(User.created_at >= week_ago).count()
    
    # Recent login attempts (last 24 hours)
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_login_attempts = OTPToken.query.filter(
        OTPToken.purpose == 'login',
        OTPToken.created_at >= yesterday
    ).count()
    
    stats = {
        'total_users': total_users,
        'verified_users': verified_users,
        'locked_users': locked_users,
        'recent_registrations': recent_registrations,
        'recent_login_attempts': recent_login_attempts
    }
    
    return render_template('admin/user_stats.html', stats=stats)
