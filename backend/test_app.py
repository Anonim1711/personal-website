"""Self-check: CRUD round-trip + write routes reject unauthenticated callers."""
import os
import tempfile

os.environ["ADMIN_PASSWORD"] = "testpw"
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(
    tempfile.mkdtemp(), "test.db")

from fastapi.testclient import TestClient  # noqa: E402
import app as appmod  # noqa: E402

c = TestClient(appmod.app)

# writes rejected without login
assert c.post("/api/notes", json={"text": "x"}).status_code == 401
assert c.put("/api/about", json={"text": "x"}).status_code == 401

# wrong password rejected
assert c.post("/api/login", json={"password": "nope"}).status_code == 401
# correct password logs in
assert c.post("/api/login", json={"password": "testpw"}).status_code == 200

# create -> list -> update -> delete a note
r = c.post("/api/notes", json={"text": "hello"})
assert r.status_code == 201, r.status_code
nid = r.json()["id"]
assert any(n["text"] == "hello" for n in c.get("/api/notes").json())
c.put(f"/api/notes/{nid}", json={"text": "edited"})
assert c.get("/api/notes").json()[0]["text"] == "edited"
c.delete(f"/api/notes/{nid}")
assert c.get("/api/notes").json() == []

# projects: skills list round-trips as a list
r = c.post("/api/projects", json={"title": "P", "skills": ["a", "b"]})
assert r.json()["skills"] == ["a", "b"]

# about singleton upsert
c.put("/api/about", json={"text": "bio", "photo": "/uploads/p.png"})
assert c.get("/api/about").json()["text"] == "bio"

print("all tests passed")
