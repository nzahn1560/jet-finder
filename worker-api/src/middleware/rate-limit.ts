/**
 * Rate limiting middleware
 * Uses KV namespace for storing rate limit counters
 */

export interface RateLimitResult {
  allowed: boolean;
  retryAfter?: number;
}

export async function rateLimiter(request: Request, env: Env): Promise<RateLimitResult> {
  const url = new URL(request.url);
  
  // Get client identifier (IP address or user ID)
  const clientId = request.headers.get('CF-Connecting-IP') || 'anonymous';
  
  // Different rate limits for different endpoints
  let limit: number;
  let windowSeconds: number;
  let key: string;
  
  if (url.pathname.startsWith('/api/auth/')) {
    // Auth endpoints: 10 requests per minute
    limit = 10;
    windowSeconds = 60;
    key = `rate_limit:auth:${clientId}`;
  } else if (url.pathname.startsWith('/api/uploads/')) {
    // Upload endpoints: 20 requests per minute
    limit = 20;
    windowSeconds = 60;
    key = `rate_limit:upload:${clientId}`;
  } else if (url.pathname.startsWith('/api/admin/')) {
    // Admin endpoints: 50 requests per minute
    limit = 50;
    windowSeconds = 60;
    key = `rate_limit:admin:${clientId}`;
  } else {
    // General API: 100 requests per minute
    limit = 100;
    windowSeconds = 60;
    key = `rate_limit:api:${clientId}`;
  }
  
  try {
    const cache = env.CACHE;
    const current = await cache.get(key);
    const count = current ? parseInt(current) : 0;
    
    if (count >= limit) {
      return {
        allowed: false,
        retryAfter: windowSeconds,
      };
    }
    
    // Increment counter
    await cache.put(key, String(count + 1), {
      expirationTtl: windowSeconds,
    });
    
    return { allowed: true };
  } catch (error) {
    console.error('Rate limit error:', error);
    // Fail open - allow request if rate limiting fails
    return { allowed: true };
  }
}

interface Env {
  CACHE: KVNamespace;
}

