"use client";

import { ChevronDown, ChevronRight, FileText, FolderClosed, FolderOpen, LockKeyhole } from "lucide-react";
import { useState } from "react";
import { canRead, sceneScope, type BackendMemory } from "@/lib/brain-api";
import type { MemoryScope } from "@/lib/memory";
import { drawersForTier } from "@/lib/sample-company";

export function MemoryCabinetBrowser({ reader, memories, tier, onTier, onInspect }: {
  reader: string; memories: BackendMemory[]; tier: MemoryScope | null;
  onTier: (tier: MemoryScope | null) => void; onInspect: (id: string) => void;
}) {
  const [search, setSearch] = useState("");
  const available = memories.filter((memory) => memory.status !== "retired" && canRead(memory.scope, reader));
  return <div className="memory-cabinet-browser">
    <label className="cabinet-search"><input aria-label="Find a saved memory" type="search" placeholder="Find a memory…" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
    <div className="cabinet-folders">
      {(["individual", "team", "organization"] as const).map((level) => {
        const records = available.filter((memory) => sceneScope(memory.scope) === level);
        const expanded = tier === level || Boolean(search.trim());
        const drawers = drawersForTier(level, reader).filter((drawer) => level !== "individual" || drawer.accessible);
        return <section className="cabinet-folder" key={level}>
          <button className="cabinet-folder-toggle" aria-expanded={expanded} onClick={() => onTier(tier === level ? null : level)}>
            {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}{expanded ? <FolderOpen size={18} /> : <FolderClosed size={18} />}
            <strong>{level === "individual" ? "Individual" : level === "team" ? "Team" : "Organization"}</strong><span>{records.length}</span>
          </button>
          {expanded ? <div className="cabinet-drawers">{drawers.map((drawer) => {
            const files = records.filter((memory) => memory.scope === drawer.path && memory.text.toLowerCase().includes(search.trim().toLowerCase()));
            return <div className="cabinet-drawer" key={drawer.path}>
              <div className="cabinet-drawer-label"><FolderClosed size={14} /><span>{drawer.label}</span>{drawer.accessible ? <small>{files.length}</small> : <LockKeyhole size={12} aria-label="No access" />}</div>
              {drawer.accessible ? files.length ? files.map((memory) => <button className="cabinet-file" key={memory.id} onClick={() => onInspect(memory.id)}>
                <FileText size={15} /><span>{memory.text}</span>{memory.flagged || memory.status === "tentative" ? <i aria-label={memory.flagged ? "Flagged for review" : "Tentative"} /> : null}
              </button>) : <p className="cabinet-empty">{search ? "No matching memories" : "No saved memories yet"}</p> : null}
            </div>;
          })}</div> : null}
        </section>;
      })}
    </div>
  </div>;
}
