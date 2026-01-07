/**
 * Listings routes
 * POST /api/listings - Create listing (require auth)
 * GET /api/listings - List approved listings with search/filter
 * GET /api/listings/:id - Get single listing
 */

import { jsonResponse, errorResponse, unauthorizedResponse } from '../utils/response';
import type { Env, AuthenticatedRequest } from '../index';

export async function listingsRouter(
    request: Request,
    env: Env,
    authInfo: AuthenticatedRequest
): Promise<Response> {
    const url = new URL(request.url);
    const method = request.method;

    try {
        // POST /api/listings - Create listing (requires auth)
        if (method === 'POST' && url.pathname === '/api/listings') {
            if (!authInfo.userId) {
                return unauthorizedResponse();
            }

            const body = await request.json() as any;

            // Input validation
            const errors: string[] = [];
            if (!body.title || typeof body.title !== 'string' || body.title.trim().length === 0) {
                errors.push('Title is required');
            }
            if (!body.price || typeof body.price !== 'number' || body.price <= 0) {
                errors.push('Valid price is required');
            }
            if (!body.performance_profile_id || typeof body.performance_profile_id !== 'number') {
                errors.push('Performance profile is required');
            }

            if (errors.length > 0) {
                return errorResponse(errors.join(', '), 400);
            }

            // Verify performance profile exists
            const profile = await env.DB.prepare(
                'SELECT id FROM performance_profiles WHERE id = ?'
            ).bind(body.performance_profile_id).first();

            if (!profile) {
                return errorResponse('Performance profile not found', 404);
            }

            // Get or create user record
            let userRecord = await env.DB.prepare(
                'SELECT id FROM users WHERE id = ?'
            ).bind(authInfo.userId).first();

            if (!userRecord) {
                // Create user record if doesn't exist
                await env.DB.prepare(
                    'INSERT INTO users (id, email, supabase_user_id, is_admin, created_at, updated_at) VALUES (?, ?, ?, 0, unixepoch(), unixepoch())'
                ).bind(authInfo.userId, authInfo.userEmail || '', authInfo.userId).run();
            }

            // Create listing
            const result = await env.DB.prepare(`
        INSERT INTO listings (
          owner_id, title, description, price, status, pricing_plan,
          performance_profile_id, created_at, updated_at
        ) VALUES (?, ?, ?, ?, 'pending', ?, ?, unixepoch(), unixepoch())
      `).bind(
                authInfo.userId,
                body.title.trim(),
                body.description || null,
                body.price,
                body.pricing_plan || null,
                body.performance_profile_id
            ).run();

            const listingId = result.meta.last_row_id;

            // Fetch created listing with joins
            const listing = await env.DB.prepare(`
        SELECT l.*, pp.manufacturer, pp.model, pp.specs
        FROM listings l
        LEFT JOIN performance_profiles pp ON l.performance_profile_id = pp.id
        WHERE l.id = ?
      `).bind(listingId).first();

            return jsonResponse({ listing });
        }

        // GET /api/listings/:id - Get single listing
        if (method === 'GET' && url.pathname.match(/^\/api\/listings\/\d+$/)) {
            const listingId = parseInt(url.pathname.split('/').pop() || '0');

            const listing = await env.DB.prepare(`
        SELECT l.*, pp.manufacturer, pp.model, pp.specs, u.email as owner_email
        FROM listings l
        LEFT JOIN performance_profiles pp ON l.performance_profile_id = pp.id
        LEFT JOIN users u ON l.owner_id = u.id
        WHERE l.id = ? AND l.status = 'active'
      `).bind(listingId).first();

            if (!listing) {
                return errorResponse('Listing not found', 404);
            }

            // Get images
            const images = await env.DB.prepare(
                'SELECT id, r2_key, order FROM listing_images WHERE listing_id = ? ORDER BY order ASC'
            ).bind(listingId).all();

            return jsonResponse({
                listing: {
                    ...listing,
                    images: images.results || [],
                },
            });
        }

        // GET /api/listings - List approved listings with search/filter
        if (method === 'GET' && url.pathname === '/api/listings') {
            const search = url.searchParams.get('search') || '';
            const manufacturer = url.searchParams.get('manufacturer') || '';
            const minPrice = url.searchParams.get('min_price');
            const maxPrice = url.searchParams.get('max_price');
            const limit = Math.min(parseInt(url.searchParams.get('limit') || '50'), 100);
            const offset = parseInt(url.searchParams.get('offset') || '0');

            let query = `
        SELECT l.*, pp.manufacturer, pp.model, pp.specs
        FROM listings l
        LEFT JOIN performance_profiles pp ON l.performance_profile_id = pp.id
        WHERE l.status = 'active'
      `;
            const params: any[] = [];

            // Search filter
            if (search) {
                query += ` AND (l.title LIKE ? OR l.description LIKE ? OR pp.manufacturer LIKE ? OR pp.model LIKE ?)`;
                const searchPattern = `%${search}%`;
                params.push(searchPattern, searchPattern, searchPattern, searchPattern);
            }

            // Manufacturer filter
            if (manufacturer) {
                query += ` AND pp.manufacturer = ?`;
                params.push(manufacturer);
            }

            // Price range filters
            if (minPrice) {
                query += ` AND l.price >= ?`;
                params.push(parseFloat(minPrice));
            }
            if (maxPrice) {
                query += ` AND l.price <= ?`;
                params.push(parseFloat(maxPrice));
            }

            query += ` ORDER BY l.created_at DESC LIMIT ? OFFSET ?`;
            params.push(limit, offset);

            const results = await env.DB.prepare(query).bind(...params).all();

            // Get total count for pagination
            let countQuery = `
        SELECT COUNT(*) as total
        FROM listings l
        LEFT JOIN performance_profiles pp ON l.performance_profile_id = pp.id
        WHERE l.status = 'active'
      `;
            const countParams: any[] = [];

            if (search) {
                countQuery += ` AND (l.title LIKE ? OR l.description LIKE ? OR pp.manufacturer LIKE ? OR pp.model LIKE ?)`;
                const searchPattern = `%${search}%`;
                countParams.push(searchPattern, searchPattern, searchPattern, searchPattern);
            }
            if (manufacturer) {
                countQuery += ` AND pp.manufacturer = ?`;
                countParams.push(manufacturer);
            }
            if (minPrice) {
                countQuery += ` AND l.price >= ?`;
                countParams.push(parseFloat(minPrice));
            }
            if (maxPrice) {
                countQuery += ` AND l.price <= ?`;
                countParams.push(parseFloat(maxPrice));
            }

            const countResult = await env.DB.prepare(countQuery).bind(...countParams).first<{ total: number }>();
            const total = countResult?.total || 0;

            return jsonResponse({
                listings: results.results || [],
                pagination: {
                    limit,
                    offset,
                    total,
                    hasMore: offset + limit < total,
                },
            });
        }

        return errorResponse('Method not allowed', 405);
    } catch (error) {
        console.error('Listings route error:', error);
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

function unauthorizedResponse(headers: HeadersInit = {}): Response {
    return jsonResponse({ error: 'Unauthorized' }, headers, 401);
}
