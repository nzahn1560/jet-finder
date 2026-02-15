/**
 * Firebase Authentication Helper
 * Handles Firebase Auth integration for frontend
 */

// Firebase configuration - SET THESE VALUES
const firebaseConfig = {
  apiKey: window.FIREBASE_API_KEY || "YOUR_API_KEY",
  authDomain: window.FIREBASE_AUTH_DOMAIN || "YOUR_PROJECT.firebaseapp.com",
  projectId: window.FIREBASE_PROJECT_ID || "YOUR_PROJECT_ID",
  storageBucket: window.FIREBASE_STORAGE_BUCKET || "YOUR_PROJECT.appspot.com",
  messagingSenderId: window.FIREBASE_MESSAGING_SENDER_ID || "YOUR_SENDER_ID",
  appId: window.FIREBASE_APP_ID || "YOUR_APP_ID"
};

// Initialize Firebase (if not already initialized)
let auth = null;
if (typeof firebase !== 'undefined') {
  if (!firebase.apps.length) {
    firebase.initializeApp(firebaseConfig);
  }
  auth = firebase.auth();
}

/**
 * Sign up with email and password
 */
async function signUpWithEmail(email, password) {
  if (!auth) {
    throw new Error('Firebase Auth not initialized');
  }
  
  try {
    const userCredential = await auth.createUserWithEmailAndPassword(email, password);
    const idToken = await userCredential.user.getIdToken();
    
    // Verify token with backend and sync to PostgreSQL
    const response = await fetch('/api/firebase-auth/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ idToken })
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Authentication failed');
    }
    
    const data = await response.json();
    return data.user;
  } catch (error) {
    console.error('Sign up error:', error);
    throw error;
  }
}

/**
 * Sign in with email and password
 */
async function signInWithEmail(email, password) {
  if (!auth) {
    throw new Error('Firebase Auth not initialized');
  }
  
  try {
    const userCredential = await auth.signInWithEmailAndPassword(email, password);
    const idToken = await userCredential.user.getIdToken();
    
    // Verify token with backend and sync to PostgreSQL
    const response = await fetch('/api/firebase-auth/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ idToken })
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Authentication failed');
    }
    
    const data = await response.json();
    return data.user;
  } catch (error) {
    console.error('Sign in error:', error);
    throw error;
  }
}

/**
 * Sign in with Google
 */
async function signInWithGoogle() {
  if (!auth) {
    throw new Error('Firebase Auth not initialized');
  }
  
  try {
    const provider = new firebase.auth.GoogleAuthProvider();
    const result = await auth.signInWithPopup(provider);
    const idToken = await result.user.getIdToken();
    
    // Verify token with backend and sync to PostgreSQL
    const response = await fetch('/api/firebase-auth/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ idToken })
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Authentication failed');
    }
    
    const data = await response.json();
    return data.user;
  } catch (error) {
    console.error('Google sign in error:', error);
    throw error;
  }
}

/**
 * Sign out
 */
async function signOut() {
  if (!auth) {
    return;
  }
  
  try {
    await auth.signOut();
    
    // Clear backend cookie
    await fetch('/api/firebase-auth/logout', {
      method: 'POST',
      credentials: 'include'
    });
    
    window.location.href = '/login';
  } catch (error) {
    console.error('Sign out error:', error);
  }
}

/**
 * Get current user
 */
async function getCurrentUser() {
  if (!auth) {
    return null;
  }
  
  try {
    const user = auth.currentUser;
    if (!user) {
      return null;
    }
    
    // Get fresh token and verify with backend
    const idToken = await user.getIdToken();
    const response = await fetch('/api/firebase-auth/me', {
      headers: {
        'Authorization': `Bearer ${idToken}`
      },
      credentials: 'include'
    });
    
    if (!response.ok) {
      return null;
    }
    
    const data = await response.json();
    return data.user;
  } catch (error) {
    console.error('Get current user error:', error);
    return null;
  }
}

/**
 * Check auth state and redirect if needed
 */
function checkAuthState() {
  if (!auth) {
    return;
  }
  
  auth.onAuthStateChanged(async (firebaseUser) => {
    if (firebaseUser) {
      // User is signed in - verify with backend
      try {
        const idToken = await firebaseUser.getIdToken();
        await fetch('/api/firebase-auth/verify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ idToken })
        });
      } catch (error) {
        console.error('Auth state verification error:', error);
      }
    } else {
      // User is signed out
      const currentPath = window.location.pathname;
      if (currentPath !== '/login' && currentPath !== '/signup' && currentPath !== '/') {
        window.location.href = '/login';
      }
    }
  });
}

// Auto-check auth state on page load
if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    checkAuthState();
  });
}
