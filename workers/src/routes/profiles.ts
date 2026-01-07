import { Env } from '../index';
import { jsonResponse, errorResponse } from '../utils/response';

export async function profilesRouter(
  request: Request,
  env: Env
): Promise<Response> {
  const url = new URL(request.url);
  const method = request.method;

  try {
    // GET /api/profiles - List performance profiles
    if (method === 'GET' && url.pathname === '/api/profiles') {
      const manufacturer = url.searchParams.get('manufacturer') || '';
      const search = url.searchParams.get('search') || '';

      let query = 'SELECT * FROM performance_profiles WHERE 1=1';
      const params: any[] = [];

      if (manufacturer) {
        query += ' AND manufacturer = ?';
        params.push(manufacturer);
      }

      if (search) {
        query += ' AND (name LIKE ? OR manufacturer LIKE ?)';
        const searchPattern = `%${search}%`;
        params.push(searchPattern, searchPattern);
      }

      query += ' ORDER BY manufacturer, name';

      const stmt = env.DB.prepare(query).bind(...params);
      const results = await stmt.all();

      return jsonResponse({ profiles: results.results || [] });
    }

    // GET /api/profiles/:id - Single profile
    if (method === 'GET' && url.pathname.match(/^\/api\/profiles\/\d+$/)) {
      const profileId = parseInt(url.pathname.split('/').pop() || '0');
      
      const profile = await env.DB.prepare('SELECT * FROM performance_profiles WHERE id = ?')
        .bind(profileId).first();

      if (!profile) {
        return errorResponse('Profile not found', 404);
      }

      return jsonResponse({ profile });
    }

    // GET /api/pricing-plans - List pricing plans
    if (method === 'GET' && url.pathname === '/api/pricing-plans') {
      const plans = await env.DB.prepare('SELECT * FROM pricing_plans WHERE is_active = 1 ORDER BY price_usd')
        .all();

      return jsonResponse({ plans: plans.results || [] });
    }

    return errorResponse('Method not allowed', 405);
  } catch (error) {
    console.error('Profiles route error:', error);
    return errorResponse(error instanceof Error ? error.message : 'Internal server error', 500);
  }
}

