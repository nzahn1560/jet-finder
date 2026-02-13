from flask import Blueprint, render_template, request, jsonify

# Create the blueprint
stripe_integration = Blueprint('stripe_integration', __name__)


@stripe_integration.route('/payment', methods=['GET', 'POST'])
def payment():
    """Handle payment processing"""
    if request.method == 'POST':
        # Mock payment processing logic
        # In a real app, this would integrate with Stripe API

        # Get payment details from form
        amount = request.form.get('amount', 0)
        description = request.form.get('description', 'Aircraft purchase')

        # Mock successful payment
        success = True

        if success:
            return jsonify({
                'success': True,
                'message': f'Payment of ${amount} processed successfully for {description}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Payment processing failed'
            })

    # GET request - show payment form
    return render_template('payment.html')


@stripe_integration.route('/checkout', methods=['GET'])
def checkout():
    """Checkout page with payment options"""
    # Get product details from query parameters
    product = request.args.get('product', 'Unknown')
    amount = float(request.args.get('amount', 0))

    return render_template(
        'checkout.html',
        product=product,
        amount=amount
    )
