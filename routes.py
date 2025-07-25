import os
import re
import stripe
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import app, db
from models import User, TestPackage, Question, AnswerOption, UserPurchase, TestAttempt, UserAnswer, Bundle, Coupon
from utils import import_questions_from_csv, process_text_with_images
from datetime import datetime

import os
import re
import stripe
from werkzeug.utils import secure_filename
from flask import render_template, request, redirect, url_for, flash, session, jsonify


# Configure Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

@app.route('/')
def index():
    test_packages = TestPackage.query.filter_by(is_active=True).all()
    from models import Bundle
    bundles = Bundle.query.filter_by(is_active=True).limit(3).all()  # Show top 3 bundles
    return render_template('index.html', test_packages=test_packages, bundles=bundles)

# Legacy routes - redirect to new OTP-based authentication
@app.route('/register', methods=['GET', 'POST'])
def register():
    flash('Please use our new secure registration system.', 'info')
    return redirect(url_for('register_otp'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    flash('Please use our new secure login system.', 'info')
    return redirect(url_for('request_otp'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get user's purchased packages (excluding bundle items)
    purchased_packages = db.session.query(TestPackage).join(UserPurchase).filter(
        UserPurchase.user_id == current_user.id,
        UserPurchase.test_package_id.isnot(None),
        UserPurchase.purchase_type != 'bundle_item'
    ).all()

    # Get user's purchased bundles
    from models import Bundle
    purchased_bundles = db.session.query(Bundle).join(UserPurchase).filter(
        UserPurchase.user_id == current_user.id,
        UserPurchase.bundle_id.isnot(None)
    ).all()

    # Get all accessible packages (including from bundles)
    all_accessible_packages = db.session.query(TestPackage).join(UserPurchase).filter(
        UserPurchase.user_id == current_user.id,
        UserPurchase.test_package_id.isnot(None)
    ).all()

    # Get recent test attempts
    recent_attempts = TestAttempt.query.filter_by(
        user_id=current_user.id,
        is_completed=True
    ).order_by(TestAttempt.end_time.desc()).limit(5).all()

    return render_template('dashboard.html', 
                         purchased_packages=purchased_packages,
                         purchased_bundles=purchased_bundles,
                         all_accessible_packages=all_accessible_packages,
                         recent_attempts=recent_attempts)

@app.route('/test-packages')
def test_packages():
    packages = TestPackage.query.filter_by(is_active=True).all()
    return render_template('test_packages.html', packages=packages)

@app.route('/bundles')
def bundles():
    from models import Bundle
    bundles = Bundle.query.filter_by(is_active=True).all()
    return render_template('bundles.html', bundles=bundles)

@app.route('/bundle/<int:bundle_id>')
def view_bundle(bundle_id):
    from models import Bundle
    bundle = Bundle.query.get_or_404(bundle_id)

    # Check if user has purchased this bundle or has access to all packages
    has_bundle_access = False
    individual_access = {}

    if current_user.is_authenticated:
        # Check for direct bundle purchase
        bundle_purchase = UserPurchase.query.filter_by(
            user_id=current_user.id,
            bundle_id=bundle_id
        ).first()
        has_bundle_access = bundle_purchase is not None

        # Check individual package access
        for bp in bundle.bundle_packages:
            package_purchase = UserPurchase.query.filter_by(
                user_id=current_user.id,
                test_package_id=bp.test_package_id
            ).first()
            individual_access[bp.test_package_id] = package_purchase is not None

    return render_template('bundle_detail.html', 
                         bundle=bundle, 
                         has_bundle_access=has_bundle_access,
                         individual_access=individual_access)

@app.route('/package/<int:package_id>')
def package_detail(package_id):
    package = TestPackage.query.get_or_404(package_id)

    # Check if user has purchased this package
    has_purchased = False
    if current_user.is_authenticated:
        purchase = UserPurchase.query.filter_by(
            user_id=current_user.id,
            test_package_id=package_id
        ).first()
        has_purchased = purchase is not None

    return render_template('package_detail.html', package=package, has_purchased=has_purchased)

@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    package_id = request.form.get('package_id')
    bundle_id = request.form.get('bundle_id')
    coupon_code = request.form.get('coupon_code', '').upper().strip()

    # Determine if it's a package or bundle purchase
    if bundle_id:
        from models import Bundle, BundlePackage
        bundle = Bundle.query.get_or_404(bundle_id)

        # Check if user already has access to all packages in bundle
        package_ids = [bp.test_package_id for bp in bundle.bundle_packages]
        existing_purchases = UserPurchase.query.filter(
            UserPurchase.user_id == current_user.id,
            UserPurchase.test_package_id.in_(package_ids)
        ).all()

        if len(existing_purchases) == len(package_ids):
            flash('You already have access to all packages in this bundle.', 'info')
            return redirect(url_for('view_bundle', bundle_id=bundle_id))

        item_title = bundle.title
        item_description = bundle.description
        original_amount = bundle.price
        purchase_type = 'bundle'

    else:
        package = TestPackage.query.get_or_404(package_id)

        # Check if user already purchased this package
        existing_purchase = UserPurchase.query.filter_by(
            user_id=current_user.id,
            test_package_id=package_id
        ).first()

        if existing_purchase:
            flash('You have already purchased this package.', 'info')
            return redirect(url_for('package_detail', package_id=package_id))

        item_title = package.title
        item_description = package.description
        original_amount = package.price
        purchase_type = 'package'

    # Apply coupon if provided
    discount_amount = 0
    final_amount = original_amount
    coupon = None

    if coupon_code:
        from models import Coupon
        coupon = Coupon.query.filter_by(code=coupon_code).first()
        if coupon:
            is_valid, message = coupon.is_valid(current_user.id, original_amount)
            if is_valid:
                discount_amount = coupon.calculate_discount(original_amount)
                final_amount = original_amount - discount_amount
            else:
                flash(f'Coupon error: {message}', 'error')
                return redirect(request.referrer or url_for('index'))
        else:
            flash('Invalid coupon code.', 'error')
            return redirect(request.referrer or url_for('index'))

    try:
        # Get domain for success/cancel URLs
        domain = os.environ.get('REPLIT_DEV_DOMAIN')
        if not domain:
            domain = request.host

        # Create line items for checkout
        line_items = [{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': item_title,
                    'description': item_description[:100] + '...' if len(item_description) > 100 else item_description,
                },
                'unit_amount': int(final_amount * 100),  # Convert to cents
            },
            'quantity': 1,
        }]

        # Add discount line item if applicable
        if discount_amount > 0:
            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'Discount ({coupon_code})',
                    },
                    'unit_amount': -int(discount_amount * 100),  # Negative amount for discount
                },
                'quantity': 1,
            })

        metadata = {
            'user_id': current_user.id,
            'purchase_type': purchase_type,
            'original_amount': str(original_amount),
            'discount_amount': str(discount_amount),
        }

        if bundle_id:
            metadata['bundle_id'] = bundle_id
            success_url = f'https://{domain}/payment-success?session_id={{CHECKOUT_SESSION_ID}}&bundle_id={bundle_id}'
            cancel_url = f'https://{domain}/payment-cancel?bundle_id={bundle_id}'
        else:
            metadata['package_id'] = package_id
            success_url = f'https://{domain}/payment-success?session_id={{CHECKOUT_SESSION_ID}}&package_id={package_id}'
            cancel_url = f'https://{domain}/payment-cancel?package_id={package_id}'

        if coupon_code:
            metadata['coupon_code'] = coupon_code

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata
        )

        return redirect(checkout_session.url, code=303)

    except Exception as e:
        flash(f'Payment processing error: {str(e)}', 'error')
        if bundle_id:
            return redirect(url_for('view_bundle', bundle_id=bundle_id))
        else:
            return redirect(url_for('package_detail', package_id=package_id))

@app.route('/payment-success')
@login_required
def payment_success():
    session_id = request.args.get('session_id')
    package_id = request.args.get('package_id')
    bundle_id = request.args.get('bundle_id')

    if not session_id or (not package_id and not bundle_id):
        flash('Invalid payment session.', 'error')
        return redirect(url_for('dashboard'))

    try:
        # Retrieve the session from Stripe
        session = stripe.checkout.Session.retrieve(session_id)

        if session.payment_status == 'paid':
            metadata = session.metadata
            purchase_type = metadata.get('purchase_type', 'package')
            original_amount = float(metadata.get('original_amount', 0))
            discount_amount = float(metadata.get('discount_amount', 0))
            coupon_code = metadata.get('coupon_code')

            if purchase_type == 'bundle' and bundle_id:
                from models import Bundle, BundlePackage, Coupon, CouponUsage

                # Check if bundle purchase already recorded
                existing_purchase = UserPurchase.query.filter_by(
                    user_id=current_user.id,
                    bundle_id=bundle_id,
                    stripe_payment_intent_id=session.payment_intent
                ).first()

                if not existing_purchase:
                    bundle = Bundle.query.get(bundle_id)

                    # Record the bundle purchase
                    purchase = UserPurchase(
                        user_id=current_user.id,
                        bundle_id=bundle_id,
                        stripe_payment_intent_id=session.payment_intent,
                        amount_paid=session.amount_total / 100,
                        original_amount=original_amount,
                        discount_amount=discount_amount,
                        coupon_code=coupon_code,
                        purchase_type='bundle'
                    )
                    db.session.add(purchase)
                    db.session.flush()  # Get purchase ID

                    # Record individual package access
                    for bp in bundle.bundle_packages:
                        # Check if user already has this package
                        existing_pkg_purchase = UserPurchase.query.filter_by(
                            user_id=current_user.id,
                            test_package_id=bp.test_package_id
                        ).first()

                        if not existing_pkg_purchase:
                            pkg_purchase = UserPurchase(
                                user_id=current_user.id,
                                test_package_id=bp.test_package_id,
                                stripe_payment_intent_id=session.payment_intent,
                                amount_paid=0,  # Individual packages in bundle have no separate cost
                                original_amount=bp.test_package.price,
                                discount_amount=bp.test_package.price,  # Full discount as part of bundle
                                purchase_type='bundle_item'
                            )
                            db.session.add(pkg_purchase)

                    # Handle coupon usage
                    if coupon_code and discount_amount > 0:
                        coupon = Coupon.query.filter_by(code=coupon_code).first()
                        if coupon:
                            coupon.used_count += 1

                            coupon_usage = CouponUsage(
                                coupon_id=coupon.id,
                                user_id=current_user.id,
                                purchase_id=purchase.id,
                                discount_amount=discount_amount
                            )
                            db.session.add(coupon_usage)

                    db.session.commit()

                    # Send purchase confirmation email
                    from email_service import send_purchase_confirmation_email
                    send_purchase_confirmation_email(
                        current_user.email, 
                        bundle.title, 
                        session.amount_total / 100
                    )

                    flash(f'Payment successful! You now have lifetime access to all {bundle.package_count} packages in {bundle.title}.', 'success')
                else:
                    flash('You already have access to this bundle.', 'info')

            else:
                # Single package purchase
                from models import Coupon, CouponUsage

                existing_purchase = UserPurchase.query.filter_by(
                    user_id=current_user.id,
                    test_package_id=package_id,
                    stripe_payment_intent_id=session.payment_intent
                ).first()

                if not existing_purchase:
                    package = TestPackage.query.get(package_id)
                    purchase = UserPurchase(
                        user_id=current_user.id,
                        test_package_id=package_id,
                        stripe_payment_intent_id=session.payment_intent,
                        amount_paid=session.amount_total / 100,
                        original_amount=original_amount,
                        discount_amount=discount_amount,
                        coupon_code=coupon_code,
                        purchase_type='package'
                    )
                    db.session.add(purchase)
                    db.session.flush()  # Get purchase ID

                    # Handle coupon usage
                    if coupon_code and discount_amount > 0:
                        coupon = Coupon.query.filter_by(code=coupon_code).first()
                        if coupon:
                            coupon.used_count += 1

                            coupon_usage = CouponUsage(
                                coupon_id=coupon.id,
                                user_id=current_user.id,
                                purchase_id=purchase.id,
                                discount_amount=discount_amount
                            )
                            db.session.add(coupon_usage)

                    db.session.commit()

                    # Send purchase confirmation email
                    from email_service import send_purchase_confirmation_email
                    send_purchase_confirmation_email(
                        current_user.email, 
                        package.title, 
                        session.amount_total / 100
                    )

                    flash(f'Payment successful! You now have lifetime access to {package.title}.', 'success')
                else:
                    flash('You already have access to this package.', 'info')
        else:
            flash('Payment was not completed successfully.', 'error')

    except Exception as e:
        flash(f'Error processing payment: {str(e)}', 'error')

    return render_template('payment_success.html')

@app.route('/payment-cancel')
def payment_cancel():
    package_id = request.args.get('package_id')
    flash('Payment was cancelled.', 'info')
    return render_template('payment_cancel.html', package_id=package_id)

@app.route('/take-test/<int:package_id>')
@login_required
def take_test(package_id):
    # Check if user has purchased this package or is an admin
    purchase = UserPurchase.query.filter_by(
        user_id=current_user.id,
        test_package_id=package_id
    ).first()

    if not purchase and not current_user.is_admin:
        flash('You must purchase this package before taking the test.', 'error')
        return redirect(url_for('package_detail', package_id=package_id))

    package = TestPackage.query.get_or_404(package_id)
    questions = Question.query.filter_by(test_package_id=package_id).all()

    if not questions:
        flash('This test package does not have any questions yet.', 'warning')
        return redirect(url_for('dashboard'))

    # Convert questions to serializable format
    questions_data = []
    for question in questions:
        options_data = []
        for option in question.answer_options:
            options_data.append({
                'id': option.id,
                'text': option.option_text,
                'order': option.option_order
            })

        # Sort options by order
        options_data.sort(key=lambda x: x['order'])

        questions_data.append({
            'id': question.id,
            'text': process_text_with_images(question.question_text, package.title),
            'type': question.question_type,
            'domain': question.domain,
            'options': options_data
        })

    # Create new test attempt
    test_attempt = TestAttempt(
        user_id=current_user.id,
        test_package_id=package_id,
        total_questions=len(questions)
    )
    db.session.add(test_attempt)
    db.session.commit()

    session['test_attempt_id'] = test_attempt.id
    session['current_question_index'] = 0

    return render_template('test_taking.html', 
                         package=package, 
                         questions=questions_data,
                         test_attempt=test_attempt)

@app.route('/submit-answer', methods=['POST'])
@login_required
def submit_answer():
    test_attempt_id = session.get('test_attempt_id')
    if not test_attempt_id:
        return jsonify({'error': 'No active test session'}), 400

    question_id = request.json.get('question_id')
    selected_option_id = request.json.get('selected_option_id')

    test_attempt = TestAttempt.query.get(test_attempt_id)
    if not test_attempt or test_attempt.user_id != current_user.id:
        return jsonify({'error': 'Invalid test attempt'}), 400

    # Check if answer already exists
    existing_answer = UserAnswer.query.filter_by(
        test_attempt_id=test_attempt_id,
        question_id=question_id
    ).first()

    if existing_answer:
        # Update existing answer
        existing_answer.selected_option_id = selected_option_id
        selected_option = AnswerOption.query.get(selected_option_id)
        existing_answer.is_correct = selected_option.is_correct if selected_option else False
        existing_answer.answered_at = datetime.utcnow()
    else:
        # Create new answer
        selected_option = AnswerOption.query.get(selected_option_id)
        user_answer = UserAnswer(
            test_attempt_id=test_attempt_id,
            question_id=question_id,
            selected_option_id=selected_option_id,
            is_correct=selected_option.is_correct if selected_option else False
        )
        db.session.add(user_answer)

    db.session.commit()

    return jsonify({'success': True})

@app.route('/complete-test', methods=['POST'])
@login_required
def complete_test():
    test_attempt_id = session.get('test_attempt_id')
    if not test_attempt_id:
        return jsonify({'error': 'No active test session'}), 400

    test_attempt = TestAttempt.query.get(test_attempt_id)
    if not test_attempt or test_attempt.user_id != current_user.id:
        return jsonify({'error': 'Invalid test attempt'}), 400

    # Calculate score
    correct_answers = UserAnswer.query.filter_by(
        test_attempt_id=test_attempt_id,
        is_correct=True
    ).count()

    total_questions = test_attempt.total_questions
    score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0

    # Update test attempt
    test_attempt.correct_answers = correct_answers
    test_attempt.score = score
    test_attempt.end_time = datetime.utcnow()
    test_attempt.is_completed = True

    db.session.commit()

    # Clear session
    session.pop('test_attempt_id', None)
    session.pop('current_question_index', None)

    return redirect(url_for('test_results', attempt_id=test_attempt_id))

@app.route('/test-results/<int:attempt_id>')
@login_required
def test_results(attempt_id):
    test_attempt = TestAttempt.query.get_or_404(attempt_id)

    if test_attempt.user_id != current_user.id:
        flash('You can only view your own test results.', 'error')
        return redirect(url_for('dashboard'))

    # Get user answers with question details
    user_answers_raw = db.session.query(UserAnswer, Question, AnswerOption).join(
        Question, UserAnswer.question_id == Question.id
    ).outerjoin(
        AnswerOption, UserAnswer.selected_option_id == AnswerOption.id
    ).filter(
        UserAnswer.test_attempt_id == attempt_id
    ).all()

    # Process user answers to include image processing
    user_answers = []
    for user_answer, question, selected_option in user_answers_raw:
        # Get package title for image processing
        package_title = test_attempt.test_package.title

        # Process question text for images
        processed_question = Question(
            id=question.id,
            test_package_id=question.test_package_id,
            question_text=process_text_with_images(question.question_text, package_title),
            question_type=question.question_type,
            domain=question.domain,
            overall_explanation=process_text_with_images(question.overall_explanation, package_title) if question.overall_explanation else ''
        )

        # Process answer options for images
        processed_options = []
        for option in question.answer_options:
            processed_option = AnswerOption(
                id=option.id,
                question_id=option.question_id,
                option_text=process_text_with_images(option.option_text, package_title),
                explanation=process_text_with_images(option.explanation, package_title) if option.explanation else '',
                is_correct=option.is_correct,
                option_order=option.option_order
            )
            processed_options.append(processed_option)

        # Attach processed options to processed question
        processed_question.answer_options = processed_options

        # Process selected option if it exists
        processed_selected_option = None
        if selected_option:
            processed_selected_option = AnswerOption(
                id=selected_option.id,
                question_id=selected_option.question_id,
                option_text=process_text_with_images(selected_option.option_text, package_title),
                explanation=process_text_with_images(selected_option.explanation, package_title) if selected_option.explanation else '',
                is_correct=selected_option.is_correct,
                option_order=selected_option.option_order
            )

        user_answers.append((user_answer, processed_question, processed_selected_option))

    return render_template('test_results.html', 
                         test_attempt=test_attempt,
                         user_answers=user_answers)

@app.route('/admin/import-questions', methods=['GET', 'POST'])
@login_required
def import_questions():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected.', 'error')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(request.url)

        if file and file.filename.endswith('.csv'):
            test_package_id = request.form.get('test_package_id')

            if not test_package_id:
                flash('Please select a test package.', 'error')
                return redirect(request.url)

            try:
                result = import_questions_from_csv(file, int(test_package_id))
                flash(f'Successfully imported {result["imported"]} questions. Skipped {result["skipped"]} duplicates.', 'success')
            except Exception as e:
                flash(f'Error importing questions: {str(e)}', 'error')
        else:
            flash('Please upload a CSV file.', 'error')

    test_packages = TestPackage.query.all()
    return render_template('admin/import_questions.html', test_packages=test_packages)

@app.route('/admin/create-package', methods=['POST'])
@login_required
def create_package():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    title = request.form.get('title')
    description = request.form.get('description')
    price = request.form.get('price')
    domain = request.form.get('domain')

    if not all([title, description, price, domain]):
        flash('All fields are required.', 'error')
        return redirect(url_for('import_questions'))

    try:
        package = TestPackage(
            title=title,
            description=description,
            price=float(price),
            domain=domain
        )
        db.session.add(package)
        db.session.commit()

        # Create package-specific image folder
        safe_package_name = re.sub(r'[^a-zA-Z0-9\-_]', '_', title.lower().replace(' ', '_'))
        package_image_dir = os.path.join('static', 'images', 'questions', safe_package_name)
        os.makedirs(package_image_dir, exist_ok=True)

        # Create a README file in the package folder
        readme_path = os.path.join(package_image_dir, 'README.md')
        with open(readme_path, 'w') as f:
            f.write(f"# Images for {title}\n\n")
            f.write(f"This folder contains images used in questions for the '{title}' test package.\n\n")
            f.write("## How to Use Images\n\n")
            f.write("1. Upload your image files (PNG, JPG, JPEG, GIF, SVG) to this folder\n")
            f.write("2. In your CSV file or when creating questions, reference images using this format:\n")
            f.write("   ```\n   IMAGE: filename.png\n   ```\n\n")
            f.write("## Supported Formats\n")
            f.write("- PNG\n- JPG/JPEG\n- GIF\n- SVG\n\n")
            f.write("## Notes\n")
            f.write("- Images will be automatically resized to fit properly in the question interface\n")
            f.write("- Make sure filenames match exactly (case-sensitive)\n")
            f.write("- Use descriptive filenames for easier management\n")
            f.write("- Images will be automatically resized to fit properly in the question interface\n")
            f.write("- Make sure filenames match exactly (case-sensitive)\n")
            f.write("- Use descriptive filenames for easier management\n")
            f.write("- Use descriptive filenames for easier management\n")
            f.write("- Use descriptive filenames for easier management\n")
            f.write("- Use descriptive filenames for easier management\n")
            f.write("- Use descriptive filenames for easier management\n")

        flash('Test package created successfully with dedicated image folder.', 'success')
    except Exception as e:
        flash(f'Error creating package: {str(e)}', 'error')

    return redirect(url_for('import_questions'))

@app.route('/admin/manage-questions/<int:package_id>')
@login_required
def manage_questions(package_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    package = TestPackage.query.get_or_404(package_id)
    questions = Question.query.filter_by(test_package_id=package_id).all()
    return render_template('admin/manage_questions.html', package=package, questions=questions)

@app.route('/admin/edit-question/<int:question_id>', methods=['GET', 'POST'])
@login_required
def edit_question(question_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    question = Question.query.get_or_404(question_id)

    if request.method == 'POST':
        try:
            # Update question details
            question_text = request.form.get('question_text', '')
            domain = request.form.get('domain', '')
            overall_explanation = request.form.get('overall_explanation', '')

            # Get package title for image processing
            package_title = question.test_package.title

            if question_text:
                question.question_text = process_text_with_images(question_text, package_title)
            if domain:
                question.domain = domain
            if overall_explanation:
                question.overall_explanation = process_text_with_images(overall_explanation, package_title)

            # Update answer options
            for option in question.answer_options:
                option_text = request.form.get(f'option_text_{option.id}')
                option_explanation = request.form.get(f'option_explanation_{option.id}', '')
                option_correct = request.form.get(f'option_correct_{option.id}') == 'on'

                if option_text:
                    option.option_text = process_text_with_images(option_text, package_title)
                    option.explanation = process_text_with_images(option_explanation, package_title) if option_explanation else ''
                    option.is_correct = option_correct

            db.session.commit()
            flash('Question updated successfully!', 'success')
            return redirect(url_for('manage_questions', package_id=question.test_package_id))

        except Exception as e:
            db.session.rollback()
            flash(f'Error updating question: {str(e)}', 'error')
            return render_template('admin/edit_question.html', question=question)

    return render_template('admin/edit_question.html', question=question)

@app.route('/admin/add-question/<int:package_id>', methods=['GET', 'POST'])
@login_required 
def add_question(package_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    package = TestPackage.query.get_or_404(package_id)

    if request.method == 'POST':
        question = Question(
            test_package_id=package_id,
            question_text=process_text_with_images(request.form.get('question_text'), package.title),
            question_type=request.form.get('question_type', 'multiple-choice'),
            domain=request.form.get('domain'),
            overall_explanation=process_text_with_images(request.form.get('overall_explanation'), package.title)
        )
        db.session.add(question)
        db.session.flush()

        # Add answer options
        option_count = int(request.form.get('option_count', 4))
        for i in range(1, option_count + 1):
            option_text = request.form.get(f'option_text_{i}')
            option_explanation = request.form.get(f'option_explanation_{i}')
            option_correct = request.form.get(f'option_correct_{i}') == 'on'

            if option_text:
                option = AnswerOption(
                    question_id=question.id,
                    option_text=process_text_with_images(option_text, package.title),
                    explanation=process_text_with_images(option_explanation, package.title) if option_explanation else '',
                    is_correct=option_correct,
                    option_order=i
                )
                db.session.add(option)

        db.session.commit()
        flash('Question added successfully!', 'success')
        return redirect(url_for('manage_questions', package_id=package_id))

    return render_template('admin/add_question.html', package=package)

@app.route('/admin/delete-question/<int:question_id>', methods=['POST'])
@login_required
def delete_question(question_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    question = Question.query.get_or_404(question_id)
    package_id = question.test_package_id

    db.session.delete(question)
    db.session.commit()

    flash('Question deleted successfully!', 'success')
    return redirect(url_for('manage_questions', package_id=package_id))

@app.route('/admin/packages')
@login_required
def admin_packages():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    packages = TestPackage.query.all()
    return render_template('admin/packages.html', packages=packages)

@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/toggle-admin/<int:user_id>', methods=['POST'])
@login_required
def toggle_admin(user_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)

    # Prevent removing admin from the environment-specified admin
    admin_email = os.environ.get('ADMIN_EMAIL')
    if admin_email and user.email == admin_email and user.is_admin:
        flash('Cannot remove admin privileges from the environment-specified admin user.', 'error')
        return redirect(url_for('admin_users'))

    # Prevent user from removing their own admin privileges
    if user.id == current_user.id:
        flash('You cannot remove your own admin privileges.', 'error')
        return redirect(url_for('admin_users'))

    user.is_admin = not user.is_admin
    db.session.commit()

    action = 'granted' if user.is_admin else 'removed'
    flash(f'Admin privileges {action} for {user.email}.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/upload-image/<int:package_id>', methods=['POST'])
@login_required
def upload_image(package_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))

    package = TestPackage.query.get_or_404(package_id)

    if 'image' not in request.files:
        flash('No image file selected.', 'error')
        return redirect(request.referrer)

    file = request.files['image']
    if file.filename == '':
        flash('No image file selected.', 'error')
        return redirect(request.referrer)

    if file and allowed_file(file.filename):
        # Check file size (limit to 5MB)
        file.seek(0, 2)  # Seek to end of file
        file_size = file.tell()
        file.seek(0)  # Reset file pointer

        if file_size > 5 * 1024 * 1024:  # 5MB limit
            flash('File size too large. Maximum size is 5MB.', 'error')
            return redirect(request.referrer)

        filename = secure_filename(file.filename)
        safe_package_name = re.sub(r'[^a-zA-Z0-9\-_]', '_', package.title.lower().replace(' ', '_'))
        package_image_dir = os.path.join('static', 'images', 'questions', safe_package_name)
        os.makedirs(package_image_dir, exist_ok=True)

        file_path = os.path.join(package_image_dir, filename)
        file.save(file_path)

        flash(f'Image {filename} uploaded successfully!', 'success')
    else:
        flash('Invalid file type. Please upload PNG, JPG, JPEG, GIF, or SVG files.', 'error')

    return redirect(request.referrer)

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS and \
           len(filename) < 255

# These routes are handled in admin_coupon_routes.py

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500