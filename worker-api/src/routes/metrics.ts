/**
 * Metrics routes (admin only)
 * GET /api/metrics - Basic usage metrics
 */

import { jsonResponse, errorResponse } from '../utils/response';
import type { Env, AuthenticatedRequest } from '../index';

export async function metricsRouter(
  request: Request,
  env: Env,
  authInfo: AuthenticatedRequest
): Promise<Response> {
  const url = new URL(request.url);
  
  try {
    // GET /api/metrics - Get usage metrics
    if (request.method === 'GET' && url.pathname === '/api/metrics') {
      const days = Math.min(parseInt(url.searchParams.get('days') || '30'), 365);
      const since = Math.floor(Date.now() / 1000) - (days * 24 * 60 * 60);
      
      // Total users
      const totalUsers = await env.DB.prepare(
        'SELECT COUNT(*) as count FROM users'
      ).first<{ count: number }>();
      
      // Total listings by status
      const listingsByStatus = await env.DB.prepare(`
        SELECT status, COUNT(*) as count
        FROM listings
        GROUP BY status
      `).all<{ status: string; count: number }>();
      
      // Tool usage stats
      const toolUsage = await env.DB.prepare(`
        SELECT tool_name, COUNT(*) as count
        FROM tool_usage
        WHERE created_at >= ?
        GROUP BY tool_name
        ORDER BY count DESC
      `).bind(since).all<{ tool_name: string; count: number }>();
      
      // Total tool usage
      const totalToolUsage = await env.DB.prepare(`
        SELECT COUNT(*) as count
        FROM tool_usage
        WHERE created_at >= ?
      `).bind(since).first<{ count: number }>();
      
      // New listings in period
      const newListings = await env.DB.prepare(`
        SELECT COUNT(*) as count
        FROM listings
        WHERE created_at >= ?
      `).bind(since).first<{ count: number }>();
      
      // Active listings count
      const activeListings = await env.DB.prepare(
        'SELECT COUNT(*) as count FROM listings WHERE status = ?'
      ).bind('active').first<{ count: number }>();
      
      // Pending listings count
      const pendingListings = await env.DB.prepare(
        'SELECT COUNT(*) as count FROM listings WHERE status = ?'
      ).bind('pending').first<{ count: number }>();
      
      return jsonResponse({
        period_days: days,
        users: {
          total: totalUsers?.count || 0,
        },
        listings: {
          total: activeListings?.count || 0,
          pending: pendingListings?.count || 0,
          by_status: listingsByStatus.results || [],
          new_in_period: newListings?.count || 0,
        },
        tool_usage: {
          total: totalToolUsage?.count || 0,
          by_tool: toolUsage.results || [],
        },
        timestamp: Math.floor(Date.now() / 1000),
      });
    }
    
    return errorResponse('Not found', 404);
  } catch (error) {
    console.error('Metrics route error:', error);
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

