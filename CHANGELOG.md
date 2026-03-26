# Changelog

All notable changes to this project are documented in this file.

This changelog is automatically prepended during release workflow runs.

## Unreleased
- No unreleased changes.

## v1.0.2 - 2026-03-26
- Polished login/signup UI with closer split-panel styling, refined spacing, and improved mobile/desktop presentation.
- Added invite and onboarding frontend routes/pages and integrated referral-aware signup UX.
- Hardened backend auth request validation by requiring proper email format for signup/login payloads.
- Refactored repeated authenticated user email extraction into a shared helper for cleaner protected-route checks.
- Added focused backend regression coverage for signup validation and growth/onboarding flows.
- Fixed backend DB initialization regression causing auth login 500s during smoke verification.
- Aligned app version metadata to 1.0.2 across backend defaults, environment template, and Render blueprint.
- Added custom workspace agents for fullstack maintenance, release gatekeeping, security review, and frontend UX polish.

## v1.0.1 - 2026-03-23
- Added PBKDF2-SHA256 password hashing with compatibility/migration for legacy credentials.
- Added optional Sentry monitoring integration with safe fallback when SDK is absent.
- Improved frontend performance via lazy route loading, Suspense fallback, and Vite chunking strategy.
- Added global launch guide for custom domain deployment and production runbooks.
- Stabilized authenticated post-flow test coverage; backend test suite now fully passing.

## v1.0.0 - 2026-03-23
- Initial production-ready release with chat, notifications, PWA, release pipeline, and deployment automation.
