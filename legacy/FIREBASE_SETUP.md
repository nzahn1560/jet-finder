# Firebase Authentication Setup

## Overview

Firebase Authentication has been integrated into the Jet Finder application. This provides:
- Email/password authentication
- Google Sign-In
- Secure token-based authentication
- Automatic user sync to PostgreSQL

## Architecture

**Hybrid Approach:**
- **Firebase Auth** - Handles authentication (email/password, Google, etc.)
- **PostgreSQL** - Stores user data and listings (syncs from Firebase)

## Setup Instructions

### 1. Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or select existing
3. Enable **Authentication** → **Sign-in method**
4. Enable:
   - **Email/Password**
   - **Google** (optional)

### 2. Get Firebase Credentials

1. Firebase Console → Project Settings → Service Accounts
2. Click **Generate New Private Key**
3. Download the JSON file

### 3. Configure Railway Environment Variables

In Railway Dashboard → Your Service → Variables:

**Option A: JSON String (Recommended for Railway)**
```
FIREBASE_CREDENTIALS_JSON={"type":"service_account","project_id":"your-project",...}
```
(Paste the entire JSON file contents as a single-line string)

**Option B: File Path (If using Railway volumes)**
```
FIREBASE_CREDENTIALS_PATH=/path/to/serviceAccountKey.json
```

### 4. Frontend Configuration

Add Firebase config to your frontend templates. Create `legacy/static/js/firebase-config.js`:

```javascript
// Firebase configuration
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_PROJECT.firebaseapp.com",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_PROJECT.appspot.com",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_APP_ID"
};

// Initialize Firebase
firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();
```

Get these values from: Firebase Console → Project Settings → General → Your apps

## API Endpoints

### `POST /api/firebase-auth/verify`
Verify Firebase ID token and sync user to PostgreSQL.

**Request:**
```json
{
  "idToken": "firebase-id-token-here"
}
```

**Response:**
```json
{
  "message": "Authentication successful",
  "user": {
    "id": "firebase-uid",
    "email": "user@example.com",
    ...
  },
  "firebase_uid": "firebase-uid"
}
```

**Sets cookie:** `firebase_id_token=<token>`

### `GET /api/firebase-auth/me`
Get current authenticated user (requires Firebase token).

**Headers:**
```
Authorization: Bearer <firebase-id-token>
```

OR

**Cookie:** `firebase_id_token=<token>`

**Response:**
```json
{
  "user": {
    "id": "firebase-uid",
    "email": "user@example.com",
    ...
  }
}
```

### `POST /api/firebase-auth/logout`
Log out (clears cookie).

## Frontend Integration

### Install Firebase SDK

Add to your HTML templates:
```html
<!-- Firebase SDK -->
<script src="https://www.gstatic.com/firebasejs/10.7.1/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/10.7.1/firebase-auth-compat.js"></script>
<script src="/static/js/firebase-config.js"></script>
```

### Sign Up with Email/Password

```javascript
firebase.auth().createUserWithEmailAndPassword(email, password)
  .then((userCredential) => {
    const user = userCredential.user;
    return user.getIdToken();
  })
  .then((idToken) => {
    // Send token to backend
    return fetch('/api/firebase-auth/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ idToken })
    });
  })
  .then(() => {
    window.location.href = '/dashboard';
  });
```

### Sign In with Email/Password

```javascript
firebase.auth().signInWithEmailAndPassword(email, password)
  .then((userCredential) => {
    return userCredential.user.getIdToken();
  })
  .then((idToken) => {
    return fetch('/api/firebase-auth/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ idToken })
    });
  })
  .then(() => {
    window.location.href = '/dashboard';
  });
```

### Google Sign-In

```javascript
const provider = new firebase.auth.GoogleAuthProvider();
firebase.auth().signInWithPopup(provider)
  .then((result) => {
    return result.user.getIdToken();
  })
  .then((idToken) => {
    return fetch('/api/firebase-auth/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ idToken })
    });
  })
  .then(() => {
    window.location.href = '/dashboard';
  });
```

### Check Auth State

```javascript
firebase.auth().onAuthStateChanged((user) => {
  if (user) {
    // User is signed in
    user.getIdToken().then((idToken) => {
      // Verify with backend
      fetch('/api/firebase-auth/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ idToken })
      });
    });
  } else {
    // User is signed out
    window.location.href = '/login';
  }
});
```

## User Sync

When a user authenticates with Firebase:
1. Firebase ID token is verified
2. User info (UID, email, name) is extracted
3. User is synced to PostgreSQL `users` table:
   - Creates user if doesn't exist
   - Updates user ID to match Firebase UID
   - Stores email and optional name

## Migration from Cookie-Based Auth

The system supports both authentication methods:
- **Firebase Auth** - New endpoints under `/api/firebase-auth/*`
- **Cookie-Based Auth** - Existing endpoints under `/api/auth/*`

You can:
1. Keep both systems running
2. Gradually migrate frontend to Firebase
3. Eventually deprecate cookie-based auth

## Security Notes

✅ **Token Verification** - All Firebase tokens are verified server-side  
✅ **HTTPS Only** - Cookies are secure in production  
✅ **HttpOnly Cookies** - Prevents XSS attacks  
✅ **Token Expiration** - Firebase tokens expire automatically  
✅ **User Sync** - Firebase users are synced to PostgreSQL for data integrity  

## Troubleshooting

### Firebase Not Initialized
- Check `FIREBASE_CREDENTIALS_JSON` or `FIREBASE_CREDENTIALS_PATH` is set
- Verify JSON credentials are valid
- Check Railway logs for initialization errors

### Token Verification Fails
- Ensure Firebase project ID matches credentials
- Check token hasn't expired
- Verify Firebase Auth is enabled in Firebase Console

### User Not Syncing
- Check PostgreSQL connection
- Verify `users` table exists
- Check Railway logs for sync errors
