/**
 * CORS middleware for handling cross-origin requests
 */

export interface Env {
  FRONTEND_URL: string;
  ENVIRONMENT?: string;
}

export function corsMiddleware(request: Request, env: Env, response: Response): Response {
  const origin = request.headers.get('Origin');
  
  // Allow requests from frontend URL or localhost in dev
  const allowedOrigins = [
    env.FRONTEND_URL,
    'http://localhost:5173',
    'http://localhost:3000',
    'http://127.0.0.1:5173',
  ];
  
  const isAllowed = origin && allowedOrigins.some(allowed => 
    origin === allowed || (env.ENVIRONMENT === 'development' && origin.startsWith('http://localhost'))
  );
  
  const corsHeaders: Record<string, string> = {
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Max-Age': '86400',
  };
  
  if (isAllowed) {
    corsHeaders['Access-Control-Allow-Origin'] = origin;
    corsHeaders['Access-Control-Allow-Credentials'] = 'true';
  }
  
  // Clone response and add CORS headers
  const newHeaders = new Headers(response.headers);
  Object.entries(corsHeaders).forEach(([key, value]) => {
    newHeaders.set(key, value);
  });
  
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: newHeaders,
  });
}

