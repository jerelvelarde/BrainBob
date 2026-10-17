import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from dataclasses import dataclass
from fastapi.testclient import TestClient
import server
from brainbob.acl import Org

ORG_JSON = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "rusty_rod" / "org.json"
org = Org.load(ORG_JSON)
ENG, S2 = "rusty-rod/engineering", "rusty-rod/sales/sales-02"


@dataclass
class M:
    id: str
    text: str
    scope: str
    status: str = "trial"
    supersedes: str | None = None


class Store:
    def __init__(self):
        self.items = [M("m1", "org fact", "rusty-rod"), M("m2", "eng secret", ENG),
                      M("m3", "sales-02 note", S2), M("m4", "sales-01 note", "rusty-rod/sales/sales-01"),
                      M("m5", "sales team", "rusty-rod/sales")]
    def search(self, q, k=40): return list(self.items)
    def all(self): return list(self.items)
    def retire(self, mid, reason="", author=None):
        return next(m for m in self.items if m.id == mid)
    def add(self, text, **kw):
        m = M(f"m{len(self.items)+1}", text, kw.get("scope", "?"))
        self.items.append(m)
        return m, ""


def build(ingest=None):
    bus = server.Bus()
    store = Store()
    for m in store.items:
        bus.emit("memory.added", memory=m)
    bus.emit("episode.ingested", episode_id="ep-zzz")  # unknown episode: hidden

    class Agent:
        def answer(self, q, mems, now=None):
            return type("A", (), {"text": "a", "cited_ids": [m.id for m in mems]})()

    class Ev:
        def report(self): return {"rows": [{"memory_id": m.id} for m in store.items]}
        def review(self, c): return []

    class Cur:
        def ingest(self, ep, st): return [st.add(ep.text)[0]]

    app = server.create_app(store, Cur(), Agent(), Ev(), lambda *a: True, events=bus, sse_once=True,
                            org=org, ingest=ingest)
    return TestClient(app), bus


def H(m): return {"X-BrainBob-Member": m}


def test_org_shape():
    assert len(org.members) == 18
    assert org.readable_scopes("sales-01") == ["rusty-rod", "rusty-rod/sales", "rusty-rod/sales/sales-01"]
    assert org.member_path("eng-03") == "rusty-rod/engineering/eng-03"
    assert org.can_approve("exec-01", "rusty-rod") and not org.can_approve("sales-01", "rusty-rod")
    assert org.can_approve("sales-01", "rusty-rod/sales") and not org.can_approve("sales-01", "rusty-rod/engineering")
    assert org.can_read("exec-01", "rusty-rod/executive") and not org.can_read("exec-01", "rusty-rod/sales")
    assert not org.can_write("sales-01", ENG) and org.can_write("sales-01", "rusty-rod")


def test_401_without_header():
    c, _ = build()
    for path in ("/memories", "/memories/m1/history", "/episodes/x", "/report", "/events"):
        assert c.get(path).status_code == 401, path
    assert c.post("/ask", json={"question": "q"}).status_code == 401
    assert c.post("/episodes", json={"text": "t"}).status_code == 401


def test_sales_cannot_see_eng_or_other_personal():
    c, _ = build()
    ids = {m["id"] for m in c.get("/memories", headers=H("sales-01")).json()}
    assert ids == {"m1", "m4", "m5"}
    a = c.post("/ask", json={"question": "q"}, headers=H("sales-01")).json()
    assert set(a["cited_ids"]) == {"m1", "m4", "m5"}
    for mid in ("m2", "m3"):
        assert c.get(f"/memories/{mid}/history", headers=H("sales-01")).status_code == 404
        assert c.post(f"/memories/{mid}/retire", json={}, headers=H("sales-01")).status_code == 404
    assert c.get("/memories/m1/history", headers=H("sales-01")).status_code == 200


def test_exec_cannot_see_sales():
    c, _ = build()
    ids = {m["id"] for m in c.get("/memories", headers=H("exec-01")).json()}
    assert ids == {"m1"}
    assert c.get("/memories/m5/history", headers=H("exec-01")).status_code == 404


def test_episodes_and_events_filtered():
    c, bus = build()
    r = c.post("/episodes", json={"text": "eng est", "scope": ENG}, headers=H("eng-01")).json()
    eid = r["episode_id"]
    assert c.get(f"/episodes/{eid}", headers=H("eng-01")).status_code == 200
    assert c.get(f"/episodes/{eid}", headers=H("sales-01")).status_code == 404
    assert c.get(f"/episodes/{eid}", headers=H("exec-01")).status_code == 404
    bus.emit("memory.retrieved", task_id="t", memory_ids=["m1", "m2"])
    def seen(member):
        body = c.get("/events", headers=H(member)).text
        return body
    s = seen("sales-01")
    assert "sales-02 note" not in s and "eng secret" not in s and eid not in s and "ep-zzz" not in s
    assert "org fact" in s and "sales-01 note" in s and "m1\", \"m2" not in s
    e = seen("eng-02")
    assert "eng secret" in e and eid in e and "sales-02 note" not in e
    q = c.get("/events", params={"member": "sales-01"}).text  # EventSource form
    assert "eng secret" not in q and "org fact" in q


def test_report_filtered():
    c, _ = build()
    rows = c.get("/report", headers=H("sales-01")).json()["rows"]
    assert {r["memory_id"] for r in rows} == {"m1", "m4", "m5"}


def test_write_checks():
    c, _ = build()
    r = c.post("/episodes", json={"text": "t", "scope": "rusty-rod", "authority": "approved"}, headers=H("sales-01"))
    assert r.status_code == 403
    r = c.post("/episodes", json={"text": "t", "scope": "rusty-rod", "authority": "approved"}, headers=H("exec-01"))
    assert r.status_code == 200
    assert c.post("/episodes", json={"text": "t", "scope": ENG}, headers=H("sales-01")).status_code == 403
    assert c.post("/episodes", json={"text": "t", "author": "eng-01"}, headers=H("sales-01")).status_code == 403
    assert c.post("/memories/m1/retire", json={}, headers=H("sales-01")).status_code == 200


def test_injected_ingest_gets_org():
    got = {}
    def fake(ep, store, acl):
        got.update(author=ep.author, authority=ep.authority, acl=acl)
        return []
    c, _ = build(ingest=fake)
    # server.Episode has no author field by default; dataclass allows setattr
    r = c.post("/episodes", json={"text": "t", "authority": "tentative", "scope": "rusty-rod/sales"}, headers=H("sales-01"))
    assert r.status_code == 200 and got["acl"] is org and got["author"] == "sales-01" and got["authority"] == "tentative"
