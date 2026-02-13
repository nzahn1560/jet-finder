# Cloudflare Setup for Bot Protection

## Overview

Cloudflare provides the best bot protection when placed in front of your Railway app. This gives you:
- DDoS protection
- Bot management
- Rate limiting at edge
- WAF rules
- CAPTCHA challenges
- Analytics

---

## Step 1: Add Your Domain to Cloudflare

1. Go to https://cloudflare.com
2. Sign up / Log in
3. Add a site → Enter your domain
4. Choose plan (Free plan is sufficient)
5. Update nameservers at your domain registrar

---

## Step 2: Point Domain to Railway

1. In Cloudflare → DNS tab
2. Add A record:
   - Type: `A`
   - Name: `@` (or subdomain like `app`)
   - IPv4 address: Get from Railway (or use CNAME)
   - Proxy status: **Proxied** (orange cloud)

Or use CNAME:
   - Type: `CNAME`
   - Name: `@`
   - Target: `your-app.up.railway.app`
   - Proxy status: **Proxied**

---

## Step 3: Configure Bot Protection

### 3.1 Security Level
Cloudflare → Security → Settings
- Security Level: **Medium** or **High**
- Challenge Passage: **30 minutes**

### 3.2 Bot Fight Mode (Free)
Cloudflare → Security → Bots
- Enable **Bot Fight Mode**
- This blocks/challenges obvious bots automatically

### 3.3 Rate Limiting (Pro plan or above)
Cloudflare → Security → WAF → Rate limiting rules

Create rules for sensitive endpoints:

**Login Protection:**
```
Rule name: Limit login attempts
Expression: (http.request.uri.path eq "/api/auth/login")
Requests: 5 requests per 1 minute
Action: Block
Duration: 10 minutes
```

**Signup Protection:**
```
Rule name: Limit signups
Expression: (http.request.uri.path eq "/api/auth/signup")
Requests: 3 requests per 5 minutes
Action: Block
Duration: 30 minutes
```

**API Protection:**
```
Rule name: Limit API calls
Expression: (http.request.uri.path contains "/api/")
Requests: 100 requests per 1 minute
Action: Challenge (CAPTCHA)
```

### 3.4 Firewall Rules (Free)
Cloudflare → Security → WAF → Firewall rules

**Block known bad bots:**
```
Field: User Agent
Operator: contains
Value: curl
Action: Block
```

**Challenge suspicious traffic:**
```
Field: Threat Score
Operator: greater than
Value: 10
Action: Managed Challenge
```

**Protect sensitive endpoints:**
```
Expression: (http.request.uri.path eq "/admin") and (cf.threat_score gt 0)
Action: Managed Challenge
```

### 3.5 Super Bot Fight Mode (Pro plan)
If you have Pro plan:
- Cloudflare → Security → Bots
- Enable **Super Bot Fight Mode**
- Configure:
  - Definitely automated: **Block**
  - Verified bots: **Allow**
  - Likely automated: **Managed Challenge**

---

## Step 4: Configure SSL/TLS

Cloudflare → SSL/TLS
- SSL/TLS encryption mode: **Full (strict)**
- Enable:
  - Always Use HTTPS
  - Automatic HTTPS Rewrites
  - Opportunistic Encryption

---

## Step 5: Performance Settings

Cloudflare → Speed → Optimization
- Enable:
  - Auto Minify (JS, CSS, HTML)
  - Brotli compression
  - Rocket Loader (optional, test first)

Cloudflare → Caching → Configuration
- Caching Level: **Standard**
- Browser Cache TTL: **4 hours**

---

## Step 6: Block AI Crawlers (Optional)

Cloudflare → Security → WAF → Custom rules

```
Rule name: Block AI crawlers
Expression:
  (http.user_agent contains "GPTBot") or
  (http.user_agent contains "ChatGPT") or
  (http.user_agent contains "CCBot") or
  (http.user_agent contains "anthropic-ai") or
  (http.user_agent contains "Claude-Web") or
  (http.user_agent contains "cohere-ai")
Action: Block
```

---

## Step 7: Monitor Traffic

Cloudflare → Analytics → Security
- Monitor blocked requests
- Check threat types
- Adjust rules based on data

Cloudflare → Analytics → Traffic
- View requests by country, path, status
- Identify patterns

---

## Step 8: Configure on Railway

Update Railway environment variables:
```
APP_BASE_URL=https://yourdomain.com
FLASK_ENV=production
```

Your app will now receive:
- `CF-Connecting-IP` header (real client IP)
- `CF-Ray` header (Cloudflare request ID)
- `CF-IPCountry` header (client country)

---

## Testing

1. **Test legitimate traffic:**
   ```bash
   curl https://yourdomain.com
   # Should work normally
   ```

2. **Test bot detection:**
   ```bash
   curl -A "Mozilla/5.0 (compatible; BadBot/1.0)" https://yourdomain.com
   # May be blocked or challenged
   ```

3. **Test rate limiting:**
   - Make multiple rapid requests to /api/auth/login
   - Should be blocked after threshold

---

## Free vs Paid Plans

### Free Plan Includes:
- DDoS protection
- Bot Fight Mode (basic)
- Firewall rules (5 rules)
- SSL/TLS
- CDN
- Analytics

### Pro Plan ($20/month) Adds:
- Super Bot Fight Mode
- Rate limiting rules
- More firewall rules
- Better analytics
- Page rules

### Recommendations:
- Start with Free plan
- Add application-level rate limiting (Flask-Limiter)
- Upgrade to Pro if you need advanced bot protection

---

## Robots.txt

Place `robots.txt` in `legacy/static/robots.txt` and add route:

```python
@app.route('/robots.txt')
def robots():
    return send_from_directory('static', 'robots.txt')
```

---

## Best Practices

1. **Layered Defense:**
   - Cloudflare (edge protection)
   - Flask-Limiter (application-level)
   - Security headers (defense in depth)

2. **Monitor & Adjust:**
   - Check Cloudflare analytics weekly
   - Adjust firewall rules based on threats
   - Update rate limits as traffic grows

3. **Don't Over-Block:**
   - Start lenient, tighten gradually
   - Whitelist legitimate services (monitoring, etc.)
   - Test thoroughly before deploying strict rules

4. **Keep Updated:**
   - Review Cloudflare security recommendations
   - Update bot user agent patterns
   - Monitor new bot threats
