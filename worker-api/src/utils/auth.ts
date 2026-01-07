/**
 * Authentication utilities for Supabase JWT verification
 */

export interface SupabaseUser {
    id: string;
    email: string;
    user_metadata?: {
        name?: string;
        avatar_url?: string;
    };
}

export interface Env {
    SUPABASE_URL: string;
    SUPABASE_ANON_KEY: string;
}

/**
 * Verify Supabase JWT token by calling Supabase API
 * This validates the token and returns user information
 */
export async function verifySupabaseJWT(token: string, env: Env): Promise<SupabaseUser | null> {
    try {
        const response = await fetch(`${env.SUPABASE_URL}/auth/v1/user`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'apikey': env.SUPABASE_ANON_KEY,
            },
        });

        if (!response.ok) {
            return null;
        }

        const user = await response.json() as SupabaseUser;
        return user;
    } catch (error) {
        console.error('Token verification error:', error);
        return null;
    }
}

/**
 * Extract user ID from JWT token without verification
 * Use only for quick validation; always verify with verifySupabaseJWT
 */
export function extractUserIdFromToken(token: string): string | null {
    try {
        const parts = token.split('.');
        if (parts.length !== 3) return null;

        const payload = JSON.parse(atob(parts[1]));
        return payload.sub || payload.user_id || null;
    } catch {
        return null;
    }
}
