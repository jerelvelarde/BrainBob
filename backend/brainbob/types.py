from dataclasses import dataclass, field
from typing import Callable, Literal, Optional

Status = Literal["trial", "promoted", "retired", "locked", "tentative"]
Authority = Literal["approved", "tentative", "discussion"]
AUTHORITIES = ("approved", "tentative", "discussion")


@dataclass
class Episode:
    id: str
    text: str
    date: str
    source: str
    author: Optional[str] = None      # member id of who said it
    scope: str = "team"               # scope path the episode was written to
    authority: str = "discussion"     # approved / tentative / discussion


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
    authority: str = "discussion"     # copied from the episode: approved / tentative / discussion
    model: Optional[str] = None       # actual model id that wrote it
    conflicts_with: list = field(default_factory=list)  # ids of active memories a tentative one conflicts with


@dataclass
class Task:
    id: str
    question: str
    grade: Callable[[str], bool]
    now: Optional[str] = None
    reference: Optional[str] = None  # gold text; only the lesson writer sees it, on training tasks


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
    action: Literal["promote", "retire", "flag", "add", "tentative", "supersede", "reject"]
    reason: str
    task_ids: list = field(default_factory=list)
    text: str = ""                    # maintain: the candidate text
    related: list = field(default_factory=list)  # maintain: ids of the existing memories the decision is about
    model: Optional[str] = None       # maintain: judge model id that made the call
