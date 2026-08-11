---
description: "Project-specific guidance for the VFX Show Tracker Flask app. Apply when editing files in this repository."
applyTo: "**/*.{py,html,css,js,md,txt}"
---

# VFX Show Tracker Project Instructions

## Project context
This repository contains a Flask application for tracking VFX shows, sequences, shots, artists, and activity history. The main application logic is in app.py, and the UI uses Jinja templates plus static assets.

## Preferred approach
- Keep changes focused and compatible with the existing Flask + SQLAlchemy structure.
- Preserve the current data model patterns and route organization unless a user explicitly asks for a broader refactor.
- When changing backend behavior, check whether the templates or frontend scripts depend on the response shape.
- Prefer small, maintainable edits over large rewrites.

## Coding conventions
- Use clear, descriptive names for routes, helpers, and variables.
- Keep existing JSON and database field naming patterns consistent with the current code.
- Avoid introducing new dependencies unless the user asks for them.
- When adding new UI controls, make sure the related backend endpoints and template hooks remain aligned.

## Validation expectations
- Verify syntax or basic runtime health after relevant edits.
- If a change affects templates or routes, check that the app still loads without obvious errors.
- Do not claim the work is complete without some form of verification.
