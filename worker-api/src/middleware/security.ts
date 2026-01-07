/**
 * Security headers middleware
 */

export interface Env {
  ENVIRONMENT?: string;
}

export function securityHeaders(env: Env): HeadersInit {
  const headers: HeadersInit = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
  };
  
  // Add strict HTTPS in production
  if (env.ENVIRONMENT === 'production') {
    headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains';
  }
  
  return headers;
}

