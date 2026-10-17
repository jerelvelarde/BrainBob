"""Episode -> atomic memories. Extraction prompt + JSON/bullet fallback parsing."""
import json, re
from . import events, llm

PROMPT = """Below is a chat session between a user and an AI assistant (session date: {date}). Extract atomic, self-contained facts worth remembering long-term: facts about the user, their preferences, events (with dates if mentioned), plans, and specific information the assistant gave (names, numbers, recommendations, lists). One fact per item, include concrete details. Output ONLY a JSON array of strings, no commentary.

SESSION:
{s}"""


def _parse(txt):
    i = txt.find("[")
    if i >= 0:
        try:
            out = []
            for a in json.JSONDecoder().raw_decode(txt[i:])[0]:  # tolerates trailing garbage
                if isinstance(a, str): out.append(a)
                elif isinstance(a, dict): out.append(" ".join(str(v) for v in a.values()))
            if out: return out
        except Exception: pass
    lines = [re.sub(r"^\s*(?:[-*]|\d+[.)])\s+", "", l).strip() for l in txt.splitlines() if re.match(r"^\s*(?:[-*]|\d+[.)])\s+", l)]
    if lines: return lines
    m = re.search(r"\{.*\}", txt, re.S)
    if m:
        try:
            out = []
            for v in json.loads(m.group(0)).values():
                out += [str(x) for x in v] if isinstance(v, list) else [str(v)]
            return out
        except Exception: pass
    # last resort for truncated / garbled JSON: salvage clean quoted sentences
    return [x for x in re.findall(r'"((?:[^"\
]){15,300})"', txt) if x.isascii()]


def extract(episode, role="curator"):
    """The model call only (cached); lets callers prefetch many episodes in parallel and then ingest in order."""
    c = llm.complete(role, [{"role": "user", "content": PROMPT.format(date=episode.date, s=episode.text[:60000])}])
    return _parse(c)


def ingest(episode, store, author=None, role="curator"):
    """The author name defaults to the role that wrote the memories."""
    author = author or role
    added = []
    for f in extract(episode, role):
        m, _ = store.add(f, author=author, origin=episode.id, date=episode.date)
        if m: added.append(m)
    events.emit("episode.ingested", episode_id=episode.id, source=episode.source, n_memories=len(added))
    return added
