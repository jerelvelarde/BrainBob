from dataclasses import dataclass, field
from typing import Callable, Literal, Optional

Status = Literal["trial", "promoted", "retired", "locked"]


@dataclass
class Episode:
    id: str
    text: str
    date: str
    source: str


@dataclass
class Memory:
    id: str
    text: str
    author: str
    origin: str
    date: str
    status: str = "trial"
    scope: str = "team"
    reason: str = ""        # why the last status change happened
    flagged: bool = False   # locked but judged harmful: handed to the owner
    supersedes: Optional[str] = None  # id of the memory this one corrects
    owner: Optional[str] = None       # who locked it; only they can resolve it


@dataclass
class Task:
    id: str
    question: str
    grade: Callable[[str], bool]
    now: Optional[str] = None


@dataclass
class Answer:
    text: str
    cited_ids: list = field(default_factory=list)


@dataclass
class Evidence:
    memory_id: str
    shown: bool
    correct: bool
    task_id: str


@dataclass
class Decision:
    memory_id: str
    action: Literal["promote", "retire", "flag"]
    reason: str
    task_ids: list = field(default_factory=list)
