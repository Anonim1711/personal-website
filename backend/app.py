"""Admin backend for the personal website.

Serves the static frontend/, exposes a JSON content API, handles photo/video
uploads, and guards all writes behind a single shared password (ADMIN_PASSWORD).

Run:  set ADMIN_PASSWORD=secret && python app.py   (Windows)
      ADMIN_PASSWORD=secret python app.py            (POSIX)
DB:   defaults to sqlite:///content.db; set DATABASE_URL=postgresql+psycopg://...
"""
import json
import os
import secrets
from pathlib import Path

import nh3

from fastapi import FastAPI, Request, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from starlette.middleware.sessions import SessionMiddleware
from werkzeug.utils import secure_filename
from sqlalchemy import create_engine, String, Text, Integer
from sqlalchemy.orm import (DeclarativeBase, Mapped, mapped_column,
                            sessionmaker)

FRONTEND = (Path(__file__).resolve().parent.parent / "frontend")
UPLOADS = FRONTEND / "uploads"
UPLOADS.mkdir(exist_ok=True)

ALLOWED = {  # ext -> is this an image (vs video)
    ".jpg": 1, ".jpeg": 1, ".png": 1, ".gif": 1, ".webp": 1, ".avif": 1,
    ".mp4": 0, ".webm": 0, ".mov": 0,
}

from dotenv import load_dotenv
load_dotenv(Path(__file__).with_name(".env"))

app = FastAPI()
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
    https_only=bool(os.environ.get("RAILWAY_ENVIRONMENT")),  # Secure cookie in prod
)
# No insecure default: the repo is public, so a missing password must fail loudly
# rather than silently accept "admin".
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    raise RuntimeError("ADMIN_PASSWORD is not set (put it in backend/.env locally, "
                       "or a Railway variable in prod)")

DB_URL = os.environ.get("DATABASE_URL", "sqlite:///content.db")
# Railway/Heroku hand out bare "postgresql://"; psycopg3 needs the +psycopg driver.
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DB_URL.startswith("postgresql://"):
    DB_URL = DB_URL.replace("postgresql://", "postgresql+psycopg://", 1)
engine = create_engine(DB_URL)
Session = sessionmaker(engine)


class Base(DeclarativeBase):
    pass


class About(Base):  # single row (id=1)
    __tablename__ = "about"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, default="")
    photo: Mapped[str] = mapped_column(String(500), default="")
    location: Mapped[str] = mapped_column(String(200), default="")

    def to_dict(self):
        return {"id": self.id, "text": self.text, "photo": self.photo,
                "location": self.location}


ABOUT_FIELDS = ["text", "photo", "location"]


class Writing(Base):
    __tablename__ = "writing"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    photo: Mapped[str] = mapped_column(String(500), default="")
    title: Mapped[str] = mapped_column(String(300), default="")
    text: Mapped[str] = mapped_column(Text, default="")

    def to_dict(self):
        return {"id": self.id, "photo": self.photo, "title": self.title,
                "text": self.text}


class Book(Base):
    __tablename__ = "book"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cover: Mapped[str] = mapped_column(String(500), default="")
    author: Mapped[str] = mapped_column(String(300), default="")
    name: Mapped[str] = mapped_column(String(300), default="")
    review: Mapped[str] = mapped_column(Text, default="")

    def to_dict(self):
        return {"id": self.id, "cover": self.cover, "author": self.author,
                "name": self.name, "review": self.review}


class Movie(Base):
    __tablename__ = "movie"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video: Mapped[str] = mapped_column(String(500), default="")
    name: Mapped[str] = mapped_column(String(300), default="")
    author: Mapped[str] = mapped_column(String(300), default="")
    review: Mapped[str] = mapped_column(Text, default="")

    def to_dict(self):
        return {"id": self.id, "video": self.video, "name": self.name,
                "author": self.author, "review": self.review}


class Project(Base):
    __tablename__ = "project"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300), default="")
    release_date: Mapped[str] = mapped_column(String(100), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    skills: Mapped[str] = mapped_column(Text, default="[]")  # JSON list

    def to_dict(self):
        try:
            skills = json.loads(self.skills or "[]")
        except ValueError:
            skills = []
        return {"id": self.id, "title": self.title,
                "release_date": self.release_date,
                "description": self.description, "skills": skills}


class Note(Base):
    __tablename__ = "note"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, default="")

    def to_dict(self):
        return {"id": self.id, "text": self.text}


class Link(Base):  # footer contact links (label + display value + url)
    __tablename__ = "link"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str] = mapped_column(String(100), default="")
    value: Mapped[str] = mapped_column(String(300), default="")
    url: Mapped[str] = mapped_column(String(500), default="")

    def to_dict(self):
        return {"id": self.id, "label": self.label, "value": self.value,
                "url": self.url}


Base.metadata.create_all(engine)


def _ensure_columns():
    # no migration framework; add any About columns missing from an older DB
    from sqlalchemy import inspect, text as sqltext
    have = {c["name"] for c in inspect(engine).get_columns("about")}
    with engine.begin() as conn:
        for col in ("location",):
            if col not in have:
                conn.execute(sqltext(
                    f'ALTER TABLE about ADD COLUMN {col} VARCHAR DEFAULT \'\''))


_ensure_columns()

# section name -> (model, ordered field list). About is handled separately.
COLLECTIONS = {
    "writing": (Writing, ["photo", "title", "text"]),
    "books": (Book, ["cover", "author", "name", "review"]),
    "movies": (Movie, ["video", "name", "author", "review"]),
    "projects": (Project, ["title", "release_date", "description", "skills"]),
    "notes": (Note, ["text"]),
    "links": (Link, ["label", "value", "url"]),
}


def require_admin(request: Request):
    if not request.session.get("admin"):
        raise HTTPException(401)


async def json_body(request: Request):
    try:
        return await request.json()
    except Exception:
        return {}


def delete_uploads(d):
    # remove any /uploads/<file> the record referenced (video, photo, cover)
    for v in d.values():
        if isinstance(v, str) and v.startswith("/uploads/"):
            f = (UPLOADS / Path(v).name)
            if f.is_file():
                f.unlink()


# fields holding rich HTML from the admin's WYSIWYG editor — sanitized on write so
# stored HTML is safe for every reader (the single trust boundary). These names are
# unique to long-form content; short fields are title/name/author/etc.
RICH_FIELDS = {"text", "review", "description"}


def apply_fields(obj, data, fields):
    for f in fields:
        if f not in data:
            continue
        val = data[f]
        if f == "skills":  # stored as JSON string
            val = json.dumps(val if isinstance(val, list) else [])
        elif f in RICH_FIELDS and isinstance(val, str):
            val = nh3.clean(val)
        setattr(obj, f, val)


# ---- auth ----
@app.post("/api/login")
async def login(request: Request):
    pw = (await json_body(request)).get("password") or ""
    if secrets.compare_digest(pw, ADMIN_PASSWORD):
        request.session["admin"] = True
        return {"ok": True}
    raise HTTPException(401)


@app.post("/api/logout")
async def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@app.get("/api/me")
async def me(request: Request):
    return {"admin": bool(request.session.get("admin"))}


# ---- uploads ----
@app.post("/api/upload")
async def upload(request: Request, file: UploadFile | None = None):
    require_admin(request)
    if not file or not file.filename:
        raise HTTPException(400)
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(400, "unsupported file type")
    # unique, safe name
    name = secure_filename(file.filename) or ("f" + ext)
    dest = UPLOADS / name
    i = 1
    while dest.exists():
        dest = UPLOADS / f"{dest.stem.rstrip('0123456789_') or 'f'}_{i}{ext}"
        i += 1
    dest.write_bytes(await file.read())
    return {"url": f"/uploads/{dest.name}"}


# ---- About (singleton) ----
@app.get("/api/about")
async def get_about():
    with Session() as s:
        row = s.get(About, 1)
        return row.to_dict() if row else {
            "id": 1, "text": "", "photo": "", "location": ""}


@app.put("/api/about")
async def put_about(request: Request):
    require_admin(request)
    data = await json_body(request)
    with Session() as s:
        row = s.get(About, 1) or About(id=1)
        apply_fields(row, data, ABOUT_FIELDS)
        s.add(row)
        s.commit()
        return row.to_dict()


# ---- collections (generic CRUD) ----
@app.get("/api/{section}")
async def list_section(section: str):
    if section not in COLLECTIONS:
        raise HTTPException(404)
    model, _ = COLLECTIONS[section]
    with Session() as s:
        rows = s.query(model).order_by(model.id.desc()).all()
        return [r.to_dict() for r in rows]


@app.post("/api/{section}")
async def create_section(section: str, request: Request):
    require_admin(request)
    if section not in COLLECTIONS:
        raise HTTPException(404)
    model, fields = COLLECTIONS[section]
    with Session() as s:
        obj = model()
        apply_fields(obj, await json_body(request), fields)
        s.add(obj)
        s.commit()
        return JSONResponse(obj.to_dict(), status_code=201)


@app.put("/api/{section}/{item_id}")
async def update_section(section: str, item_id: int, request: Request):
    require_admin(request)
    if section not in COLLECTIONS:
        raise HTTPException(404)
    model, fields = COLLECTIONS[section]
    with Session() as s:
        obj = s.get(model, item_id)
        if not obj:
            raise HTTPException(404)
        apply_fields(obj, await json_body(request), fields)
        s.commit()
        return obj.to_dict()


@app.delete("/api/{section}/{item_id}")
async def delete_section(section: str, item_id: int, request: Request):
    require_admin(request)
    if section not in COLLECTIONS:
        raise HTTPException(404)
    model, _ = COLLECTIONS[section]
    with Session() as s:
        obj = s.get(model, item_id)
        if obj:
            delete_uploads(obj.to_dict())
            s.delete(obj)
            s.commit()
        return {"ok": True}


# ---- static frontend ----
@app.get("/uploads/{name:path}")
async def serve_upload(name: str):
    return _serve(UPLOADS, name)


# pretty slug -> actual template file
PAGES = {
    "": "Usmonbek Anvarbekov.dc.html", "about": "About.dc.html",
    "writing": "Writing.dc.html", "books": "Books.dc.html",
    "movies": "Movies.dc.html", "projects": "Projects.dc.html",
    "notes": "Notes.dc.html", "admin": "admin.html",
}


@app.get("/")
async def index():
    return _serve(FRONTEND, PAGES[""])


@app.get("/{name:path}")
async def serve_frontend(name: str):
    # clean slug -> template; otherwise serve the file as-is (assets, old .html links)
    return _serve(FRONTEND, PAGES.get(name, name))


def _serve(root: Path, name: str):
    # resolve + containment check (send_from_directory equivalent)
    dest = (root / name).resolve()
    if root.resolve() not in dest.parents or not dest.is_file():
        raise HTTPException(404)
    return FileResponse(dest)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
