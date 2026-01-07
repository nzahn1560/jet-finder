import type { Env } from '../index';

export type { Env };

export interface ListingRow {
    id: number;
    title: string;
    description: string | null;
    price_usd: number;
    location: string;
    engine_type: string;
    contact_email: string;
    serial_number: string | null;
    hours: number | null;
    year: number | null;
    status: 'pending' | 'active' | 'rejected';
    payment_plan: 'monthly' | 'six_month';
    owner_id: string | null;
    performance_profile_id: number | null;
    pricing_plan_id: number | null;
    created_at: number;
    updated_at: number;
    approved_at: number | null;
    rejected_reason: string | null;
}

export interface PerformanceProfileRow {
    id: number;
    name: string;
    manufacturer: string;
    engine_type: string;
    range_nm: number;
    cruise_speed_knots: number;
    max_passengers: number;
    max_altitude_ft: number;
    cabin_volume_cuft: number | null;
    baggage_volume_cuft: number | null;
    runway_requirement_ft: number | null;
    hourly_cost_usd: number | null;
    annual_maintenance_usd: number | null;
    purchase_price_usd: number | null;
    image_url: string | null;
    created_at: number;
}

export interface UserRow {
    id: string;
    email: string;
    name: string | null;
    avatar_url: string | null;
    is_admin: number;
    created_at: number;
    updated_at: number;
}

// Ensure user exists in our database (synced from Supabase)
export async function ensureUser(db: D1Database, supabaseUserId: string, email: string, name?: string, avatarUrl?: string): Promise<UserRow> {
    // Check if user exists
    const existing = await db.prepare(
        'SELECT * FROM users WHERE id = ?'
    ).bind(supabaseUserId).first<UserRow>();

    if (existing) {
        // Update if email, name, or avatar changed
        if (existing.email !== email || existing.name !== name || existing.avatar_url !== avatarUrl) {
            await db.prepare(
                'UPDATE users SET email = ?, name = ?, avatar_url = ?, updated_at = unixepoch() WHERE id = ?'
            ).bind(email, name || null, avatarUrl || null, supabaseUserId).run();
            return { ...existing, email, name: name || null, avatar_url: avatarUrl || null };
        }
        return existing;
    }

    // Create new user
    await db.prepare(
        'INSERT INTO users (id, email, name, avatar_url, is_admin, created_at, updated_at) VALUES (?, ?, ?, ?, 0, unixepoch(), unixepoch())'
    ).bind(supabaseUserId, email, name || null, avatarUrl || null).run();

    return {
        id: supabaseUserId,
        email,
        name: name || null,
        avatar_url: avatarUrl || null,
        is_admin: 0,
        created_at: Math.floor(Date.now() / 1000),
        updated_at: Math.floor(Date.now() / 1000),
    };
}

export async function isAdmin(db: D1Database, userId: string | null): Promise<boolean> {
    if (!userId) return false;

    const user = await db.prepare(
        'SELECT is_admin FROM users WHERE id = ?'
    ).bind(userId).first<{ is_admin: number }>();

    return user?.is_admin === 1;
}

// Track tool usage
export async function trackUsage(env: Env, userId: string, toolName: string, action: string, metadata?: Record<string, any>): Promise<void> {
    await env.DB.prepare(`
    INSERT INTO usage_tracking (user_id, tool_name, action, metadata, created_at)
    VALUES (?, ?, ?, ?, unixepoch())
  `).bind(
        userId,
        toolName,
        action,
        metadata ? JSON.stringify(metadata) : null
    ).run();
}

// Get usage stats for a user
export async function getUserUsageStats(db: D1Database, userId: string, days: number = 30): Promise<{ tool_name: string; count: number }[]> {
    const since = Math.floor(Date.now() / 1000) - (days * 24 * 60 * 60);

    const results = await db.prepare(`
    SELECT tool_name, COUNT(*) as count
    FROM usage_tracking
    WHERE user_id = ? AND created_at >= ?
    GROUP BY tool_name
    ORDER BY count DESC
  `).bind(userId, since).all<{ tool_name: string; count: number }>();

    return results.results || [];
}
