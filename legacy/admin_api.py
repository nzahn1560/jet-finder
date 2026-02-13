"""
Admin API Blueprint
Endpoints for listing approval, user management, and admin dashboard
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps
import os
from datetime import datetime

admin_api_bp = Blueprint('admin_api', __name__)

def require_admin(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id') or not session.get('is_admin'):
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def get_db_connection():
    """Get database connection (PostgreSQL or SQLite)"""
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(database_url)
        conn.row_factory = psycopg2.extras.RealDictRowFactory
        return conn, 'postgres'
    else:
        import sqlite3
        from pathlib import Path
        db_path = Path(__file__).parent / 'instance' / 'jet_finder.db'
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn, 'sqlite'

@admin_api_bp.route('/health', methods=['GET'])
def health_check():
    """Admin API health check"""
    return jsonify({
        'status': 'healthy',
        'service': 'admin-api',
        'version': '1.0.0'
    })

@admin_api_bp.route('/pending-listings', methods=['GET'])
@require_admin
def get_pending_listings():
    """Get all listings pending approval"""
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                l.*,
                u.email as seller_email,
                u.first_name as seller_first_name,
                u.last_name as seller_last_name
            FROM listings l
            JOIN users u ON l.user_id = u.id
            WHERE l.status = 'pending'
            ORDER BY l.created_at DESC
        """)
        
        listings = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'count': len(listings),
            'listings': listings
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/listing/<int:listing_id>/approve', methods=['POST'])
@require_admin
def approve_listing(listing_id):
    """Approve a pending listing"""
    try:
        data = request.json or {}
        admin_notes = data.get('notes', '')
        
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        admin_id = session.get('user_id')
        
        if db_type == 'postgres':
            cursor.execute("""
                UPDATE listings
                SET status = 'approved',
                    approved_at = NOW(),
                    approved_by = %s,
                    admin_notes = %s,
                    updated_at = NOW()
                WHERE id = %s
                RETURNING id, aircraft_name
            """, (admin_id, admin_notes, listing_id))
        else:
            cursor.execute("""
                UPDATE listings
                SET status = 'approved',
                    approved_at = datetime('now'),
                    approved_by = ?,
                    admin_notes = ?,
                    updated_at = datetime('now')
                WHERE id = ?
            """, (admin_id, admin_notes, listing_id))
        
        conn.commit()
        
        # Get updated listing
        cursor.execute("SELECT * FROM listings WHERE id = ?", (listing_id,))
        listing = dict(cursor.fetchone())
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Listing approved: {listing["aircraft_name"]}',
            'listing': listing
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/listing/<int:listing_id>/reject', methods=['POST'])
@require_admin
def reject_listing(listing_id):
    """Reject a pending listing"""
    try:
        data = request.json or {}
        admin_notes = data.get('notes', '')
        reason = data.get('reason', 'Does not meet listing requirements')
        
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        admin_id = session.get('user_id')
        full_notes = f"REJECTED: {reason}. {admin_notes}"
        
        if db_type == 'postgres':
            cursor.execute("""
                UPDATE listings
                SET status = 'rejected',
                    approved_by = %s,
                    admin_notes = %s,
                    updated_at = NOW()
                WHERE id = %s
                RETURNING id, aircraft_name
            """, (admin_id, full_notes, listing_id))
        else:
            cursor.execute("""
                UPDATE listings
                SET status = 'rejected',
                    approved_by = ?,
                    admin_notes = ?,
                    updated_at = datetime('now')
                WHERE id = ?
            """, (admin_id, full_notes, listing_id))
        
        conn.commit()
        
        cursor.execute("SELECT * FROM listings WHERE id = ?", (listing_id,))
        listing = dict(cursor.fetchone())
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Listing rejected: {listing["aircraft_name"]}',
            'listing': listing
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/dashboard-stats', methods=['GET'])
@require_admin
def get_dashboard_stats():
    """Get admin dashboard statistics"""
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Total listings by status
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM listings
            GROUP BY status
        """)
        stats['listings_by_status'] = {row['status']: row['count'] for row in cursor.fetchall()}
        
        # Total users
        cursor.execute("SELECT COUNT(*) as count FROM users")
        stats['total_users'] = cursor.fetchone()['count']
        
        # Pending approvals
        cursor.execute("SELECT COUNT(*) as count FROM listings WHERE status = 'pending'")
        stats['pending_approvals'] = cursor.fetchone()['count']
        
        # Total inquiries
        cursor.execute("SELECT COUNT(*) as count FROM inquiries")
        stats['total_inquiries'] = cursor.fetchone()['count']
        
        # Recent activity
        cursor.execute("""
            SELECT 
                l.id,
                l.aircraft_name,
                l.status,
                l.created_at,
                u.email as seller_email
            FROM listings l
            JOIN users u ON l.user_id = u.id
            ORDER BY l.created_at DESC
            LIMIT 10
        """)
        stats['recent_listings'] = [dict(row) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/users', methods=['GET'])
@require_admin
def get_users():
    """Get all users (with pagination)"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        offset = (page - 1) * per_page
        
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id, email, first_name, last_name, company, user_type,
                is_admin, is_verified_seller, total_listings, created_at
            FROM users
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (per_page, offset))
        
        users = [dict(row) for row in cursor.fetchall()]
        
        cursor.execute("SELECT COUNT(*) as count FROM users")
        total = cursor.fetchone()['count']
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'users': users,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_api_bp.route('/user/<int:user_id>/verify-seller', methods=['POST'])
@require_admin
def verify_seller(user_id):
    """Verify a seller account"""
    try:
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        
        if db_type == 'postgres':
            cursor.execute("""
                UPDATE users
                SET is_verified_seller = TRUE,
                    verification_status = 'verified',
                    updated_at = NOW()
                WHERE id = %s
                RETURNING email
            """, (user_id,))
        else:
            cursor.execute("""
                UPDATE users
                SET is_verified_seller = 1,
                    verification_status = 'verified',
                    updated_at = datetime('now')
                WHERE id = ?
            """, (user_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Seller verified successfully'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
