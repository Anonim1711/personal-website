# Backend

Serves `../frontend`, stores all site content in a database, and lets you edit
everything from `/admin.html` behind a password.

## Run

```bash
pip install -r requirements.txt

# Windows (PowerShell)
$env:ADMIN_PASSWORD="your-password"; python app.py
# Windows (cmd)
set ADMIN_PASSWORD=your-password && python app.py
# POSIX
ADMIN_PASSWORD=your-password python app.py
```

Then open http://localhost:5000/ (public site) or
http://localhost:5000/admin.html (editor — log in with ADMIN_PASSWORD).

## Config (env vars)

- `ADMIN_PASSWORD` — password for the admin panel (default `admin`).
- `SECRET_KEY` — Flask session key (a random one is used if unset; set a fixed
  value in production so sessions survive restarts).
- `DATABASE_URL` — defaults to `sqlite:///content.db`. For Postgres:
  `postgresql+psycopg://user:pass@host/dbname`.

Uploaded photos/videos are saved to `../frontend/uploads/` and served at
`/uploads/<file>`.

## Test

```bash
python test_app.py
```
