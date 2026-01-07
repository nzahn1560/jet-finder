/**
 * Response utility functions
 */

export function jsonResponse(data: any, headers: HeadersInit = {}, status: number = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  });
}

export function errorResponse(message: string, status: number = 400, headers: HeadersInit = {}): Response {
  return jsonResponse({ error: message }, headers, status);
}

export function unauthorizedResponse(headers: HeadersInit = {}): Response {
  return jsonResponse({ error: 'Unauthorized' }, headers, 401);
}

export function forbiddenResponse(headers: HeadersInit = {}): Response {
  return jsonResponse({ error: 'Forbidden' }, headers, 403);
}

export function notFoundResponse(headers: HeadersInit = {}): Response {
  return jsonResponse({ error: 'Not found' }, headers, 404);
}
