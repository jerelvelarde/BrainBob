"""question + memories -> Answer(text, cited_ids). Memories numbered [m1].., model ends with CITED: m3, m7."""
import re
from . import llm
from .types import Answer

PROMPT = """You are answering a question using the memories below, which were recorded from past conversations. Newer memories override older ones when they conflict. If the memories do not contain the answer, say you don't know.

MEMORIES:
{mems}

Current date: {now}
Question: {q}

Answer concisely. Then, on the final line, list the memories you actually used in the form `CITED: m3, m7` (or `CITED: none`)."""


def answer(question, memories, now=None):
    mems = "\n".join(f"[m{i}] ({m.date}) {m.text}" for i, m in enumerate(memories, 1)) or "(no memories)"
    c = llm.complete("agent", [{"role": "user", "content": PROMPT.format(mems=mems, now=now or "unknown", q=question)}])
    cited, text = [], c
    mt = re.search(r"CITED:\s*(.*)\s*$", c, re.I)
    if mt:
        text = c[:mt.start()].strip()
        for n in re.findall(r"m(\d+)", mt.group(1)):
            i = int(n)
            if 1 <= i <= len(memories) and memories[i - 1].id not in cited: cited.append(memories[i - 1].id)
    return Answer(text, cited)
