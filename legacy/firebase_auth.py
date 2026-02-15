"""
Firebase Authentication Integration
Handles Firebase Auth token verification and user sync with PostgreSQL
"""
import firebase_admin
from firebase_admin import credentials, auth
from flask import request, jsonify
from functools import wraps
from models import SessionLocal, User
import os
import logging

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
firebase_app = None

def init_firebase():
    """Initialize Firebase Admin SDK"""
    global firebase_app
    
    if firebase_app:
        return firebase_app
    
    try:
        # Check for Firebase credentials
        firebase_creds_path = os.environ.get('FIREBASE_CREDENTIALS_PATH')
        firebase_creds_json = os.environ.get('FIREBASE_CREDENTIALS_JSON')
        
        if firebase_creds_path and os.path.exists(firebase_creds_path):
            # Load from file path
            cred = credentials.Certificate(firebase_creds_path)
            firebase_app = firebase_admin.initialize_app(cred)
            logger.info("✅ Firebase initialized from credentials file")
        elif firebase_creds_json:
            # Load from JSON string (Railway environment variable)
            import json
            cred_dict = json.loads(firebase_creds_json)
            cred = credentials.Certificate(cred_dict)
            firebase_app = firebase_admin.initialize_app(cred)
            logger.info("✅ Firebase initialized from JSON credentials")
        else:
            # Try default credentials (for local development with gcloud)
            try:
                firebase_app = firebase_admin.initialize_app()
                logger.info("✅ Firebase initialized with default credentials")
            except Exception as e:
                logger.warning(f"⚠️ Firebase not initialized: {e}")
                logger.warning("⚠️ Set FIREBASE_CREDENTIALS_PATH or FIREBASE_CREDENTIALS_JSON")
                return None
        
        return firebase_app
    except Exception as e:
        logger.error(f"❌ Firebase initialization failed: {e}")
        return None

# Initialize on import
init_firebase()

def verify_firebase_token(id_token):
    """
    Verify Firebase ID token and return decoded token
    Returns: dict with user info or None if invalid
    """
    if not firebase_app:
        logger.error("Firebase not initialized")
        return None
    
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except auth.InvalidIdTokenError:
        logger.warning("Invalid Firebase ID token")
        return None
    except auth.ExpiredIdTokenError:
        logger.warning("Expired Firebase ID token")
        return None
    except Exception as e:
        logger.error(f"Firebase token verification error: {e}")
        return None

def get_firebase_user_from_request():
    """
    Get Firebase user from request (Authorization header or cookie)
    Returns: (decoded_token, firebase_uid) or (None, None)
    """
    # Check Authorization header (Bearer token)
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        id_token = auth_header.split('Bearer ')[1]
        decoded_token = verify_firebase_token(id_token)
        if decoded_token:
            return decoded_token, decoded_token.get('uid')
    
    # Check cookie (for browser-based auth)
    id_token = request.cookies.get('firebase_id_token')
    if id_token:
        decoded_token = verify_firebase_token(id_token)
        if decoded_token:
            return decoded_token, decoded_token.get('uid')
    
    return None, None

def sync_firebase_user_to_postgres(firebase_uid, email, display_name=None):
    """
    Sync Firebase user to PostgreSQL users table
    Creates user if doesn't exist, updates if exists
    Returns: User object
    """
    db = SessionLocal()
    try:
        # Check if user exists by email
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # Create new user
            user = User(
                id=firebase_uid,  # Use Firebase UID as PostgreSQL ID
                email=email,
                password_hash='firebase_auth',  # Placeholder - Firebase handles auth
                is_admin=False
            )
            
            # Parse display name if provided
            if display_name:
                name_parts = display_name.split(' ', 1)
                user.first_name = name_parts[0] if len(name_parts) > 0 else None
                user.last_name = name_parts[1] if len(name_parts) > 1 else None
            
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"✅ Created PostgreSQL user for Firebase UID: {firebase_uid}")
        else:
            # Update existing user if needed
            if user.id != firebase_uid:
                # Update ID to match Firebase UID
                user.id = firebase_uid
                db.commit()
                logger.info(f"✅ Updated PostgreSQL user ID to match Firebase UID: {firebase_uid}")
        
        return user
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error syncing Firebase user to PostgreSQL: {e}")
        raise
    finally:
        db.close()

def get_current_firebase_user():
    """
    Get current user from Firebase token and sync to PostgreSQL
    Returns: User object or None
    """
    decoded_token, firebase_uid = get_firebase_user_from_request()
    
    if not decoded_token or not firebase_uid:
        return None
    
    # Get user info from Firebase
    email = decoded_token.get('email')
    name = decoded_token.get('name')
    
    if not email:
        return None
    
    # Sync to PostgreSQL
    try:
        user = sync_firebase_user_to_postgres(firebase_uid, email, name)
        return user
    except Exception as e:
        logger.error(f"❌ Error getting Firebase user: {e}")
        return None

def require_firebase_auth(f):
    """
    Decorator: require Firebase authentication
    Syncs Firebase user to PostgreSQL and attaches to request
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_firebase_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Attach user to request
        request.current_user = user
        return f(*args, **kwargs)
    
    return decorated_function
