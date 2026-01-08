// Supabase authentication integration for React frontend
// Install: npm install @supabase/supabase-js

import { createClient } from '@supabase/supabase-js';
import axios from 'axios';

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || '';
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || '';
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://jetfinder-api.YOUR_WORKER_SUBDOMAIN.workers.dev';

// Debug: Always log the API URL being used (critical for debugging production issues)
console.log('🌐 API Base URL:', API_BASE_URL);
if (!import.meta.env.VITE_API_URL) {
    console.error('❌ WARNING: VITE_API_URL environment variable is not set!');
    console.error('❌ API calls will fail! Set VITE_API_URL in Cloudflare Pages environment variables.');
} else if (API_BASE_URL.includes('jetschoolusa.com')) {
    console.error('❌ WARNING: API URL is set to api.jetschoolusa.com (this domain is not configured!)');
    console.error('❌ Update VITE_API_URL to: https://web-production-bf632.up.railway.app');
}

// Debug: Log environment variables in development
if (import.meta.env.DEV) {
    console.log('🔍 Environment Variables:', {
        VITE_API_URL: API_BASE_URL,
        VITE_SUPABASE_URL: SUPABASE_URL ? 'SET' : 'MISSING',
        VITE_SUPABASE_ANON_KEY: SUPABASE_ANON_KEY ? 'SET' : 'MISSING'
    });
}

// Validate Supabase config
if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    console.error('❌ Missing Supabase configuration! Site may not work correctly.');
    console.error('Missing:', {
        SUPABASE_URL: !SUPABASE_URL,
        SUPABASE_ANON_KEY: !SUPABASE_ANON_KEY
    });
}

// Create Supabase client (will fail gracefully if config is missing)
export const supabase = SUPABASE_URL && SUPABASE_ANON_KEY 
    ? createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
        auth: {
            autoRefreshToken: true,
            persistSession: true,
            detectSessionInUrl: true,
        },
    })
    : null; // Return null if config is missing

// Create axios instance with auth interceptor
export const apiClient = axios.create({
    baseURL: API_BASE_URL,
});

// Add auth token to requests
apiClient.interceptors.request.use(async (config) => {
    // Get token from Supabase
    const { data: { session } } = await supabase.auth.getSession();
    if (session?.access_token) {
        config.headers.Authorization = `Bearer ${session.access_token}`;
    }
    return config;
});

// Sync Supabase user to our backend
export async function syncUserToBackend(user) {
    if (!user) return null;

    try {
        const response = await apiClient.post('/api/auth/sync', {
            email: user.email,
            name: user.user_metadata?.name || user.user_metadata?.full_name || null,
            avatar_url: user.user_metadata?.avatar_url || null,
        });
        return response.data.user;
    } catch (error) {
        console.error('Failed to sync user:', error);
        return null;
    }
}

// Get current user from backend
export async function getCurrentUser() {
    try {
        const response = await apiClient.get('/api/auth/me');
        return response.data.user;
    } catch (error) {
        console.error('Failed to get current user:', error);
        return null;
    }
}

// Auth helper functions
export async function signUp(email, password, metadata = {}) {
    const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
            data: metadata,
        },
    });

    if (error) throw error;

    // Sync user to backend
    if (data.user) {
        await syncUserToBackend(data.user);
    }

    return data;
}

export async function signIn(email, password) {
    const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
    });

    if (error) throw error;

    // Sync user to backend
    if (data.user) {
        await syncUserToBackend(data.user);
    }

    return data;
}

export async function signOut() {
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
}

export async function resetPassword(email) {
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/reset-password`,
    });
    if (error) throw error;
}

// Get current session
export async function getSession() {
    const { data: { session } } = await supabase.auth.getSession();
    return session;
}

// Listen to auth changes
export function onAuthStateChange(callback) {
    return supabase.auth.onAuthStateChange((event, session) => {
        callback(event, session);

        // Sync user when signed in
        if (event === 'SIGNED_IN' && session?.user) {
            syncUserToBackend(session.user);
        }
    });
}

