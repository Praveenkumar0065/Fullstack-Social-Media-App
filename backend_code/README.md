# Pixora Backend

FastAPI backend for the Pixora full-stack social media app.

## Endpoints

- `GET /` root info
- `GET /health` health check
- `GET /api/info` API capabilities
- `GET /api/status` API status
- `POST /api/auth/signup` register user
- `POST /api/auth/login` login user
- `GET /api/posts` list posts
- `POST /api/posts` create post
- `POST /api/posts/{post_id}/like` like post
- `POST /api/posts/{post_id}/comment` add comment
- `POST /api/posts/{post_id}/save` save post
- `POST /api/posts/{post_id}/unsave` unsave post
- `GET /api/posts/saved` list saved posts
- `DELETE /api/posts/{post_id}` delete post
- `GET /api/notifications/{email}` list notifications
- `GET /api/messages/{email}` list direct messages
- `GET /api/admin/flagged` get flagged content list

## Run

1. Install dependencies:
   - `python -m pip install -r requirements.txt`
2. Create `.env` file in `backend_code`:
   - `MONGODB_URI=mongodb://localhost:27017`
   - `MONGODB_DB=socialsphere`
   - Optional: `ALLOWED_ORIGINS=http://localhost:5500`
3. Start MongoDB local service (or MongoDB Atlas URI).
4. Start server:
   - `python -m uvicorn main:app --reload`
5. Open docs:
   - `http://127.0.0.1:8000/docs`

## MongoDB Compass

1. Open Compass and connect using the same URI you place in `.env`.
2. Open database `socialsphere` (or your `MONGODB_DB` value).
3. You will see collections created automatically:
   - `users`
   - `posts`
   - `notifications`
   - `messages`

## Run (without Mongo)

If `MONGODB_URI` is not set or connection fails, the backend falls back to in-memory demo mode.

## Demo Accounts

- Admin:
  - email: `admin@socialsphere.app`
  - password: `admin123`

## Notes

- With Mongo connected, data is persistent and visible in Compass.
- Without Mongo, data is in-memory and resets on server restart.

## Deploy

### Option A: Render (recommended)

1. Push this project to GitHub.
2. In Render, create a new Blueprint and select your repository.
3. Render will detect `render.yaml`.
4. Add environment variable `MONGODB_URI` in Render dashboard.
5. Keep `MONGODB_DB=socialsphere` (already set in `render.yaml`).
6. Click deploy.
7. Open `https://<your-render-domain>/` for frontend and `https://<your-render-domain>/docs` for API docs.

This deployment serves frontend and backend from one service:
- Frontend at `/`
- API at `/api/*`

### Option B: Docker anywhere

From project root:

1. Build image:
   - `docker build -f backend_code/Dockerfile -t socialsphere-app .`
2. Run container:
   - `docker run -p 8000:8000 --env-file backend_code/.env socialsphere-app`
