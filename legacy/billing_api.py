"""
Billing API - Stripe integration for listing fees
"""
from flask import Blueprint, request, jsonify
from auth import require_auth
from models import SessionLocal, Listing, ListingStatus, Payment, PaymentStatus
import stripe
import os

billing_bp = Blueprint('billing', __name__, url_prefix='/api/billing')

# Stripe configuration
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
APP_BASE_URL = os.environ.get('APP_BASE_URL', 'http://localhost:5015')

# Listing fee (in cents)
LISTING_FEE_CENTS = 5000  # $50.00

@billing_bp.route('/listing-checkout', methods=['POST'])
@require_auth
def create_listing_checkout():
    """Create Stripe Checkout session for listing fee"""
    data = request.get_json()
    listing_id = data.get('listing_id')
    user = request.current_user
    
    if not listing_id:
        return jsonify({'error': 'listing_id is required'}), 400
    
    db = SessionLocal()
    try:
        # Get listing
        listing = db.query(Listing).filter(Listing.id == listing_id).first()
        
        if not listing:
            return jsonify({'error': 'Listing not found'}), 404
        
        # Check ownership
        if listing.owner_user_id != user.id:
            return jsonify({'error': 'You do not own this listing'}), 403
        
        # Check status
        if listing.status not in [ListingStatus.UNPAID, ListingStatus.DRAFT]:
            return jsonify({'error': f'Listing status must be unpaid or draft (currently: {listing.status.value})'}), 400
        
        # Check if payment already exists
        existing_payment = db.query(Payment).filter(
            Payment.listing_id == listing_id,
            Payment.status == PaymentStatus.PAID
        ).first()
        
        if existing_payment:
            return jsonify({'error': 'Listing fee already paid'}), 400
        
        # Create Stripe Checkout Session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': LISTING_FEE_CENTS,
                    'product_data': {
                        'name': 'Listing Fee',
                        'description': f'Listing fee for: {listing.title}'
                    }
                },
                'quantity': 1
            }],
            mode='payment',
            success_url=f'{APP_BASE_URL}/dashboard?payment=success&listing_id={listing_id}',
            cancel_url=f'{APP_BASE_URL}/dashboard?payment=cancelled&listing_id={listing_id}',
            metadata={
                'listing_id': str(listing_id),
                'owner_user_id': str(user.id)
            }
        )
        
        # Create payment record
        payment = Payment(
            listing_id=listing_id,
            stripe_checkout_session_id=checkout_session.id,
            amount_cents=LISTING_FEE_CENTS,
            currency='usd',
            status=PaymentStatus.CREATED
        )
        db.add(payment)
        db.commit()
        
        return jsonify({
            'checkout_url': checkout_session.url,
            'session_id': checkout_session.id
        }), 200
        
    except stripe.error.StripeError as e:
        print(f"Stripe error: {e}")
        return jsonify({'error': 'Payment processing error'}), 500
    except Exception as e:
        db.rollback()
        print(f"Checkout error: {e}")
        return jsonify({'error': 'An error occurred creating checkout session'}), 500
    finally:
        db.close()

@billing_bp.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    if not STRIPE_WEBHOOK_SECRET:
        print("⚠️ STRIPE_WEBHOOK_SECRET not configured!")
        return jsonify({'error': 'Webhook not configured'}), 500
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        print(f"Invalid payload: {e}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        print(f"Invalid signature: {e}")
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_complete(session)
    
    return jsonify({'status': 'success'}), 200

def handle_checkout_complete(session):
    """Handle successful checkout completion"""
    db = SessionLocal()
    try:
        session_id = session['id']
        payment_intent_id = session.get('payment_intent')
        listing_id = int(session['metadata'].get('listing_id'))
        
        # Find payment record
        payment = db.query(Payment).filter(
            Payment.stripe_checkout_session_id == session_id
        ).first()
        
        if not payment:
            print(f"⚠️ Payment record not found for session: {session_id}")
            return
        
        # Update payment status
        payment.status = PaymentStatus.PAID
        payment.stripe_payment_intent_id = payment_intent_id
        
        # Update listing status to pending (ready for admin review)
        listing = db.query(Listing).filter(Listing.id == listing_id).first()
        if listing and listing.status in [ListingStatus.UNPAID, ListingStatus.DRAFT]:
            listing.status = ListingStatus.PENDING
        
        db.commit()
        
        print(f"✅ Payment successful for listing {listing_id}")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error handling checkout complete: {e}")
    finally:
        db.close()
