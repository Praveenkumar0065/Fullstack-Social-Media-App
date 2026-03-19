# Pixora — Full-Stack Social Media Web App

Pixora is a full-stack social media web application built for portfolio and learning purposes. It includes authentication, post creation, social feed interactions, saved posts, notifications, direct messages, admin moderation tools, and deployment-ready configuration.

## Features

### Authentication
- User sign up and login
- Backend auth endpoints for register/login
- Basic role support (`user` / `admin`)
- Optional Firebase auth template (currently mock/off mode)

### Social Feed and Posts
- Create posts with text and optional media URL
- View posts in newest-first order
- Like posts
- Comment on posts
- Delete posts

### Saved Posts
- Save a post
- Unsave a post
- View saved posts list

### Notifications and Messages
- Notifications page connected to backend endpoint
- Direct messages page connected to backend endpoint
- Demo/fallback data support

### Explore and Discovery
- Explore page with search input
- Demo trending/search-backed content rendering

### Profile and Account
- Profile page showing name, email, and verification state
- Follow/Unfollow buttons in UI (frontend-only currently)

### Admin Features
- Admin dashboard
- Flagged content list endpoint for moderation workflow

### UX and Platform Features
- SPA routing
- Theme toggle
- Language toggle (EN/ES)
- Client-side anti-spam/rate-limit behavior
- Mobile-responsive design

### Backend and Deployment
- FastAPI backend
- FastAPI docs at `/docs`
- Health check endpoint at `/health`
- MongoDB support
- In-memory fallback mode
- Seed/demo data setup
- Single-service Render deployment setup

## Tech Stack
- **Frontend:** SPA frontend
- **Backend:** FastAPI
- **Database:** MongoDB
- **Deployment:** Render
- **API Docs:** Swagger UI via FastAPI

## Current Status
This project is functional and deployment-ready for demo/portfolio usage.

### Implemented
- Authentication
- Posts/feed
- Likes/comments/delete
- Saved posts
- Notifications/messages
- Admin moderation endpoint
- Responsive frontend
- Render deployment support

### Planned / Partial
- Full backend follow/unfollow system
- Real Firebase authentication integration
- Expanded explore recommendation system
- Improved real-time messaging

## Local Setup

```bash
git clone https://github.com/Praveenkumar0065/Fullstack-Social-Media-App.git
cd Fullstack-Social-Media-App
```

Install backend dependencies and run the app based on your project structure.

## API Endpoints

- `/docs` — FastAPI Swagger docs
- `/health` — health check

## Deployment

This project is configured for Render deployment with a single-service setup.

## Screenshots

Add application screenshots here after deployment.

## Author

Praveen Kumar
