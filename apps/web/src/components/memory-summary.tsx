"use client";

import { useEffect, useState } from "react";
import { LoaderCircle, RefreshCw, Sparkles } from "lucide-react";
import { brainApi, type MemorySummary as Summary } from "@/lib/brain-api";

export function MemorySummary({ member }: { member: string }) {
  const [result, setResult] = useState<Summary>();
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const abort = new AbortController();
    let active = true;
    // Coalesce memory events arriving together during initial replay or ingestion.
    const timer = setTimeout(() => {
      void brainApi.memorySummary(member, abort.signal).then((value) => {
        if (active) setResult(value);
      }).catch((err) => {
        if (active) setError(err instanceof Error ? err.message : "Couldn’t summarize memory.");
      }).finally(() => clearTimeout(timeout));
    }, 350);
    const timeout = setTimeout(() => {
      if (active) { active = false; abort.abort(); setError("The summary took too long. Try again or browse Memory files."); }
    }, 75000);
    return () => { active = false; clearTimeout(timer); clearTimeout(timeout); abort.abort(); };
  }, [member, attempt]);
  return <div className="memory-summary">
    <p className="memory-intro">A quick overview of your current saved memory.</p>
    {error ? <div className="memory-summary-error" role="alert"><p>{error}</p><button onClick={() => { setError(""); setResult(undefined); setAttempt((value) => value + 1); }}><RefreshCw size={14} />Try again</button></div>
      : !result ? <div className="memory-summary-loading" role="status"><LoaderCircle size={16} className="memory-tool-spinner" /><span>Summarizing your memory…</span></div>
      : result.memory_count === 0 ? <p className="empty-state">No saved memories yet. Your summary will appear as BrainBob remembers context.</p>
      : <><div className="memory-summary-copy">{result.summary.split(/\n\s*\n/).filter(Boolean).map((paragraph, index) => <p key={index}>{paragraph}</p>)}</div>
        <p className="memory-summary-caption"><Sparkles size={13} />Summarized from {result.memory_count} {result.memory_count === 1 ? "memory" : "memories"}</p>
        {result.truncated ? <p className="memory-snapshot-note">This overview covers {result.memory_count} of {result.total_count} memories. Browse Memory files for the full context.</p> : null}
        <p className="memory-snapshot-note">AI summaries can miss details. Check Memory files for sources and history.</p></>}
  </div>;
}
