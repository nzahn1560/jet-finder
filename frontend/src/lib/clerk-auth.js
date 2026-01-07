// Clerk authentication integration for React frontend
// Install: npm install @clerk/clerk-react

import { useAuth as useClerkAuth, useUser as useClerkUser } from '@clerk/clerk-react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://jetfinder-api.YOUR_WORKER_SUBDOMAIN.workers.dev';

// Create axios instance with auth interceptor
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

// Add auth token to requests
apiClient.interceptors.request.use(async (config) => {
  // Get token from Clerk (this will be set by ClerkProvider)
  const token = await window.Clerk?.session?.getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Sync Clerk user to our backend
export async function syncUserToBackend(user) {
  if (!user) return null;

  try {
    const response = await apiClient.post('/api/auth/sync', {
      email: user.primaryEmailAddress?.emailAddress || '',
      name: `${user.firstName || ''} ${user.lastName || ''}`.trim() || null,
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

// Export hooks for use in components
export { useClerkAuth as useAuth, useClerkUser as useUser };

