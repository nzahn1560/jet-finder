/**
 * Tool usage routes
 * POST /api/tool/usage - Record internal tool usage
 */

import { jsonResponse, errorResponse } from '../utils/response';
import type { Env, AuthenticatedRequest } from '../index';

export async function toolRouter(
  request: Request,
  env: Env,
  authInfo: AuthenticatedRequest
): Promise<Response> {
  const url = new URL(request.url);
  
  try {
    // POST /api/tool/usage - Record tool usage
    if (request.method === 'POST' && url.pathname === '/api/tool/usage') {
      const body = await request.json() as any;
      const { tool_name, meta } = body;
      
      // Input validation
      if (!tool_name || typeof tool_name !== 'string' || tool_name.trim().length === 0) {
        return errorResponse('tool_name is required', 400);
      }
      
      // Validate tool name (prevent injection)
      const allowedTools = ['aircraft-matcher', 'scoring', 'comparison', 'route-planner'];
      if (!allowedTools.includes(tool_name)) {
        return errorResponse(`Invalid tool_name. Allowed: ${allowedTools.join(', ')}`, 400);
      }
      
      // Ensure user exists in database
      const userRecord = await env.DB.prepare(
        'SELECT id FROM users WHERE id = ?'
      ).bind(authInfo.userId).first();
      
      if (!userRecord) {
        return errorResponse('User not found', 404);
      }
      
      // Record usage
      await env.DB.prepare(`
        INSERT INTO tool_usage (user_id, tool_name, meta, created_at)
        VALUES (?, ?, ?, unixepoch())
      `).bind(
        authInfo.userId,
        tool_name.trim(),
        meta ? JSON.stringify(meta) : null
      ).run();
      
      return jsonResponse({
        success: true,
        message: 'Usage recorded',
        tool_name,
      });
    }
    
    return errorResponse('Not found', 404);
  } catch (error) {
    console.error('Tool route error:', error);
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

