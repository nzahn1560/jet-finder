import { Env } from '../index';
import type { Env } from '../index';
import { jsonResponse, errorResponse, unauthorizedResponse, forbiddenResponse } from '../utils/response';
import { getUserUsageStats, isAdmin } from '../utils/db';

export async function usageRouter(
    request: Request,
    env: Env,
    userId: string | null
): Promise<Response> {
    if (!userId) {
        return unauthorizedResponse();
    }

    const url = new URL(request.url);
    const method = request.method;

    try {
        // GET /api/usage/me - Get current user's usage stats
        if (method === 'GET' && url.pathname === '/api/usage/me') {
            const days = parseInt(url.searchParams.get('days') || '30');
            const stats = await getUserUsageStats(env.DB, userId, days);

            // Get total usage count
            const total = stats.reduce((sum, s) => sum + s.count, 0);

            return jsonResponse({
                user_id: userId,
                period_days: days,
                total_usage: total,
                by_tool: stats,
            });
        }

        // GET /api/usage/all - Get all usage stats (admin only)
        if (method === 'GET' && url.pathname === '/api/usage/all') {
            const isUserAdmin = await isAdmin(env.DB, userId);
            if (!isUserAdmin) {
                return forbiddenResponse();
            }

            const days = parseInt(url.searchParams.get('days') || '30');
            const since = Math.floor(Date.now() / 1000) - (days * 24 * 60 * 60);

            // Get aggregated stats
            const stats = await env.DB.prepare(`
        SELECT 
          tool_name,
          COUNT(*) as total_uses,
          COUNT(DISTINCT user_id) as unique_users
        FROM usage_tracking
        WHERE created_at >= ?
        GROUP BY tool_name
        ORDER BY total_uses DESC
      `).bind(since).all<{ tool_name: string; total_uses: number; unique_users: number }>();

            return jsonResponse({
                period_days: days,
                tools: stats.results || [],
            });
        }

        return errorResponse('Method not allowed', 405);
    } catch (error) {
        console.error('Usage route error:', error);
        return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
    }
}

