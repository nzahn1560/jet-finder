// Supabase Auth integration for Cloudflare Workers
// Uses Supabase JWT tokens and user metadata

export interface SupabaseUser {
    id: string;
    email: string;
    user_metadata?: {
        name?: string;
        avatar_url?: string;
    };
    app_metadata?: {
        provider?: string;
        providers?: string[];
    };
}

// Verify Supabase JWT token
export async function verifySupabaseToken(token: string, supabaseUrl: string, supabaseAnonKey: string): Promise<SupabaseUser | null> {
    try {
        // Supabase tokens are JWTs signed with the JWT secret
        // For production, verify using Supabase's public keys
        // For MVP, we'll call Supabase API to verify

        const response = await fetch(`${supabaseUrl}/auth/v1/user`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'apikey': supabaseAnonKey,
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

// Extract user ID from token (for quick validation without API call)
export function extractUserIdFromToken(token: string): string | null {
    try {
        // JWT format: header.payload.signature
        const parts = token.split('.');
        if (parts.length !== 3) return null;

        const payload = JSON.parse(atob(parts[1]));
        return payload.sub || payload.user_id || null;
    } catch {
        return null;
    }
}
