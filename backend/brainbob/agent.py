"""question + memories -> Answer(text, cited_ids). Memories numbered [m1].., model ends with CITED: m3, m7."""
import re
from . import llm
from .types import Answer

PROMPT = """You are answering a question using the memories below, which were recorded from past conversations. Each memory shows its date, scope, authority (approved / tentative / discussion) and status (active or tentative).

Rules:
- Rely on memories that are approved and active. When an approved, active memory and a discussion or tentative memory disagree, the approved, active one is the answer.
- A memory with status "tentative, conflicts with [mX]" is an unresolved conflict: do not treat it as the answer over [mX], but mention that the conflict is unresolved.
- Discussion memories with no conflict are still usable evidence. Among active memories with equal authority that disagree, the newer one wins.
- If the memories do not contain the answer, answer "I don't know".

MEMORIES:
{mems}

Current date: {now}
Question: {q}

Answer concisely. Then, on the final line, list the memories you actually used in the form `CITED: m3, m7` (or `CITED: none`)."""

LEGACY_PROMPT = """You are answering a question using the memories below, which were recorded from past conversations. Newer memories override older ones when they conflict. If the memories do not contain the answer, say you don't know.

MEMORIES:
{mems}

Current date: {now}
Question: {q}

Answer concisely. Then, on the final line, list the memories you actually used in the form `CITED: m3, m7` (or `CITED: none`)."""


def _status(m, index):
    if m.status != "tentative": return "active"
    refs = [f"[m{index[c]}]" for c in (getattr(m, "conflicts_with", None) or []) if c in index]
    return "tentative, conflicts with " + (", ".join(refs) if refs else "a memory not shown")


def render(memories):
    """One line per memory: [mK] (date; scope; authority; status) text. Conflict refs use prompt numbers, never store ids."""
    index = {m.id: i for i, m in enumerate(memories, 1)}
    return "\n".join(f"[m{i}] (date {m.date}; scope {m.scope}; authority {getattr(m, 'authority', None) or 'discussion'}; "
                     f"status {_status(m, index)}) {m.text}" for i, m in enumerate(memories, 1)) or "(no memories)"


def answer(question, memories, now=None, fresh=False, legacy=False):
    """legacy=True reproduces the pre-correctness prompt (date + text only) for old benchmark runs."""
    if legacy:
        mems = "\n".join(f"[m{i}] ({m.date}) {m.text}" for i, m in enumerate(memories, 1)) or "(no memories)"
        content = LEGACY_PROMPT.format(mems=mems, now=now or "unknown", q=question)
    else:
        content = PROMPT.format(mems=render(memories), now=now or "unknown", q=question)
    c = llm.complete("agent", [{"role": "user", "content": content}], fresh=fresh)
    cited, text = [], c
    mt = re.search(r"CITED:\s*(.*)\s*$", c, re.I)
    if mt:
        text = c[:mt.start()].strip()
        for n in re.findall(r"m(\d+)", mt.group(1)):
            i = int(n)
            if 1 <= i <= len(memories) and memories[i - 1].id not in cited: cited.append(memories[i - 1].id)
    return Answer(text, cited)
