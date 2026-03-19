# Fullstack-Social-Media-App

Production-ready full-stack social media web app built with FastAPI, SPA frontend, MongoDB, authentication, posts, saved posts, notifications, messaging, admin moderation, and Render deployment support.

## Pixora - Full-Stack Social Media Web App

Pixora is a full-stack social media web application built for portfolio and learning purposes. It includes authentication, post creation, social feed interactions, saved posts, notifications, direct messages, admin moderation tools, and deployment-ready configuration.

## Project Summary
Built a full-stack social media web application with user authentication, post creation, likes, comments, saved posts, notifications, messaging, admin moderation, and cloud deployment support using FastAPI, MongoDB, and a responsive SPA frontend.

## Features

### Authentication
- User sign up and login
- Backend auth endpoints for register/login
- Basic role support (user/admin)
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
- FastAPI docs at /docs
- Health check endpoint at /health
- MongoDB support
- In-memory fallback mode
- Seed/demo data setup
- Single-service Render deployment setup

## Tech Stack
- Frontend: SPA frontend (HTML, CSS, JavaScript)
- Backend: FastAPI (Python)
- Database: MongoDB
- Deployment: Render
- API Docs: Swagger UI via FastAPI

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

### Planned or Partial
- Full backend follow/unfollow system
- Real Firebase authentication integration
- Expanded explore recommendation system
- Improved real-time messaging

## Local Setup

1. Clone the repository:
   - git clone https://github.com/YOUR_USERNAME/Fullstack-Social-Media-App.git
2. Go into the project folder:
   - cd Fullstack-Social-Media-App
3. Backend setup:
   - cd backend_code
   - python -m pip install -r requirements.txt
   - python -m uvicorn main:app --reload
4. Frontend local run (optional separate static server):
   - cd ../frontend_code
   - python -m http.server 5500

## API Endpoints
- /docs - FastAPI Swagger docs
- /health - health check

## Deployment
This project is configured for Render deployment with a single-service setup using render.yaml.

## Resume Bullets
- Developed a full-stack social media web application with FastAPI backend and responsive SPA frontend.
- Implemented user authentication, role-based access, post creation, likes, comments, saved posts, and admin moderation endpoints.
- Integrated MongoDB support with fallback demo mode and prepared the application for cloud deployment on Render.
- Designed mobile-responsive UI with theme toggle, language toggle, notifications, messages, and profile workflows.

## Tagline
A deployment-ready full-stack social platform with core social features, admin workflow, and responsive user experience.

## Author
Praveen Kumar
