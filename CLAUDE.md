# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Everything runs from `backend/`. On Windows use the repo venv at `venv/` (note: the venv lives at the repo root, `backend` is one level down).

```bash
# install (first time)
./venv/Scripts/python.exe -m pip install -r backend/requirements.txt

# run the server (serves site + admin + JSON API on :5000)
./venv/Scripts/python.exe backend/app.py

# run tests (plain unittest, no framework)
./venv/Scripts/python.exe backend/test_app.py
# single test:
./venv/Scripts/python.exe -m unittest test_app.TestClass.test_method   # cwd=backend
```

The admin password comes from `ADMIN_PASSWORD`. It is loaded from `backend/.env` via `load_dotenv` at import (default `admin` if unset). Editing `.env` requires a **server restart** — it is read once at import. HTML/JS edits do not need a restart, just a browser refresh.

## Architecture

Two decoupled halves, no build step:

- **`backend/app.py`** — a single-file FastAPI app (run with `uvicorn`, Starlette `SessionMiddleware` for the admin session). It is both the JSON API and the static file server for `frontend/`. SQLAlchemy models (`About`, `Writing`, `Book`, `Movie`, `Project`, `Note`) back a generic CRUD layer: all collections route through `/api/<section>` handlers driven by the `COLLECTIONS` dict (`section -> (model, ordered field list)`), so adding a field means editing the model + that dict, not adding routes. `About` is a singleton (row id=1) handled separately. `skills` is stored as a JSON string and (de)serialized in `Project.to_dict`/`apply_fields`. All writes are guarded by `@require_admin` (a single shared-password Flask session, `session["admin"]`). Uploads go to `frontend/uploads/` and are served at `/uploads/<file>`.

- **`frontend/*.dc.html`** — pages rendered by the **DC runtime** (`support.js`), a custom React-based template engine (no bundler; React/ReactDOM are loaded by `support.js`). Understanding this runtime is essential before touching any page:
  - `support.js` finds `<x-dc>`, **replaces it with a React-owned `<div id="dc-root">`**, and renders the compiled template there. Any DOM you inject *inside* `#dc-root` is wiped on re-render — inject siblings on `document.body` instead (this is why `particles.js` attaches to `body` and pages use `background:transparent` so the fixed canvas shows through).
  - Template syntax: `{{ expr }}` interpolation, `<sc-for list="{{ items }}" as="x">`, `<sc-if value="{{ cond }}">`, `style-hover="..."` for pseudo-classes. Page logic lives in the inline `<script type="text/x-dc" data-dc-script>` block as a `class Component extends DCLogic` with `state`, `componentDidMount`, and `renderVals()` (returns the values the template binds to).
  - **Boolean HTML attributes are a trap**: a bare attr like `loop` compiles to the React prop `loop=""`, which React (for known boolean props) treats as false and drops. Write `loop="true"` for those. Lowercase attrs React doesn't recognize (`autoplay`, `playsinline`) pass through as-is.
  - The served HTML contains raw `src="{{ ... }}"` placeholders; the browser eagerly fetches them (harmless 404s in console) before the runtime re-renders with real values.

- **`particles.js`** — standalone floating-particle canvas + cursor glow, self-injecting on `document.body`, shared by all subpages via `<script src="./particles.js" defer>`. The index page (`Usmonbek Anvarbekov.dc.html`) has its own in-component copy (`setupParticles`) instead, so it does not include this file.

## Routing

`app.py`'s `PAGES` dict maps clean slugs to template files (`/movies` -> `Movies.dc.html`, `/` -> index, `/admin` -> `admin.html`). The `/<path:name>` catch-all falls back to serving the raw filename, so old `*.dc.html` URLs still work. When adding a page, add its slug to `PAGES` and link to the slug, not the filename.

## Conventions

- Colors are hardcoded inline throughout: bg `#0B0B0C`, text `#EAE7DF`, accent/rust `#C6432B`.
- The admin panel (`admin.html`) is plain vanilla JS (no DC runtime). Its `SCHEMA` object mirrors `COLLECTIONS` on the backend — keep the two in sync.
