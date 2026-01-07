import { Env } from '../index';
import type { Env } from '../index';
import { jsonResponse, errorResponse, unauthorizedResponse, forbiddenResponse } from '../utils/response';
import { isAdmin } from '../utils/db';

export async function adminRouter(
    request: Request,
    env: Env,
    userId: string | null
): Promise<Response> {
    if (!userId) {
        return unauthorizedResponse();
    }

    const isUserAdmin = await isAdmin(env.DB, userId);
    if (!isUserAdmin) {
        return forbiddenResponse();
    }

    const url = new URL(request.url);
    const method = request.method;

    try {
        // GET /api/admin/listings - List pending listings
        if (method === 'GET' && url.pathname === '/api/admin/listings') {
            const status = url.searchParams.get('status') || 'pending';

            const listings = await env.DB.prepare(`
        SELECT l.*, pp.*, pr.*, u.email as owner_email, u.name as owner_name
        FROM listings l
        LEFT JOIN performance_profiles pp ON l.performance_profile_id = pp.id
        LEFT JOIN pricing_plans pr ON l.pricing_plan_id = pr.id
        LEFT JOIN users u ON l.owner_id = u.id
        WHERE l.status = ?
        ORDER BY l.created_at DESC
      `).bind(status).all();

            return jsonResponse({ listings: listings.results || [] });
        }

        // POST /api/admin/listings/:id/approve - Approve listing
        if (method === 'POST' && url.pathname.match(/^\/api\/admin\/listings\/\d+\/approve$/)) {
            const listingId = parseInt(url.pathname.split('/')[4] || '0');
            const body = await request.json() as any;

            // Update listing status
            await env.DB.prepare(`
        UPDATE listings 
        SET status = 'active', approved_at = unixepoch(), updated_at = unixepoch()
        WHERE id = ?
      `).bind(listingId).run();

            // Log approval
            await env.DB.prepare(`
        INSERT INTO approvals (listing_id, admin_id, action, reason, created_at)
        VALUES (?, ?, 'approved', ?, unixepoch())
      `).bind(listingId, userId, body.reason || null).run();

            const listing = await env.DB.prepare(`
        SELECT l.*, pp.*, pr.*
        FROM listings l
        LEFT JOIN performance_profiles pp ON l.performance_profile_id = pp.id
        LEFT JOIN pricing_plans pr ON l.pricing_plan_id = pr.id
        WHERE l.id = ?
      `).bind(listingId).first();

            return jsonResponse({ listing });
        }

        // POST /api/admin/listings/:id/reject - Reject listing
        if (method === 'POST' && url.pathname.match(/^\/api\/admin\/listings\/\d+\/reject$/)) {
            const listingId = parseInt(url.pathname.split('/')[4] || '0');
            const body = await request.json() as any;

            if (!body.reason) {
                return errorResponse('Rejection reason is required');
            }

            // Update listing status
            await env.DB.prepare(`
        UPDATE listings 
        SET status = 'rejected', rejected_reason = ?, updated_at = unixepoch()
        WHERE id = ?
      `).bind(body.reason, listingId).run();

            // Log rejection
            await env.DB.prepare(`
        INSERT INTO approvals (listing_id, admin_id, action, reason, created_at)
        VALUES (?, ?, 'rejected', ?, unixepoch())
      `).bind(listingId, userId, body.reason).run();

            const listing = await env.DB.prepare(`
        SELECT l.*, pp.*, pr.*
        FROM listings l
        LEFT JOIN performance_profiles pp ON l.performance_profile_id = pp.id
        LEFT JOIN pricing_plans pr ON l.pricing_plan_id = pr.id
        WHERE l.id = ?
      `).bind(listingId).first();

            return jsonResponse({ listing });
        }

        // PUT /api/admin/users/:id/admin - Toggle admin status
        if (method === 'PUT' && url.pathname.match(/^\/api\/admin\/users\/[^/]+\/admin$/)) {
            const targetUserId = url.pathname.split('/')[4];
            const body = await request.json() as any;

            if (targetUserId === userId) {
                return errorResponse('Cannot modify your own admin status');
            }

            await env.DB.prepare(`
        UPDATE users SET is_admin = ?, updated_at = unixepoch() WHERE id = ?
      `).bind(body.is_admin ? 1 : 0, targetUserId).run();

            const user = await env.DB.prepare('SELECT * FROM users WHERE id = ?')
                .bind(targetUserId).first();

            return jsonResponse({ user });
        }

        return errorResponse('Method not allowed', 405);
    } catch (error) {
        console.error('Admin route error:', error);
        return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
    }
}

