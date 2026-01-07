import { verifySupabaseToken, extractUserIdFromToken } from './utils/auth';
import { corsHeaders, handleCors, jsonResponse } from './utils/response';
import { listingsRouter } from './routes/listings';
import { profilesRouter } from './routes/profiles';
import { adminRouter } from './routes/admin';
import { authRouter } from './routes/auth';
import { uploadRouter } from './routes/upload';
import { toolsRouter } from './routes/tools';
import { usageRouter } from './routes/usage';

export interface Env {
    DB: D1Database;
    IMAGES: R2Bucket;
    VIDEOS: R2Bucket;
    CACHE: KVNamespace;
    SUPABASE_URL: string;
    SUPABASE_ANON_KEY: string;
    SUPABASE_SERVICE_KEY: string;
    FRONTEND_URL: string;
}

export default {
    async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
        const url = new URL(request.url);

        // Handle CORS preflight
        if (request.method === 'OPTIONS') {
            return handleCors(request, env);
        }

        // Verify Supabase auth token
        const authHeader = request.headers.get('Authorization');
        let userId: string | null = null;
        let userEmail: string | null = null;

        if (authHeader?.startsWith('Bearer ')) {
            const token = authHeader.substring(7);

            // Quick validation using token extraction
            const extractedUserId = extractUserIdFromToken(token);

            if (extractedUserId) {
                // Full verification with Supabase
                const user = await verifySupabaseToken(token, env.SUPABASE_URL, env.SUPABASE_ANON_KEY);
                if (user) {
                    userId = user.id;
                    userEmail = user.email;
                }
            }
        }

        // Route handling
        try {
            // Health check
            if (url.pathname === '/api/health') {
                return jsonResponse({ status: 'ok', timestamp: Date.now() });
            }

            // API routes
            if (url.pathname.startsWith('/api/listings')) {
                return listingsRouter(request, env, userId, userEmail);
            }

            if (url.pathname.startsWith('/api/profiles')) {
                return profilesRouter(request, env);
            }

            if (url.pathname.startsWith('/api/admin')) {
                return adminRouter(request, env, userId);
            }

            if (url.pathname.startsWith('/api/auth')) {
                return authRouter(request, env, userId, userEmail);
            }

            if (url.pathname.startsWith('/api/upload')) {
                return uploadRouter(request, env, userId);
            }

            if (url.pathname.startsWith('/api/tools')) {
                return toolsRouter(request, env, userId);
            }

            if (url.pathname.startsWith('/api/usage')) {
                return usageRouter(request, env, userId);
            }

            // 404
            return jsonResponse({ error: 'Not found' }, 404);
        } catch (error) {
            console.error('Request error:', error);
            return jsonResponse(
                { error: 'Internal server error', message: error instanceof Error ? error.message : 'Unknown error' },
                500
            );
        }
    },
};

