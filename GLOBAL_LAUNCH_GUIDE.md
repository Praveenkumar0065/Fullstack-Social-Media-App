# Global Launch Guide: Complete 5-Step Production Upgrade

This guide completes all 5 next-level items in one sequence for this repository.

## 1) Custom Domain Setup (Render + Vercel)

### Backend domain on Render
1. Open Render service dashboard.
2. Go to **Settings -> Custom Domains**.
3. Add `api.yourdomain.com`.
4. Add the DNS records Render provides in your domain registrar.
5. Wait for TLS certificate to become active.

### Frontend domain on Vercel
1. Open Vercel project.
2. Go to **Settings -> Domains**.
3. Add `app.yourdomain.com` and/or `yourdomain.com`.
4. Apply the DNS records shown by Vercel.
5. In Vercel env vars set:

```bash
VITE_API_BASE=https://api.yourdomain.com/api
```

### CORS for custom domain
Set backend env var in Render:

```bash
ALLOWED_ORIGINS=https://app.yourdomain.com,https://yourdomain.com
```

## 2) Authentication Security Upgrade (Implemented)

Implemented in backend code:
- Password hashing with PBKDF2-SHA256 (`AUTH_PASSWORD_ITERATIONS` configurable).
- Password verification using constant-time compare.
- Legacy plaintext password compatibility with automatic migration to hashed passwords on successful login.
- Access/refresh token TTL already enforced and refresh rotation already present.

Operational notes:
- Keep `AUTH_TOKEN_SECRET` long and random.
- Rotate secret if previously exposed.
- Do not use the default secret in production.

## 3) Monitoring and Error Tracking (Implemented)

Implemented in backend code:
- Optional Sentry initialization using `SENTRY_DSN`.
- Trace sampling controlled by `SENTRY_TRACES_SAMPLE_RATE`.
- Environment and release context included (`APP_ENV`, `APP_VERSION`).

Set these in Render to enable:

```bash
SENTRY_DSN=<your-dsn>
SENTRY_TRACES_SAMPLE_RATE=0.1
APP_ENV=production
```

## 4) Performance Optimization (Implemented)

Implemented in frontend build/app:
- Route-level lazy loading for major pages.
- Suspense fallback while chunks load.
- Vite manual chunk splitting for better browser cache reuse.
- Source maps enabled for production debugging.

Recommended check:

```bash
cd frontend_react
npm run build
```

## 5) PWA Installability (Implemented)

Already present and production-ready in this repo:
- Manifest file with standalone display mode.
- Service worker registration in app bootstrap.
- Static asset caching with API-cache bypass to avoid stale auth/data.
- Install prompt available in supported browsers.

Verification checklist:
1. Open deployed app in Chrome.
2. Check install icon in address bar.
3. Install app and reopen from app launcher.
4. Confirm core shell loads with limited connectivity.

## Final Release Verification

Run these after deployment:

```bash
powershell -ExecutionPolicy Bypass -File scripts/release_checklist.ps1 -BaseUrl https://api.yourdomain.com
```

Manual sanity checks:
- Signup/login
- Post creation and image upload
- Messaging and read/delivered markers
- Notifications
- Dark mode and responsive layout
- PWA install

## Security Checklist

- Keep `.env` files out of git.
- Rotate any previously exposed keys/secrets.
- Use separate credentials for local/dev/prod.
- Restrict CORS to exact frontend domains in production.
