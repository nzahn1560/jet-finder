"""
Firebase Authentication Routes
Provides endpoints for Firebase Auth integration
"""
from flask import Blueprint, request, jsonify, make_response
from firebase_auth import (
    verify_firebase_token, 
    sync_firebase_user_to_postgres,
    get_current_firebase_user,
    require_firebase_auth
)
from models import SessionLocal, User
import os

firebase_auth_bp = Blueprint('firebase_auth', __name__, url_prefix='/api/firebase-auth')

@firebase_auth_bp.route('/verify', methods=['POST'])
def verify_token():
    """
    Verify Firebase ID token and sync user to PostgreSQL
    Called by frontend after Firebase sign-in
    """
    data = request.get_json()
    id_token = data.get('idToken')
    
    if not id_token:
        return jsonify({'error': 'ID token required'}), 400
    
    # Verify token
    decoded_token = verify_firebase_token(id_token)
    if not decoded_token:
        return jsonify({'error': 'Invalid or expired token'}), 401
    
    # Get user info from Firebase
    firebase_uid = decoded_token.get('uid')
    email = decoded_token.get('email')
    name = decoded_token.get('name')
    
    if not email:
        return jsonify({'error': 'Email not found in token'}), 400
    
    # Sync to PostgreSQL
    try:
        user = sync_firebase_user_to_postgres(firebase_uid, email, name)
        
        # Return user info
        response = make_response(jsonify({
            'message': 'Authentication successful',
            'user': user.to_dict(),
            'firebase_uid': firebase_uid
        }), 200)
        
        # Set cookie with Firebase ID token (optional, for cookie-based auth)
        response.set_cookie(
            'firebase_id_token',
            value=id_token,
            max_age=30 * 24 * 60 * 60,  # 30 days
            secure=os.environ.get('RAILWAY_ENVIRONMENT') == 'production',
            httponly=True,
            samesite='Lax',
            path='/'
        )
        
        return response
    except Exception as e:
        return jsonify({'error': f'Error syncing user: {str(e)}'}), 500

@firebase_auth_bp.route('/me', methods=['GET'])
@require_firebase_auth
def get_me():
    """Get current authenticated user"""
    user = request.current_user
    return jsonify({
        'user': user.to_dict()
    }), 200

@firebase_auth_bp.route('/logout', methods=['POST'])
def logout():
    """Log out (clear cookie)"""
    response = make_response(jsonify({
        'message': 'Logged out successfully'
    }), 200)
    
    response.set_cookie(
        'firebase_id_token',
        value='',
        max_age=0,
        path='/'
    )
    
    return response
