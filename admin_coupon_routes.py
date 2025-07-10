
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import app, db
from models import Coupon, Bundle, BundlePackage, TestPackage, CouponUsage, UserPurchase
from datetime import datetime, timedelta
import re

@app.route('/admin/coupons')
@login_required
def admin_coupons():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    coupons = Coupon.query.order_by(Coupon.created_at.desc()).all()
    return render_template('admin/coupons.html', coupons=coupons)

@app.route('/admin/create-coupon', methods=['GET', 'POST'])
@login_required
def create_coupon():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            code = request.form.get('code', '').upper().strip()
            description = request.form.get('description', '').strip()
            discount_type = request.form.get('discount_type')
            discount_value = float(request.form.get('discount_value', 0))
            minimum_purchase = request.form.get('minimum_purchase')
            usage_limit = request.form.get('usage_limit')
            valid_until = request.form.get('valid_until')
            
            # Validate code format
            if not re.match(r'^[A-Z0-9_-]+$', code):
                flash('Coupon code can only contain letters, numbers, hyphens, and underscores.', 'error')
                return render_template('admin/create_coupon.html')
            
            # Check if code already exists
            existing_coupon = Coupon.query.filter_by(code=code).first()
            if existing_coupon:
                flash('A coupon with this code already exists.', 'error')
                return render_template('admin/create_coupon.html')
            
            # Validate discount value
            if discount_type == 'percentage' and (discount_value <= 0 or discount_value > 100):
                flash('Percentage discount must be between 1 and 100.', 'error')
                return render_template('admin/create_coupon.html')
            elif discount_type == 'fixed' and discount_value <= 0:
                flash('Fixed discount must be greater than 0.', 'error')
                return render_template('admin/create_coupon.html')
            
            # Create coupon
            coupon = Coupon(
                code=code,
                description=description,
                discount_type=discount_type,
                discount_value=discount_value,
                minimum_purchase=float(minimum_purchase) if minimum_purchase else None,
                usage_limit=int(usage_limit) if usage_limit else None,
                valid_until=datetime.strptime(valid_until, '%Y-%m-%d') if valid_until else None,
                created_by=current_user.id
            )
            
            db.session.add(coupon)
            db.session.commit()
            
            flash(f'Coupon "{code}" created successfully!', 'success')
            return redirect(url_for('admin_coupons'))
            
        except ValueError as e:
            flash('Invalid input values. Please check your entries.', 'error')
        except Exception as e:
            flash(f'Error creating coupon: {str(e)}', 'error')
    
    return render_template('admin/create_coupon.html')

@app.route('/admin/toggle-coupon/<int:coupon_id>', methods=['POST'])
@login_required
def toggle_coupon(coupon_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    coupon = Coupon.query.get_or_404(coupon_id)
    coupon.is_active = not coupon.is_active
    db.session.commit()
    
    status = 'activated' if coupon.is_active else 'deactivated'
    flash(f'Coupon "{coupon.code}" {status} successfully.', 'success')
    return redirect(url_for('admin_coupons'))

@app.route('/admin/bundles')
@login_required
def admin_bundles():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    bundles = Bundle.query.order_by(Bundle.created_at.desc()).all()
    return render_template('admin/bundles.html', bundles=bundles)

@app.route('/admin/create-bundle', methods=['GET', 'POST'])
@login_required
def create_bundle():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            price = float(request.form.get('price', 0))
            package_ids = request.form.getlist('package_ids[]')
            
            if not title or not description:
                flash('Title and description are required.', 'error')
                return render_template('admin/create_bundle.html', packages=TestPackage.query.filter_by(is_active=True).all())
            
            if not package_ids or len(package_ids) < 2:
                flash('Please select at least 2 test packages for the bundle.', 'error')
                return render_template('admin/create_bundle.html', packages=TestPackage.query.filter_by(is_active=True).all())
            
            # Calculate original price
            selected_packages = TestPackage.query.filter(TestPackage.id.in_(package_ids)).all()
            original_price = sum(pkg.price for pkg in selected_packages)
            
            if price >= original_price:
                flash('Bundle price must be less than the sum of individual package prices.', 'error')
                return render_template('admin/create_bundle.html', packages=TestPackage.query.filter_by(is_active=True).all())
            
            # Create bundle
            bundle = Bundle(
                title=title,
                description=description,
                price=price,
                original_price=original_price,
                created_by=current_user.id
            )
            db.session.add(bundle)
            db.session.flush()  # Get the bundle ID
            
            # Add packages to bundle
            for package_id in package_ids:
                bundle_package = BundlePackage(
                    bundle_id=bundle.id,
                    test_package_id=int(package_id)
                )
                db.session.add(bundle_package)
            
            db.session.commit()
            
            flash(f'Bundle "{title}" created successfully!', 'success')
            return redirect(url_for('admin_bundles'))
            
        except ValueError:
            flash('Invalid price value. Please enter a valid number.', 'error')
        except Exception as e:
            flash(f'Error creating bundle: {str(e)}', 'error')
    
    packages = TestPackage.query.filter_by(is_active=True).all()
    return render_template('admin/create_bundle.html', packages=packages)

@app.route('/admin/toggle-bundle/<int:bundle_id>', methods=['POST'])
@login_required
def toggle_bundle(bundle_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    bundle = Bundle.query.get_or_404(bundle_id)
    bundle.is_active = not bundle.is_active
    db.session.commit()
    
    status = 'activated' if bundle.is_active else 'deactivated'
    flash(f'Bundle "{bundle.title}" {status} successfully.', 'success')
    return redirect(url_for('admin_bundles'))

@app.route('/admin/coupon-analytics')
@login_required
def coupon_analytics():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get coupon usage statistics
    coupon_stats = db.session.query(
        Coupon.code,
        Coupon.used_count,
        db.func.sum(CouponUsage.discount_amount).label('total_discount'),
        db.func.count(CouponUsage.id).label('usage_count')
    ).outerjoin(CouponUsage).group_by(Coupon.id).all()
    
    # Get recent coupon usages
    recent_usages = db.session.query(CouponUsage, Coupon, UserPurchase).join(
        Coupon
    ).join(UserPurchase).order_by(CouponUsage.used_at.desc()).limit(10).all()
    
    return render_template('admin/coupon_analytics.html', 
                         coupon_stats=coupon_stats,
                         recent_usages=recent_usages)

@app.route('/api/validate-coupon', methods=['POST'])
@login_required
def validate_coupon():
    """API endpoint to validate coupon codes"""
    data = request.get_json()
    coupon_code = data.get('code', '').upper().strip()
    amount = float(data.get('amount', 0))
    
    if not coupon_code:
        return jsonify({'valid': False, 'message': 'Please enter a coupon code'})
    
    coupon = Coupon.query.filter_by(code=coupon_code).first()
    if not coupon:
        return jsonify({'valid': False, 'message': 'Invalid coupon code'})
    
    is_valid, message = coupon.is_valid(current_user.id, amount)
    
    if is_valid:
        discount = coupon.calculate_discount(amount)
        return jsonify({
            'valid': True,
            'message': message,
            'discount_amount': discount,
            'final_amount': amount - discount,
            'discount_type': coupon.discount_type,
            'discount_value': coupon.discount_value
        })
    else:
        return jsonify({'valid': False, 'message': message})
