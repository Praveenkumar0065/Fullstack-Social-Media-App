# Deployment Runbook (Render)

This runbook is for deploying Fullstack-Social-Media-App to Render using the existing Blueprint setup.

## Prerequisites
- GitHub repository is up to date
- Render account is connected to GitHub
- MongoDB connection string is ready (Atlas or hosted MongoDB)

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

## Notes
- The app supports MongoDB persistence and in-memory fallback mode.
- Follow/Unfollow is UI-only currently.
- Firebase auth is optional and currently mock/off mode.
