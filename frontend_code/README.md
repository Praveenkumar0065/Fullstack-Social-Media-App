# SocialSphere Full-Stack Frontend

SPA frontend for the SocialSphere app, connected to a FastAPI backend.

## Pages
- `/` Landing Page (Header, Hero, Auth Buttons)
- `/login` Login
- `/feed` Personalized feed (PostList, StoriesBar)
- `/explore` Search + ExploreGrid
- Additional: `/signup`, `/profile`, `/notifications`, `/messages`, `/admin`

## Features included
- Public registration + email verification messaging
- Secure login flow (FastAPI auth + optional Firebase template)
- Profiles, posts CRUD, likes/comments, save posts UI
- Explore/search users & hashtags (API-backed demo)
- Notifications and direct messaging from backend demo data
- Admin dashboard + content moderation from backend endpoint
- Spam protection (client-side rate limiting)
- Multi-language (EN/ES)
- Mobile responsive and global-ready UI

## Run (with backend)
1. Start backend API from the `backend_code` folder:
   - `python -m pip install -r requirements.txt`
   - `python -m uvicorn main:app --reload`
2. In another terminal, start static frontend server from `frontend_code`:
   - `python -m http.server 5500`
3. Open `http://localhost:5500`
4. Frontend calls backend at `http://127.0.0.1:8000/api` by default.

## Deploy (Render, single service)
1. Push the full project to GitHub.
2. In Render, create a Blueprint deployment from the repository.
3. Render uses `render.yaml` and `backend_code/Dockerfile`.
4. Add `MONGODB_URI` as a secret environment variable.
5. Deploy and open your Render URL.

In production, frontend and backend are served from the same domain:
- Frontend: `/`
- API: `/api/*`

The frontend auto-detects this and uses `${location.origin}/api` when not running on local port `5500`.

## Default Admin Login
- Email: `admin@socialsphere.app`
- Password: `admin123`

## Firebase (optional)
- Fill `firebase-config.js` with your project credentials and set `firebaseReady = true`.
- Replace auth calls with modular methods as needed.

## Notes
- The backend currently uses in-memory storage for fast local development.
- For production, replace in-memory stores with a database and hashed passwords.