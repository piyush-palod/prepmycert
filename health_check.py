"""
Health Check Module for PrepMyCert Application
Provides endpoints for monitoring application and dependency health
"""

import os
import json
from datetime import datetime
from flask import jsonify, request
from app import app, db
from models import User, Course
import psycopg2


@app.route('/health')
def health_check():
    """
    Basic health check endpoint
    Returns 200 OK if application is running
    """
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "service": "prepmycert"
    }), 200


@app.route('/health/detailed')
def detailed_health_check():
    """
    Detailed health check including database connectivity
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "service": "prepmycert",
        "checks": {}
    }
    
    overall_status = "healthy"
    status_code = 200
    
    # Database connectivity check
    try:
        # Simple query to check database connection
        db.session.execute("SELECT 1")
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
        overall_status = "unhealthy"
        status_code = 503
    
    # Environment variables check
    required_env_vars = ["DATABASE_URL", "SESSION_SECRET"]
    env_check = {"status": "healthy", "missing": []}
    
    for var in required_env_vars:
        if not os.environ.get(var):
            env_check["missing"].append(var)
    
    if env_check["missing"]:
        env_check["status"] = "unhealthy"
        env_check["message"] = f"Missing required environment variables: {', '.join(env_check['missing'])}"
        overall_status = "unhealthy"
        status_code = 503
    else:
        env_check["message"] = "All required environment variables are set"
    
    health_status["checks"]["environment"] = env_check
    
    # Optional services check
    optional_checks = {}
    
    # Stripe configuration check
    if os.environ.get("STRIPE_SECRET_KEY"):
        optional_checks["stripe"] = {"status": "configured"}
    else:
        optional_checks["stripe"] = {"status": "not_configured", "message": "Stripe not configured"}
    
    # Azure Storage check
    if os.environ.get("AZURE_STORAGE_CONNECTION_STRING"):
        optional_checks["azure_storage"] = {"status": "configured"}
    else:
        optional_checks["azure_storage"] = {"status": "not_configured", "message": "Azure Storage not configured"}
    
    # Email service check
    if os.environ.get("MAIL_SERVER") and os.environ.get("MAIL_USERNAME"):
        optional_checks["email"] = {"status": "configured"}
    else:
        optional_checks["email"] = {"status": "not_configured", "message": "Email service not configured"}
    
    health_status["checks"]["optional_services"] = optional_checks
    health_status["status"] = overall_status
    
    return jsonify(health_status), status_code


@app.route('/health/readiness')
def readiness_check():
    """
    Kubernetes/Container readiness probe
    Checks if application is ready to serve traffic
    """
    try:
        # Check database connectivity and basic data
        user_count = User.query.count()
        course_count = Course.query.count()
        
        return jsonify({
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "database": "connected",
                "data_integrity": {
                    "users": user_count,
                    "courses": course_count
                }
            }
        }), 200
    
    except Exception as e:
        return jsonify({
            "status": "not_ready",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }), 503


@app.route('/health/liveness')
def liveness_check():
    """
    Kubernetes/Container liveness probe
    Simple check to determine if application should be restarted
    """
    return jsonify({
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": "available"
    }), 200


@app.route('/metrics')
def application_metrics():
    """
    Basic application metrics for monitoring
    """
    try:
        # Get basic application statistics
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "users_total": User.query.count(),
                "users_verified": User.query.filter_by(is_email_verified=True).count(),
                "users_admin": User.query.filter_by(is_admin=True).count(),
                "courses_total": Course.query.count(),
                "courses_active": Course.query.filter_by(is_active=True).count(),
            },
            "system": {
                "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
                "environment": os.environ.get("FLASK_ENV", "development")
            }
        }
        
        return jsonify(metrics), 200
    
    except Exception as e:
        return jsonify({
            "error": "Failed to collect metrics",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@app.route('/version')
def version_info():
    """
    Application version information
    """
    return jsonify({
        "application": "PrepMyCert",
        "version": "1.0.0",
        "build_date": "2025-09-04",
        "environment": os.environ.get("FLASK_ENV", "development"),
        "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
        "timestamp": datetime.utcnow().isoformat()
    }), 200


# Error handlers for health check related errors
@app.errorhandler(503)
def service_unavailable(e):
    """Handle service unavailable errors"""
    return jsonify({
        "status": "service_unavailable",
        "message": "Service temporarily unavailable",
        "timestamp": datetime.utcnow().isoformat()
    }), 503


# Import health check module in main.py or routes
if __name__ == "__main__":
    print("Health check module loaded")