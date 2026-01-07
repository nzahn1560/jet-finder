import { Env } from '../index';
import { jsonResponse, errorResponse, unauthorizedResponse } from '../utils/response';
import { ensureUser, isAdmin } from '../utils/db';

export async function authRouter(
    request: Request,
    env: Env,
    userId: string | null,
    userEmail: string | null
): Promise<Response> {
    const url = new URL(request.url);
    const method = request.method;

    try {
        // GET /api/auth/me - Get current user
        if (method === 'GET' && url.pathname === '/api/auth/me') {
            if (!userId) {
                return unauthorizedResponse();
            }

            const user = await env.DB.prepare('SELECT * FROM users WHERE id = ?')
                .bind(userId).first();

            if (!user) {
                return errorResponse('User not found', 404);
            }

            const admin = await isAdmin(env.DB, userId);

            return jsonResponse({
                user: {
                    id: user.id,
                    email: user.email,
                    name: user.name,
                    is_admin: admin,
                },
            });
        }

        // POST /api/auth/sync - Sync Supabase user to DB
        if (method === 'POST' && url.pathname === '/api/auth/sync') {
            if (!userId) {
                return unauthorizedResponse();
            }

            const body = await request.json() as any;
            const { email, name, avatar_url } = body;

            const emailToUse = email || userEmail;
            if (!emailToUse) {
                return errorResponse('Email is required');
            }

            const user = await ensureUser(env.DB, userId, emailToUse, name, avatar_url);
            const admin = await isAdmin(env.DB, userId);

            return jsonResponse({
                user: {
                    id: user.id,
                    email: user.email,
                    name: user.name,
                    avatar_url: user.avatar_url,
                    is_admin: admin,
                },
            });
        }

        return errorResponse('Method not allowed', 405);
    } catch (error) {
        console.error('Auth route error:', error);
        return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
    }
}

