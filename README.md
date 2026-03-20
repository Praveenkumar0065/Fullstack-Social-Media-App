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
- Notifications page connected to backend endpoint
- Direct messages page connected to backend endpoint
- Demo/fallback data support

### Explore and Discovery
- Explore page with search input
- Trending/demo-backed discovery UI

### Profile and Account
- Profile page with name, email, and verification status
- Follow/Unfollow buttons in UI (frontend-only currently)

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

## Deployment

This project is configured for deployment on Render using render.yaml.

Main deployment steps:

1. Push code to GitHub
2. Create a Blueprint deploy on Render
3. Add MONGODB_URI
4. Deploy and verify /, /health, and /docs

Detailed deployment instructions are available in:

- DEPLOYMENT_RUNBOOK.md

## Screenshots

Add screenshots here:

- Landing page
- Login page
- Feed page
- Profile page
- Admin page
- API docs page

## Known Notes

- Follow/Unfollow is currently frontend-only
- Firebase auth is included as a template in mock/off mode
- Some discovery content uses demo/fallback rendering
- If MongoDB is not configured, the app may use in-memory fallback mode

## Author

Praveen Kumar

## Resume Project Summary

Developed and deployed a full-stack social media web application using FastAPI, MongoDB, and a SPA frontend with authentication, posts, saved posts, notifications, messaging, admin moderation, multilingual UI, and Render-based cloud deployment.
