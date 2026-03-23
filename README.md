# SocialSphere - Full-Stack Social Media Web App

SocialSphere is a production-ready full-stack social media web application built for portfolio, learning, and deployment practice. It includes authentication, social feed features, saved posts, notifications, messaging, admin moderation support, multilingual UI, theming, and Render deployment.

## Live Demo
- App: https://socialsphere-app-wc5v.onrender.com
- Health Check: https://socialsphere-app-wc5v.onrender.com/health
- API Docs: https://socialsphere-app-wc5v.onrender.com/docs

## GitHub Repository
- https://github.com/Praveenkumar0065/Fullstack-Social-Media-App

## Features

### Authentication
- User sign up and login
- Backend authentication endpoints
- Basic role support (user, admin)
- Optional Firebase auth template in mock/off mode

### Social Feed
- Create posts with text and optional media URL
- View all posts in newest-first order
- Like posts
- Comment on posts
- Delete posts

### Saved Posts
- Save a post
- Unsave a post
- View saved posts list

### Notifications and Messages
- Notifications page connected to authenticated me-scoped endpoint
- Direct messages page connected to authenticated me-scoped endpoint
- Demo/fallback data support

### API Deprecation Notice
Legacy email-based endpoints for notifications and direct messages are deprecated and return HTTP 410.
Use authenticated me-scoped endpoints instead:
- GET /api/notifications/me
- GET /api/messages/me
- GET /api/users/me/social

### Explore and Discovery
- Explore page with search input
- Trending/demo-backed discovery UI

### Profile and Account
- Profile page with name, email, and verification status
- Follow/Unfollow system with backend authorization, rate limiting, and audit logging

### Admin Features
- Admin dashboard route/page
- Flagged content moderation endpoint

### UX and Platform Features
- Single Page Application routing
- Language toggle (EN/ES)
- Theme toggle
- Client-side anti-spam/rate-limit behavior
- Mobile-responsive UI

### Backend and Deployment
- FastAPI backend
- Swagger docs at /docs
- Health endpoint at /health
- MongoDB support
- In-memory fallback mode
- Seed/demo data support
- Single-service Render deployment

## Tech Stack
- Frontend: SPA frontend
- Backend: FastAPI
- Database: MongoDB
- Deployment: Render
- API Docs: FastAPI Swagger UI

## Project Structure
```bash
Fullstack-Social-Media-App/
|-- backend_code/
|-- frontend_code/
|-- frontend_react/
|-- render.yaml
|-- README.md
`-- DEPLOYMENT_RUNBOOK.md
```

## Current Status

This project is live and deployment-ready for portfolio/demo usage.

### Implemented

- Authentication
- Social feed and posts
- Likes, comments, delete
- Saved posts
- Notifications and messages
- Admin moderation endpoint
- Responsive UI
- Render deployment support

### Partial / Planned

- Full backend follow/unfollow system
- Full Firebase authentication integration
- Expanded recommendation/discovery system
- Improved real-time messaging

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/Praveenkumar0065/Fullstack-Social-Media-App.git
cd Fullstack-Social-Media-App
```

### 2. Configure environment variables

Create your environment file and add required values such as:

```env
MONGODB_URI=your_mongodb_connection_string
```

### 3. Run the backend

Install dependencies and run the FastAPI server based on the project structure.

### 4. Run backend tests

Install dev dependencies and run tests:

```bash
pip install -r backend_code/requirements-dev.txt
pytest -q backend_code/tests
```

## Deployment

This project is configured for deployment on Render using render.yaml.

For split hosting (Render backend + Vercel frontend):
- Backend: deploy API on Render and set MONGODB_URI to Atlas.
- Frontend: deploy frontend_react to Vercel.
- Set Vercel environment variable:
	- VITE_API_BASE = "https://your-backend.onrender.com/api"
- Set backend ALLOWED_ORIGINS to your Vercel domain.

Config templates provided:
- backend_code/.env.example
- frontend_code/deploy-config.example.js

Main deployment steps:

1. Push code to GitHub
2. Create a Blueprint deploy on Render
3. Add MONGODB_URI
4. Deploy and verify /, /health, and /docs

Detailed deployment instructions are available in:

- DEPLOYMENT_RUNBOOK.md

## Continuous Integration

This repository includes a GitHub Actions workflow at .github/workflows/backend-tests.yml.

It automatically runs on push and pull requests to main when backend files change, and executes:
- Backend test suite with coverage gate: pytest --cov=backend_code --cov-fail-under=60 -q backend_code/tests
- Backend compile check: python -m compileall backend_code
- Frontend syntax checks: node --check frontend_code/app.js and node --check frontend_code/firebase-config.js

This repository also includes .github/workflows/license-audit.yml.

It automatically runs on push and pull requests when dependency manifests or notice files change, and executes:
- Frontend install (frontend_react npm ci)
- Backend dependency install (pip install -r backend_code/requirements.txt)
- Dependency license validation (strict + whitelist + risk policy): python scripts/check_dependency_licenses.py --verify-notices --strict --allowed-license MIT --allowed-license Apache-2.0 --allowed-license BSD-3-Clause --allowed-license BSD --allowed-license Unlicense --allowed-license ISC --fail-on-risk medium
- Compliance report generation:
	- JSON: artifacts/license-compliance.json
	- HTML dashboard: artifacts/license-compliance.html
- Compliance artifact upload includes both JSON and HTML reports

This repository also includes .github/workflows/post-deploy-smoke.yml.

It can be run manually after deployment to execute scripts/smoke_test.ps1 against a live Render URL.
Use workflow inputs for base URL and optional checks (rate-limit and non-admin guard validation).

One-command local release checklist wrapper is available at scripts/release_checklist.ps1:
- Runs backend checks
- Runs frontend build
- Runs license audit + dashboard generation
- Runs smoke tests against the provided BaseUrl

For production release control, use .github/workflows/release-gate.yml (manual dispatch):
- Runs backend and frontend quality gates
- Requires smoke_test_confirmed=yes input before tag/release creation
- Requires semantic version input (X.Y.Z) that matches the root VERSION file
- Requires release notes file: release-notes/v<version>.md
- Validates required sections in release notes: Summary, Changes, Migration Notes, Validation
- Auto-updates CHANGELOG.md from commit history
- Creates annotated git tag and GitHub release (v<version>) only after checks pass

Optional release-gate inputs:
- docker_build: build Docker image in workflow
- docker_push: push image to Docker Hub
- auto_deploy: trigger Render/Railway deploy webhooks
- notify_after_release: send webhook notification after release

Optional secrets for advanced automation:
- DOCKERHUB_USERNAME, DOCKERHUB_TOKEN (Docker push)
- RENDER_DEPLOY_HOOK_URL (Render auto deploy)
- RAILWAY_DEPLOY_HOOK_URL (Railway auto deploy)
- RELEASE_NOTIFY_WEBHOOK_URL (Slack/Email webhook relay)

Release notes format guidance is available in release-notes/README.md.
Use release-notes/TEMPLATE.md as the starting point for each release note file.
A ready-to-use example is provided at release-notes/v1.0.0.md.

Release prep helper:
- Run: python scripts/release_prep.py X.Y.Z
- This updates VERSION and creates release-notes/vX.Y.Z.md from template.
- Use --notes-only to scaffold notes without changing VERSION.
- Use --force to overwrite an existing release-notes file.
- Use --dry-run to preview changes without modifying files.
- Use --major / --minor / --patch to auto-bump from current VERSION.
- Script blocks when git working tree is dirty (use --allow-dirty to bypass).
- Script blocks if tag vX.Y.Z already exists.
- Use --commit to auto-stage and commit VERSION + release notes.
- Use --open to open the generated release notes file for editing.

CI also runs release-tooling unit tests from tests/test_release_prep.py.

## Third-Party Notices

Dependency license inventory is documented in THIRD_PARTY_NOTICES.md.

## Screenshots

Add screenshots here:

- Landing page
- Login page
- Feed page
- Profile page
- Admin page
- API docs page

### Known Notes

- Firebase auth is included as a template in mock/off mode
- Some discovery content uses demo/fallback rendering
- If MongoDB is not configured, the app may use in-memory fallback mode

## Author

Praveen Kumar

## Resume Project Summary

Developed and deployed a full-stack social media web application using FastAPI, MongoDB, and a SPA frontend with authentication, posts, saved posts, notifications, messaging, admin moderation, multilingual UI, and Render-based cloud deployment.
