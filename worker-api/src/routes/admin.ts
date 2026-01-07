/**
 * Admin routes
 * GET /api/admin/listings?status=pending - List pending listings (admin only)
 * POST /api/admin/listings/:id/approve - Approve listing (admin only)
 * POST /api/admin/listings/:id/deny - Deny listing (admin only)
 */

import { jsonResponse, errorResponse, forbiddenResponse } from '../utils/response';
import type { Env, AuthenticatedRequest } from '../index';

export async function adminRouter(
    request: Request,
    env: Env,
    authInfo: AuthenticatedRequest
): Promise<Response> {
    const url = new URL(request.url);
    const method = request.method;

    try {
        // GET /api/admin/listings?status=pending
        if (method === 'GET' && url.pathname === '/api/admin/listings') {
            const status = url.searchParams.get('status') || 'pending';
            const limit = Math.min(parseInt(url.searchParams.get('limit') || '50'), 100);
            const offset = parseInt(url.searchParams.get('offset') || '0');

            if (!['pending', 'active', 'denied'].includes(status)) {
                return errorResponse('Invalid status', 400);
            }

            const results = await env.DB.prepare(`
        SELECT l.*, pp.manufacturer, pp.model, pp.specs, u.email as owner_email
        FROM listings l
        LEFT JOIN performance_profiles pp ON l.performance_profile_id = pp.id
        LEFT JOIN users u ON l.owner_id = u.id
        WHERE l.status = ?
        ORDER BY l.created_at ASC
        LIMIT ? OFFSET ?
      `).bind(status, limit, offset).all();

            const countResult = await env.DB.prepare(
                'SELECT COUNT(*) as total FROM listings WHERE status = ?'
            ).bind(status).first<{ total: number }>();

            return jsonResponse({
                listings: results.results || [],
                pagination: {
                    limit,
                    offset,
                    total: countResult?.total || 0,
                },
            });
        }

        // POST /api/admin/listings/:id/approve
        if (method === 'POST' && url.pathname.match(/^\/api\/admin\/listings\/\d+\/approve$/)) {
            const listingId = parseInt(url.pathname.split('/')[4]);
            const body = await request.json() as any;

            // Check listing exists and is pending
            const listing = await env.DB.prepare(
                'SELECT id, status, owner_id FROM listings WHERE id = ?'
            ).bind(listingId).first<{ id: number; status: string; owner_id: string }>();

            if (!listing) {
                return errorResponse('Listing not found', 404);
            }

            if (listing.status !== 'pending') {
                return errorResponse(`Listing is already ${listing.status}`, 400);
            }

            // Update listing status
            await env.DB.prepare(
                'UPDATE listings SET status = ?, updated_at = unixepoch() WHERE id = ?'
            ).bind('active', listingId).run();

            // Log approval
            await env.DB.prepare(`
        INSERT INTO approvals (listing_id, admin_id, action, reason, created_at)
        VALUES (?, ?, 'approved', ?, unixepoch())
      `).bind(listingId, authInfo.userId, body.reason || null).run();

            return jsonResponse({ message: 'Listing approved', listing_id: listingId });
        }

        // POST /api/admin/listings/:id/deny
        if (method === 'POST' && url.pathname.match(/^\/api\/admin\/listings\/\d+\/deny$/)) {
            const listingId = parseInt(url.pathname.split('/')[4]);
            const body = await request.json() as any;

            if (!body.reason || typeof body.reason !== 'string' || body.reason.trim().length === 0) {
                return errorResponse('Reason is required for denial', 400);
            }

            // Check listing exists and is pending
            const listing = await env.DB.prepare(
                'SELECT id, status FROM listings WHERE id = ?'
            ).bind(listingId).first<{ id: number; status: string }>();

            if (!listing) {
                return errorResponse('Listing not found', 404);
            }

            if (listing.status !== 'pending') {
                return errorResponse(`Listing is already ${listing.status}`, 400);
            }

            // Update listing status
            await env.DB.prepare(
                'UPDATE listings SET status = ?, updated_at = unixepoch() WHERE id = ?'
            ).bind('denied', listingId).run();

            // Log denial
            await env.DB.prepare(`
        INSERT INTO approvals (listing_id, admin_id, action, reason, created_at)
        VALUES (?, ?, 'denied', ?, unixepoch())
      `).bind(listingId, authInfo.userId, body.reason.trim()).run();

            return jsonResponse({ message: 'Listing denied', listing_id: listingId });
        }

        return errorResponse('Not found', 404);
    } catch (error) {
        console.error('Admin route error:', error);
        return errorResponse(
            error instanceof Error ? error.message : 'Internal server error',
            500
        );
    }
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

function errorResponse(message: string, status: number = 400, headers: HeadersInit = {}): Response {
    return jsonResponse({ error: message }, headers, status);
}
