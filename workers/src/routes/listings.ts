import { Env } from '../index';
import { jsonResponse, errorResponse, unauthorizedResponse } from '../utils/response';
import { ensureUser, isAdmin, ListingRow } from '../utils/db';

export async function listingsRouter(
    request: Request,
    env: Env,
    userId: string | null,
    userEmail: string | null
): Promise<Response> {
    const url = new URL(request.url);
    const method = request.method;

    try {
        // GET /api/listings - Public listings or user's listings
        if (method === 'GET' && url.pathname === '/api/listings') {
            const myListings = url.searchParams.get('my_listings') === 'true';
            const status = myListings ? undefined : (url.searchParams.get('status') || 'active');
            const search = url.searchParams.get('search') || '';
            const manufacturer = url.searchParams.get('manufacturer') || '';
            const limit = parseInt(url.searchParams.get('limit') || '50');
            const offset = parseInt(url.searchParams.get('offset') || '0');

            let query = `
        SELECT l.*, pp.*, pr.*
        FROM listings l
        LEFT JOIN performance_profiles pp ON l.performance_profile_id = pp.id
        LEFT JOIN pricing_plans pr ON l.pricing_plan_id = pr.id
        WHERE 1=1
      `;
            const params: any[] = [];

            // If requesting user's listings, filter by owner_id
            if (myListings) {
                if (!userId) {
                    return unauthorizedResponse();
                }
                query += ` AND l.owner_id = ?`;
                params.push(userId);
            } else if (status) {
                query += ` AND l.status = ?`;
                params.push(status);
            }

            if (search) {
                query += ` AND (l.title LIKE ? OR l.description LIKE ? OR pp.name LIKE ? OR pp.manufacturer LIKE ?)`;
                const searchPattern = `%${search}%`;
                params.push(searchPattern, searchPattern, searchPattern, searchPattern);
            }

            if (manufacturer) {
                query += ` AND pp.manufacturer = ?`;
                params.push(manufacturer);
            }

            query += ` ORDER BY l.created_at DESC LIMIT ? OFFSET ?`;
            params.push(limit, offset);

            const stmt = env.DB.prepare(query).bind(...params);
            const results = await stmt.all();

            return jsonResponse({
                listings: results.results || [],
                pagination: {
                    limit,
                    offset,
                    total: results.results?.length || 0,
                },
            });
        }

        // GET /api/listings/:id - Single listing
        if (method === 'GET' && url.pathname.match(/^\/api\/listings\/\d+$/)) {
            const listingId = parseInt(url.pathname.split('/').pop() || '0');

            const listing = await env.DB.prepare(`
        SELECT l.*, pp.*, pr.*, u.email as owner_email
        FROM listings l
        LEFT JOIN performance_profiles pp ON l.performance_profile_id = pp.id
        LEFT JOIN pricing_plans pr ON l.pricing_plan_id = pr.id
        LEFT JOIN users u ON l.owner_id = u.id
        WHERE l.id = ?
      `).bind(listingId).first();

            if (!listing) {
                return errorResponse('Listing not found', 404);
            }

            return jsonResponse({ listing });
        }

        // POST /api/listings - Create listing (requires auth)
        if (method === 'POST' && url.pathname === '/api/listings') {
            if (!userId) {
                return unauthorizedResponse();
            }

            const body = await request.json() as any;
            const {
                title,
                description,
                price_usd,
                location,
                engine_type,
                contact_email,
                serial_number,
                hours,
                year,
                performance_profile_id,
                pricing_plan_id,
                payment_plan = 'monthly',
            } = body;

            // Validate required fields
            if (!title || !price_usd || !location || !engine_type || !contact_email || !performance_profile_id) {
                return errorResponse('Missing required fields');
            }

            // Ensure user exists in our DB
            const email = userEmail || request.headers.get('X-User-Email') || '';
            if (!email) {
                return errorResponse('User email is required');
            }
            await ensureUser(env.DB, userId, email);

            // Get pricing plan if provided
            if (pricing_plan_id) {
                const plan = await env.DB.prepare('SELECT * FROM pricing_plans WHERE id = ? AND is_active = 1')
                    .bind(pricing_plan_id).first();
                if (!plan) {
                    return errorResponse('Invalid pricing plan');
                }
            }

            // Insert listing
            const result = await env.DB.prepare(`
        INSERT INTO listings (
          title, description, price_usd, location, engine_type, contact_email,
          serial_number, hours, year, status, payment_plan,
          owner_id, performance_profile_id, pricing_plan_id,
          created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, unixepoch(), unixepoch())
      `).bind(
                title,
                description || null,
                price_usd,
                location,
                engine_type,
                contact_email,
                serial_number || null,
                hours || null,
                year || null,
                payment_plan,
                userId,
                performance_profile_id,
                pricing_plan_id || null,
            ).run();

            const listingId = result.meta.last_row_id;

            // Fetch complete listing with relationships
            const listing = await env.DB.prepare(`
        SELECT l.*, pp.*, pr.*
        FROM listings l
        LEFT JOIN performance_profiles pp ON l.performance_profile_id = pp.id
        LEFT JOIN pricing_plans pr ON l.pricing_plan_id = pr.id
        WHERE l.id = ?
      `).bind(listingId).first();

            return jsonResponse({ listing }, 201);
        }

        // PUT /api/listings/:id - Update listing (owner only)
        if (method === 'PUT' && url.pathname.match(/^\/api\/listings\/\d+$/)) {
            if (!userId) {
                return unauthorizedResponse();
            }

            const listingId = parseInt(url.pathname.split('/').pop() || '0');
            const body = await request.json() as any;

            // Check ownership
            const existing = await env.DB.prepare('SELECT owner_id FROM listings WHERE id = ?')
                .bind(listingId).first<{ owner_id: string | null }>();

            if (!existing || existing.owner_id !== userId) {
                return errorResponse('Forbidden', 403);
            }

            // Build update query dynamically
            const updates: string[] = [];
            const values: any[] = [];

            const allowedFields = ['title', 'description', 'price_usd', 'location', 'engine_type', 'contact_email', 'serial_number', 'hours', 'year'];
            for (const field of allowedFields) {
                if (body[field] !== undefined) {
                    updates.push(`${field} = ?`);
                    values.push(body[field]);
                }
            }

            if (updates.length === 0) {
                return errorResponse('No fields to update');
            }

            updates.push('updated_at = unixepoch()');
            values.push(listingId);

            await env.DB.prepare(`
        UPDATE listings SET ${updates.join(', ')} WHERE id = ?
      `).bind(...values).run();

            const listing = await env.DB.prepare(`
        SELECT l.*, pp.*, pr.*
        FROM listings l
        LEFT JOIN performance_profiles pp ON l.performance_profile_id = pp.id
        LEFT JOIN pricing_plans pr ON l.pricing_plan_id = pr.id
        WHERE l.id = ?
      `).bind(listingId).first();

            return jsonResponse({ listing });
        }

        // DELETE /api/listings/:id - Delete listing (owner only)
        if (method === 'DELETE' && url.pathname.match(/^\/api\/listings\/\d+$/)) {
            if (!userId) {
                return unauthorizedResponse();
            }

            const listingId = parseInt(url.pathname.split('/').pop() || '0');

            // Check ownership
            const existing = await env.DB.prepare('SELECT owner_id FROM listings WHERE id = ?')
                .bind(listingId).first<{ owner_id: string | null }>();

            if (!existing || existing.owner_id !== userId) {
                return errorResponse('Forbidden', 403);
            }

            await env.DB.prepare('DELETE FROM listings WHERE id = ?').bind(listingId).run();

            return jsonResponse({ message: 'Listing deleted' });
        }

        return errorResponse('Method not allowed', 405);
    } catch (error) {
        console.error('Listings route error:', error);
        return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
    }
}

