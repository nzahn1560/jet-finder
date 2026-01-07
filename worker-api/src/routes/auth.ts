/**
 * Auth routes
 * POST /api/auth/verify - Verify Supabase JWT token
 */

import { verifySupabaseJWT } from '../utils/auth';
import { jsonResponse } from '../utils/response';
import type { Env, AuthenticatedRequest } from '../index';

export async function authRouter(
    request: Request,
    env: Env,
    authInfo: AuthenticatedRequest
): Promise<Response> {
    const url = new URL(request.url);

    // POST /api/auth/verify - Verify Supabase JWT
    if (request.method === 'POST' && url.pathname === '/api/auth/verify') {
        const authHeader = request.headers.get('Authorization');

        if (!authHeader?.startsWith('Bearer ')) {
            return jsonResponse({ error: 'Missing or invalid authorization header' }, {}, 401);
        }

        const token = authHeader.substring(7);
        const user = await verifySupabaseJWT(token, env);

        if (!user) {
            return jsonResponse({ error: 'Invalid or expired token' }, {}, 401);
        }

        // Ensure user exists in our database
        const existingUser = await env.DB.prepare(
            'SELECT id, email, is_admin FROM users WHERE supabase_user_id = ?'
        ).bind(user.id).first<{ id: string; email: string; is_admin: number }>();

        if (!existingUser) {
            // Create user record if doesn't exist
            const userId = crypto.randomUUID();
            await env.DB.prepare(
                'INSERT INTO users (id, email, supabase_user_id, is_admin, created_at, updated_at) VALUES (?, ?, ?, 0, unixepoch(), unixepoch())'
            ).bind(userId, user.email, user.id).run();

            return jsonResponse({
                verified: true,
                user: {
                    id: userId,
                    email: user.email,
                    is_admin: false,
                },
            });
        }

        return jsonResponse({
            verified: true,
            user: {
                id: existingUser.id,
                email: existingUser.email,
                is_admin: existingUser.is_admin === 1,
            },
        });
    }

    return jsonResponse({ error: 'Not found' }, {}, 404);
}

function jsonResponse(data: any, headers: HeadersInit = {}, status: number = 200): Response {
    return new Response(JSON.stringify(data), {
        status,
        headers: {
            'Content-Type': 'application/json',
            ...headers,
        },
    });
}
