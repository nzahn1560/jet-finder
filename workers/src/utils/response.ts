import { Env } from '../index';

export function jsonResponse(data: any, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...corsHeaders(),
    },
  });
}

export function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  };
}

export function handleCors(request: Request, env: Env): Response {
  const origin = request.headers.get('Origin');
  const allowedOrigins = [env.FRONTEND_URL, 'http://localhost:5173', 'http://localhost:3000'];
  
  const headers = {
    ...corsHeaders(),
    'Access-Control-Allow-Origin': allowedOrigins.includes(origin || '') ? origin! : '*',
    'Access-Control-Max-Age': '86400',
  };

  return new Response(null, { status: 204, headers });
}

export function errorResponse(message: string, status = 400): Response {
  return jsonResponse({ error: message }, status);
}

export function unauthorizedResponse(): Response {
  return jsonResponse({ error: 'Unauthorized' }, 401);
}

export function forbiddenResponse(): Response {
  return jsonResponse({ error: 'Forbidden' }, 403);
}

