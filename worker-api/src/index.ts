/**
 * JetSchoolUSA Cloudflare Worker API
 * Main entry point for all API routes
 */

import { authRouter } from './routes/auth';
import { listingsRouter } from './routes/listings';
import { adminRouter } from './routes/admin';
import { uploadsRouter } from './routes/uploads';
import { toolRouter } from './routes/tool';
import { metricsRouter } from './routes/metrics';
import { rateLimiter } from './middleware/rate-limit';
import { corsMiddleware } from './middleware/cors';
import { securityHeaders } from './middleware/security';
import { verifySupabaseJWT } from './utils/auth';

export interface Env {
    // Database
    DB: D1Database;

    // Storage
    IMAGES: R2Bucket;
    VIDEOS: R2Bucket;
    CACHE: KVNamespace;

    // Supabase Auth
    SUPABASE_URL: string;
    SUPABASE_ANON_KEY: string;
    SUPABASE_SERVICE_KEY: string;

    // App Config
    FRONTEND_URL: string;
    ENVIRONMENT: string;

    // Rate limiting keys (optional)
    RATE_LIMIT_ENABLED?: string;
}

export interface AuthenticatedRequest {
    userId?: string;
    userEmail?: string;
    isAdmin?: boolean;
}

export default {
    async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
        const url = new URL(request.url);

        // Apply security headers to all responses
        const responseHeaders = securityHeaders(env);

        // Handle CORS preflight
        if (request.method === 'OPTIONS') {
            return corsMiddleware(request, env, new Response(null, { headers: responseHeaders }));
        }

        // Apply CORS to all responses
        const corsHandler = (response: Response) => corsMiddleware(request, env, response);

        // Health check (no auth required)
        if (url.pathname === '/api/health') {
            return corsHandler(jsonResponse({ status: 'ok', timestamp: Date.now() }, responseHeaders));
        }

        // Rate limiting (skip for health checks)
        if (env.RATE_LIMIT_ENABLED !== 'false') {
            const rateLimitResult = await rateLimiter(request, env);
            if (!rateLimitResult.allowed) {
                return corsHandler(jsonResponse(
                    { error: 'Rate limit exceeded', retryAfter: rateLimitResult.retryAfter },
                    { ...responseHeaders, 'Retry-After': String(rateLimitResult.retryAfter) },
                    429
                ));
            }
        }

        // Extract auth info for protected routes
        let authInfo: AuthenticatedRequest = {};

        if (url.pathname.startsWith('/api/auth/verify') ||
            url.pathname.startsWith('/api/listings') ||
            url.pathname.startsWith('/api/admin') ||
            url.pathname.startsWith('/api/uploads') ||
            url.pathname.startsWith('/api/tool') ||
            url.pathname.startsWith('/api/metrics')) {

            const authHeader = request.headers.get('Authorization');

            if (authHeader?.startsWith('Bearer ')) {
                const token = authHeader.substring(7);
                try {
                    const user = await verifySupabaseJWT(token, env);
                    if (user) {
                        authInfo.userId = user.id;
                        authInfo.userEmail = user.email;

                        // Check admin status
                        const adminCheck = await env.DB.prepare(
                            'SELECT is_admin FROM users WHERE id = ?'
                        ).bind(user.id).first<{ is_admin: number }>();

                        authInfo.isAdmin = adminCheck?.is_admin === 1;
                    }
                } catch (error) {
                    // Auth failed, but continue - some routes handle this
                    console.warn('Auth verification failed:', error);
                }
            }
        }

        // Route handling
        try {
            // Auth routes
            if (url.pathname.startsWith('/api/auth')) {
                return corsHandler(await authRouter(request, env, authInfo));
            }

            // Listings routes (some public, some require auth)
            if (url.pathname.startsWith('/api/listings')) {
                return corsHandler(await listingsRouter(request, env, authInfo));
            }

            // Admin routes (require auth + admin)
            if (url.pathname.startsWith('/api/admin')) {
                if (!authInfo.userId || !authInfo.isAdmin) {
                    return corsHandler(jsonResponse({ error: 'Unauthorized' }, responseHeaders, 403));
                }
                return corsHandler(await adminRouter(request, env, authInfo));
            }

            // Upload routes (require auth)
            if (url.pathname.startsWith('/api/uploads')) {
                if (!authInfo.userId) {
                    return corsHandler(jsonResponse({ error: 'Unauthorized' }, responseHeaders, 401));
                }
                return corsHandler(await uploadsRouter(request, env, authInfo));
            }

            // Tool usage routes (require auth)
            if (url.pathname.startsWith('/api/tool')) {
                if (!authInfo.userId) {
                    return corsHandler(jsonResponse({ error: 'Unauthorized' }, responseHeaders, 401));
                }
                return corsHandler(await toolRouter(request, env, authInfo));
            }

            // Metrics routes (require auth + admin)
            if (url.pathname.startsWith('/api/metrics')) {
                if (!authInfo.userId || !authInfo.isAdmin) {
                    return corsHandler(jsonResponse({ error: 'Unauthorized' }, responseHeaders, 403));
                }
                return corsHandler(await metricsRouter(request, env, authInfo));
            }

            // 404
            return corsHandler(jsonResponse({ error: 'Not found' }, responseHeaders, 404));

        } catch (error) {
            console.error('Request error:', error);
            const errorMessage = error instanceof Error ? error.message : 'Internal server error';

            // Don't expose internal errors in production
            const publicMessage = env.ENVIRONMENT === 'production'
                ? 'Internal server error'
                : errorMessage;

            return corsHandler(jsonResponse(
                { error: publicMessage },
                responseHeaders,
                500
            ));
        }
    },
};

// Helper function for JSON responses
function jsonResponse(data: any, headers: HeadersInit = {}, status: number = 200): Response {
    return new Response(JSON.stringify(data), {
        status,
        headers: {
            'Content-Type': 'application/json',
            ...headers,
        },
    });
}
