"""
Listings API - CRUD with ownership and admin review
"""
from flask import Blueprint, request, jsonify
from auth import require_auth, require_admin, get_current_user
from models import SessionLocal, Listing, ListingStatus, ListingMedia, MediaType, Payment, PaymentStatus
from sqlalchemy import or_

listings_bp = Blueprint('listings', __name__, url_prefix='/api/listings')

@listings_bp.route('', methods=['GET'])
def get_listings():
    """Get public listings (only approved/active) OR user's own listings"""
    db = SessionLocal()
    try:
        current_user = get_current_user()
        status_filter = request.args.get('status', 'active')
        
        # Build query
        query = db.query(Listing)
        
        # If not logged in, only show active/approved
        if not current_user:
            query = query.filter(or_(
                Listing.status == ListingStatus.ACTIVE,
                Listing.status == ListingStatus.APPROVED
            ))
        else:
            # If specific status requested, filter by it (for dashboard)
            if status_filter and status_filter != 'all':
                try:
                    status_enum = ListingStatus[status_filter.upper()]
                    query = query.filter(Listing.status == status_enum)
                except KeyError:
                    pass
        
        listings = query.order_by(Listing.created_at.desc()).all()
        
        return jsonify({
            'listings': [listing.to_dict() for listing in listings]
        }), 200
        
    finally:
        db.close()

@listings_bp.route('/<int:listing_id>', methods=['GET'])
def get_listing(listing_id):
    """Get single listing (if public or owner/admin)"""
    db = SessionLocal()
    try:
        listing = db.query(Listing).filter(Listing.id == listing_id).first()
        
        if not listing:
            return jsonify({'error': 'Listing not found'}), 404
        
        current_user = get_current_user()
        
        # Check if user can view this listing
        is_public = listing.status in [ListingStatus.ACTIVE, ListingStatus.APPROVED]
        is_owner = current_user and listing.owner_user_id == current_user.id
        is_admin = current_user and current_user.is_admin
        
        if not (is_public or is_owner or is_admin):
            return jsonify({'error': 'Access denied'}), 403
        
        return jsonify({
            'listing': listing.to_dict(include_owner=is_admin)
        }), 200
        
    finally:
        db.close()

@listings_bp.route('', methods=['POST'])
@require_auth
def create_listing():
    """Create new listing (owner_user_id = current user)"""
    data = request.get_json()
    user = request.current_user
    
    db = SessionLocal()
    try:
        # Create listing
        listing = Listing(
            owner_user_id=user.id,
            status=ListingStatus.UNPAID,  # Start as unpaid
            title=data.get('title', ''),
            aircraft_type=data.get('aircraft_type', ''),
            manufacturer=data.get('manufacturer'),
            model=data.get('model'),
            year=data.get('year'),
            price=data.get('price'),
            location=data.get('location'),
            description=data.get('description'),
            interior_year=data.get('interior_year'),
            exterior_paint_year=data.get('exterior_paint_year'),
            avionics_value_estimate=data.get('avionics_value_estimate'),
            airframe_time=data.get('airframe_time'),
            engine1_time=data.get('engine1_time'),
            engine1_tbo=data.get('engine1_tbo'),
            engine2_time=data.get('engine2_time'),
            engine2_tbo=data.get('engine2_tbo'),
            contact_email=data.get('contact_email', user.email),
            contact_phone=data.get('contact_phone')
        )
        
        db.add(listing)
        db.commit()
        db.refresh(listing)
        
        # Add media if provided
        media_urls = data.get('media', [])
        for idx, media_item in enumerate(media_urls):
            media = ListingMedia(
                listing_id=listing.id,
                media_type=MediaType[media_item.get('type', 'PHOTO').upper()],
                url=media_item.get('url'),
                sort_order=idx
            )
            db.add(media)
        
        db.commit()
        db.refresh(listing)
        
        return jsonify({
            'message': 'Listing created successfully',
            'listing': listing.to_dict()
        }), 201
        
    except Exception as e:
        db.rollback()
        print(f"Create listing error: {e}")
        return jsonify({'error': 'An error occurred creating the listing'}), 500
    finally:
        db.close()

@listings_bp.route('/<int:listing_id>', methods=['PATCH'])
@require_auth
def update_listing(listing_id):
    """Update listing (only if owner and status allows editing)"""
    data = request.get_json()
    user = request.current_user
    
    db = SessionLocal()
    try:
        listing = db.query(Listing).filter(Listing.id == listing_id).first()
        
        if not listing:
            return jsonify({'error': 'Listing not found'}), 404
        
        # Check ownership
        if listing.owner_user_id != user.id:
            return jsonify({'error': 'You do not own this listing'}), 403
        
        # Check if status allows editing
        editable_statuses = [ListingStatus.DRAFT, ListingStatus.UNPAID, ListingStatus.PENDING]
        if listing.status not in editable_statuses:
            return jsonify({'error': f'Cannot edit listing with status: {listing.status.value}'}), 400
        
        # Update fields
        updateable_fields = [
            'title', 'aircraft_type', 'manufacturer', 'model', 'year', 'price',
            'location', 'description', 'interior_year', 'exterior_paint_year',
            'avionics_value_estimate', 'airframe_time', 'engine1_time', 'engine1_tbo',
            'engine2_time', 'engine2_tbo', 'contact_email', 'contact_phone'
        ]
        
        for field in updateable_fields:
            if field in data:
                setattr(listing, field, data[field])
        
        db.commit()
        db.refresh(listing)
        
        return jsonify({
            'message': 'Listing updated successfully',
            'listing': listing.to_dict()
        }), 200
        
    except Exception as e:
        db.rollback()
        print(f"Update listing error: {e}")
        return jsonify({'error': 'An error occurred updating the listing'}), 500
    finally:
        db.close()

@listings_bp.route('/<int:listing_id>/submit', methods=['POST'])
@require_auth
def submit_listing(listing_id):
    """Submit listing for review (requires payment first)"""
    user = request.current_user
    
    db = SessionLocal()
    try:
        listing = db.query(Listing).filter(Listing.id == listing_id).first()
        
        if not listing:
            return jsonify({'error': 'Listing not found'}), 404
        
        # Check ownership
        if listing.owner_user_id != user.id:
            return jsonify({'error': 'You do not own this listing'}), 403
        
        # Check if payment exists and is paid
        payment = db.query(Payment).filter(
            Payment.listing_id == listing_id,
            Payment.status == PaymentStatus.PAID
        ).first()
        
        if not payment:
            return jsonify({'error': 'Payment required before submission'}), 400
        
        # Move to pending review
        listing.status = ListingStatus.PENDING
        db.commit()
        
        return jsonify({
            'message': 'Listing submitted for review',
            'listing': listing.to_dict()
        }), 200
        
    except Exception as e:
        db.rollback()
        print(f"Submit listing error: {e}")
        return jsonify({'error': 'An error occurred submitting the listing'}), 500
    finally:
        db.close()

# User dashboard route
@listings_bp.route('/me/listings', methods=['GET'])
@require_auth
def get_my_listings():
    """Get current user's listings"""
    user = request.current_user
    
    db = SessionLocal()
    try:
        listings = db.query(Listing).filter(
            Listing.owner_user_id == user.id
        ).order_by(Listing.created_at.desc()).all()
        
        return jsonify({
            'listings': [listing.to_dict() for listing in listings]
        }), 200
        
    finally:
        db.close()

@listings_bp.route('/<int:listing_id>', methods=['DELETE'])
@require_auth
def delete_listing(listing_id):
    """Delete listing (only if owner and status allows deletion)"""
    user = request.current_user
    
    db = SessionLocal()
    try:
        listing = db.query(Listing).filter(Listing.id == listing_id).first()
        
        if not listing:
            return jsonify({'error': 'Listing not found'}), 404
        
        # Check ownership
        if listing.owner_user_id != user.id:
            return jsonify({'error': 'You do not own this listing'}), 403
        
        # Check if status allows deletion (only draft or unpaid)
        deletable_statuses = [ListingStatus.DRAFT, ListingStatus.UNPAID]
        if listing.status not in deletable_statuses:
            return jsonify({'error': f'Cannot delete listing with status: {listing.status.value}'}), 400
        
        # Delete listing (cascade will delete media and payments)
        db.delete(listing)
        db.commit()
        
        return jsonify({
            'message': 'Listing deleted successfully'
        }), 200
        
    except Exception as e:
        db.rollback()
        print(f"Delete listing error: {e}")
        return jsonify({'error': 'An error occurred deleting the listing'}), 500
    finally:
        db.close()

# Admin routes
@listings_bp.route('/admin/pending', methods=['GET'])
@require_admin
def get_pending_listings():
    """Get all pending listings (admin only)"""
    db = SessionLocal()
    try:
        listings = db.query(Listing).filter(
            Listing.status == ListingStatus.PENDING
        ).order_by(Listing.created_at.asc()).all()
        
        return jsonify({
            'listings': [listing.to_dict(include_owner=True) for listing in listings]
        }), 200
        
    finally:
        db.close()

@listings_bp.route('/admin/<int:listing_id>/approve', methods=['POST'])
@require_admin
def approve_listing(listing_id):
    """Approve a listing (admin only)"""
    db = SessionLocal()
    try:
        listing = db.query(Listing).filter(Listing.id == listing_id).first()
        
        if not listing:
            return jsonify({'error': 'Listing not found'}), 404
        
        if listing.status != ListingStatus.PENDING:
            return jsonify({'error': 'Only pending listings can be approved'}), 400
        
        # Approve listing
        listing.status = ListingStatus.ACTIVE
        db.commit()
        
        return jsonify({
            'message': 'Listing approved',
            'listing': listing.to_dict()
        }), 200
        
    except Exception as e:
        db.rollback()
        print(f"Approve listing error: {e}")
        return jsonify({'error': 'An error occurred approving the listing'}), 500
    finally:
        db.close()

@listings_bp.route('/admin/<int:listing_id>/reject', methods=['POST'])
@require_admin
def reject_listing(listing_id):
    """Reject a listing (admin only)"""
    data = request.get_json()
    reason = data.get('reason', 'Not specified')
    
    db = SessionLocal()
    try:
        listing = db.query(Listing).filter(Listing.id == listing_id).first()
        
        if not listing:
            return jsonify({'error': 'Listing not found'}), 404
        
        if listing.status != ListingStatus.PENDING:
            return jsonify({'error': 'Only pending listings can be rejected'}), 400
        
        # Reject listing
        listing.status = ListingStatus.REJECTED
        listing.rejected_reason = reason
        db.commit()
        
        return jsonify({
            'message': 'Listing rejected',
            'listing': listing.to_dict()
        }), 200
        
    except Exception as e:
        db.rollback()
        print(f"Reject listing error: {e}")
        return jsonify({'error': 'An error occurred rejecting the listing'}), 500
    finally:
        db.close()
