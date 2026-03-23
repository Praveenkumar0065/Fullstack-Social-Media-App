# Deployment Runbook (Render)

This runbook is for deploying Fullstack-Social-Media-App to Render using the existing Blueprint setup.

## Prerequisites
- GitHub repository is up to date
- Render account is connected to GitHub
- MongoDB connection string is ready (Atlas or hosted MongoDB)

## Quick Start (Do This First)
1. Copy backend env template values from backend_code/.env.example.
2. Set Render environment values from that template (especially MONGODB_URI, ALLOWED_ORIGINS, AUTH_TOKEN_SECRET).
3. In frontend_react/.env set:
  - VITE_API_BASE="https://<your-render-service>.onrender.com/api"
4. Build frontend_react so backend can serve the generated dist bundle:
  - npm --prefix frontend_react ci
  - npm --prefix frontend_react run build

## Deploy Steps (Blueprint)
1. Open Render Dashboard.
2. Click New and select Blueprint.
3. Select repository:
   - https://github.com/Praveenkumar0065/Fullstack-Social-Media-App
4. Confirm Render detects render.yaml.
5. In environment variables, set:
   - MONGODB_URI = <your-mongodb-uri>
6. Confirm service settings:
   - Web service name: socialsphere-app
   - Environment: Docker
   - Health check: /health
7. Click Deploy.

## Expected Routes After Deploy
- Frontend: /
- API docs: /docs
- API base: /api
- Health: /health

## Post-Deploy Verification Checklist
1. Open / and confirm landing page loads.
2. Open /health and confirm status response.
3. Open /docs and confirm FastAPI docs are visible.
4. Sign up a user from the UI.
5. Log in and create a post.
6. Like the post.
7. Comment on the post.
8. Save and unsave the post.
9. Open notifications and messages pages.

## Production Smoke-Test Checklist (Render)

Run these checks immediately after each production deploy. Replace <BASE_URL> with your Render URL.

### Fast Path (Automated)
Use the automation script to run the key checks end-to-end:

  - powershell -ExecutionPolicy Bypass -File scripts/smoke_test.ps1 -BaseUrl https://<your-render-service>.onrender.com
- One-command deploy verification using VERSION file:
  - powershell -ExecutionPolicy Bypass -File scripts/post_deploy_verify.ps1 -BaseUrl https://<your-render-service>.onrender.com
- With explicit non-admin guard validation:
  - powershell -ExecutionPolicy Bypass -File scripts/smoke_test.ps1 -BaseUrl https://<your-render-service>.onrender.com -UserEmail <non-admin-email> -UserPassword <non-admin-password>
  - powershell -ExecutionPolicy Bypass -File scripts/smoke_test.ps1 -BaseUrl https://<your-render-service>.onrender.com -RunRateLimit
### Fast Path (GitHub Actions Manual Run)
Use manual workflow dispatch to run smoke checks from CI against your live Render URL:

Workflow:
- .github/workflows/post-deploy-smoke.yml

Required input:
- base_url = https://<your-render-service>.onrender.com

Optional workflow flags:
- run_rate_limit = yes/no
- run_non_admin_check = yes/no

Optional secrets for workflow:
- SMOKE_ADMIN_EMAIL
- SMOKE_ADMIN_PASSWORD
- SMOKE_USER_EMAIL (required when run_non_admin_check=yes)
- SMOKE_USER_PASSWORD (required when run_non_admin_check=yes)

### One-Command Release Checklist Wrapper
Run build checks + license compliance + smoke tests in one command:

- powershell -ExecutionPolicy Bypass -File scripts/release_checklist.ps1 -BaseUrl https://<your-render-service>.onrender.com

Useful flags:
- -UserEmail <non-admin-email> -UserPassword <non-admin-password>
- -RunRateLimit
- -SkipBackendTests
- -SkipFrontendBuild
- -SkipLicenseAudit
- -DryRun

Script coverage:
- /health and /docs availability
- admin login + token issue
- protected me-scoped access with bearer token
- refresh-token rotation and old-token replay rejection
- admin guard (200 for admin and 403 for non-admin when non-admin credentials are provided)
- legacy endpoint deprecation (410)
- logout with rotated refresh token

### 1) Health and Docs
- GET <BASE_URL>/health returns 200 and {"status":"healthy"}
- GET <BASE_URL>/docs returns 200

### 2) Auth and Token Rotation
1. Login with admin account:
  - POST <BASE_URL>/api/auth/login
  - body: {"email":"admin@socialsphere.app","password":"admin123"}
2. Verify access token on protected route:
  - GET <BASE_URL>/api/users/me/social with Authorization: Bearer <access_token>
3. Rotate refresh token:
  - POST <BASE_URL>/api/auth/refresh with body {"refresh_token":"<refresh_token>"}
4. Replay old refresh token:
  - POST /api/auth/refresh with old refresh token must return 401

### 3) Admin Guard
- Call GET <BASE_URL>/api/admin/audit-logs with:
  - admin token: expect 200
  - non-admin token: expect 403

### 4) Rate Limits
- Login rate limit: trigger repeated invalid logins and confirm HTTP 429 is eventually returned.
- Follow rate limit: perform rapid follow/unfollow actions and confirm HTTP 429 is returned.

### 5) Legacy Endpoint Deprecation
- Confirm deprecated email-based routes return HTTP 410:
  - GET /api/users/{email}/social
  - GET /api/notifications/{email}
  - GET /api/messages/{email}

### 6) Realtime and Persistence
- Join chat room from two sessions and verify messages broadcast in real-time.
- Reload and confirm room history persists from /api/chat/messages/{room_id}.
- Verify follow and chat actions create entries in /api/admin/audit-logs.

## Troubleshooting
- Build fails:
  - Confirm backend_code/Dockerfile exists and is valid.
- App boots but data is not persistent:
  - Verify MONGODB_URI is set correctly in Render.
- CORS issue:
  - Confirm ALLOWED_ORIGINS value in Render env vars if needed.
- Health check failing:
  - Verify /health route returns HTTP 200.

## Rollback
1. In Render service, open Deploys tab.
2. Select the previous successful deploy.
3. Click Redeploy.

## Release Gate Workflow

Before creating a production release tag, run GitHub Actions workflow:
- .github/workflows/release-gate.yml

Recommended prep command before dispatch:
- python scripts/release_prep.py X.Y.Z

Advanced helper options:
- python scripts/release_prep.py --patch
- python scripts/release_prep.py --minor
- python scripts/release_prep.py --major
- add --commit to auto-commit prep files
- add --open to open generated release notes immediately

Required inputs:
- version: semantic version without prefix (example: 1.2.0)
- smoke_test_confirmed: set to yes only after completing this runbook's smoke-test checklist
- docker_build: yes/no
- docker_push: yes/no
- auto_deploy: yes/no
- notify_after_release: yes/no

Version governance:
- version input must follow X.Y.Z
- version input must exactly match the root VERSION file

Required file before dispatch:
- release-notes/v<version>.md (must exist and be non-empty)
- required headings in that file:
  - ## Summary
  - ## Changes
  - ## Migration Notes
  - ## Validation

Behavior:
- If quality checks fail, release is blocked.
- If version format is invalid or mismatched with VERSION file, release is blocked.
- If release notes file is missing/empty, release is blocked.
- If release notes required headings are missing, release is blocked.
- If smoke_test_confirmed is no, release is blocked intentionally.
- If checks pass and smoke_test_confirmed is yes, workflow creates:
  - changelog update in CHANGELOG.md from commit history
  - annotated git tag v<version>
  - GitHub Release using release-notes/v<version>.md as release body

Optional automation (when enabled + secrets configured):
- Docker build and push
- Render/Railway deploy-hook trigger
- Post-release webhook notification

Optional secrets:
- DOCKERHUB_USERNAME, DOCKERHUB_TOKEN
- RENDER_DEPLOY_HOOK_URL
- RAILWAY_DEPLOY_HOOK_URL
- RELEASE_NOTIFY_WEBHOOK_URL

## Notes
- The app supports MongoDB persistence and in-memory fallback mode.
- Firebase auth is optional and currently mock/off mode.

## Multi-User Global Deployment (Render + Vercel + Atlas)

This setup enables multiple users from different locations to use the app through shared cloud infrastructure.

### 1) Deploy Backend on Render
1. Deploy using render.yaml blueprint.
2. Set required backend env vars:
  - MONGODB_URI=<MongoDB Atlas connection string>
  - MONGODB_DB=socialsphere
  - AUTH_TOKEN_SECRET=<long random secret>
3. Set CORS to your frontend origin(s):
  - ALLOWED_ORIGINS=https://your-frontend.vercel.app
  - For multiple origins, use comma-separated values.
4. Verify:
  - https://your-backend.onrender.com/health
  - https://your-backend.onrender.com/docs

### 2) Use MongoDB Atlas (Central Shared DB)
1. Create Atlas cluster and database user.
2. Add Render egress or 0.0.0.0/0 (temporary) in Atlas Network Access.
3. Use Atlas URI in Render MONGODB_URI.
4. Confirm users/posts/messages persist across sessions/devices.

### 3) Deploy Frontend on Vercel
1. Import repository into Vercel.
2. Set root directory to frontend_react.
3. Build command: npm run build. Output directory: dist.
4. Configure frontend API target in Vercel environment variables:
  - VITE_API_BASE=https://your-backend.onrender.com/api
5. Redeploy and verify login/feed/profile/chat work against Render backend.

### 4) Final Connectivity Check
1. User A signs up from one network/location.
2. User B logs in from another location/device.
3. Validate shared data behavior:
  - Follow/unfollow changes are visible across accounts.
  - Posts/comments persist and are visible to others.
  - Notifications/messages are scoped correctly.
