"use client";

import { ChevronRight, FileText, FolderClosed, FolderOpen } from "lucide-react";
import { useEffect, useState } from "react";
import { canRead, sceneScope, scopeLabel, type BackendMemory } from "@/lib/brain-api";
import type { MemoryScope } from "@/lib/memory";
import { drawersForTier, memberForReader } from "@/lib/sample-company";

const labels = { individual: "Individual", team: "Team", organization: "Organization" };

export function MemoryCabinetBrowser({ reader, memories, tier, onTier, onInspect }: {
  reader: string; memories: BackendMemory[]; tier: MemoryScope | null;
  onTier: (tier: MemoryScope | null) => void; onInspect: (id: string) => void;
}) {
  const [search, setSearch] = useState("");
  const [folder, setFolder] = useState<string | null>(null);
  useEffect(() => { setFolder(null); setSearch(""); }, [tier, reader]);
  const available = memories.filter((memory) => memory.status !== "retired" && canRead(memory.scope, reader));
  const path = tier === "individual" ? reader : folder;
  const querying = Boolean(search.trim());
  const files = available.filter((memory) => (!tier || sceneScope(memory.scope) === tier) && (!path || memory.scope === path) && memory.text.toLowerCase().includes(search.trim().toLowerCase()));
  const showFiles = querying || Boolean(path);
  function root() { setFolder(null); setSearch(""); onTier(null); }
  return <div className="memory-cabinet-browser">
    {tier ? <nav className="cabinet-breadcrumbs" aria-label="Memory folder path">
      <button onClick={root}>Cabinets</button><ChevronRight size={11} />
      <button aria-current={!path ? "page" : undefined} onClick={() => { setFolder(null); setSearch(""); }}>{labels[tier]}</button>
      {path ? <><ChevronRight size={11} /><span aria-current="page">{tier === "individual" ? memberForReader(reader)?.label : scopeLabel(path)}</span></> : null}
    </nav> : null}
    <label className="cabinet-search"><input aria-label="Find a saved memory" type="search" placeholder={path ? `Search ${scopeLabel(path)}’s memories…` : "Find a memory…"} value={search} onChange={(event) => setSearch(event.target.value)} /></label>
    {!tier && !querying ? <div className="cabinet-folders">{(["individual", "team", "organization"] as const).map((level) => <button className="cabinet-folder-toggle" key={level} onClick={() => onTier(level)}>
      <FolderClosed size={19} /><strong>{labels[level]}</strong><span>{available.filter((memory) => sceneScope(memory.scope) === level).length}</span><ChevronRight size={14} />
    </button>)}</div> : showFiles ? <div className="cabinet-files">
      <div className="cabinet-list-heading"><span>Memory</span><small>{files.length} {files.length === 1 ? "file" : "files"}</small></div>
      {files.map((memory) => <button className="cabinet-file" key={memory.id} onClick={() => onInspect(memory.id)}>
        <FileText size={16} /><span>{memory.text}{querying && !path ? <small>{scopeLabel(memory.scope)}</small> : null}</span>{memory.flagged || memory.status === "tentative" ? <i aria-label={memory.flagged ? "Flagged for review" : "Tentative"} /> : null}
      </button>)}
      {!files.length ? <p className="cabinet-empty">{querying ? "No matching memories" : "No saved memories yet"}</p> : null}
    </div> : tier ? <div className="cabinet-folders">{drawersForTier(tier, reader).filter((drawer) => drawer.accessible).map((drawer) => <button className="cabinet-folder-toggle" key={drawer.path} onClick={() => setFolder(drawer.path)}>
      <FolderOpen size={18} /><strong>{drawer.label}</strong><span>{available.filter((memory) => memory.scope === drawer.path).length}</span><ChevronRight size={14} />
    </button>)}</div> : null}
  </div>;
}
