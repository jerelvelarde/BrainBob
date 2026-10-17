"use client";

import { useEffect, useId, useRef, useState } from "react";
import { Check, ChevronsUpDown, Search, SquarePen, X } from "lucide-react";
import { companyMembers, companyTeams, memberForReader, teamForReader } from "@/lib/sample-company";

export function MemberSelect({ value, onChange, onNewSession, autoFocus = false, sessions = [] }: {
  value: string; onChange: (value: string) => void; onNewSession: () => void; autoFocus?: boolean;
  sessions?: { label: string; selected: boolean; onOpen: () => void }[];
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const root = useRef<HTMLDivElement>(null), trigger = useRef<HTMLButtonElement>(null), search = useRef<HTMLInputElement>(null);
  const id = useId();
  const member = memberForReader(value), team = teamForReader(value);
  const matching = companyMembers.filter((person) => `${person.label} ${person.team}`.toLowerCase().includes(query.trim().toLowerCase()));
  const teams = [...companyTeams].sort((a, b) => Number(b.slug === team?.slug) - Number(a.slug === team?.slug));
  function close(restore = false) { setOpen(false); if (restore) trigger.current?.focus(); }
  useEffect(() => {
    if (!open) return;
    search.current?.focus();
    const outside = (event: PointerEvent) => { if (event.target instanceof Node && !root.current?.contains(event.target)) setOpen(false); };
    document.addEventListener("pointerdown", outside);
    return () => document.removeEventListener("pointerdown", outside);
  }, [open]);
  return <div ref={root} className="member-switcher" onKeyDown={(event) => {
    if (event.key === "Escape" && open) { event.preventDefault(); event.stopPropagation(); close(true); }
  }} onBlur={(event) => { if (event.relatedTarget && !event.currentTarget.contains(event.relatedTarget)) setOpen(false); }}>
    <button ref={trigger} className="member-account" autoFocus={autoFocus} aria-label={`Switch person or start a session. Current person: ${member?.label}`} aria-haspopup="dialog" aria-expanded={open} aria-controls={open ? id : undefined}
      onClick={() => { setQuery(""); setOpen(!open); }}>
      <span className="account-avatar" data-team={member?.team} aria-hidden="true">{member?.label.split(" ").map((part) => part[0]).join("")}</span>
      <span className="account-label"><strong>{member?.label}</strong><small>{team?.label} · Rusty Rod</small></span><ChevronsUpDown size={16} aria-hidden="true" />
    </button>
    {open ? <div className="member-menu-anchor"><section id={id} className="member-menu" role="dialog" aria-labelledby={`${id}-title`} aria-describedby={`${id}-hint`}>
      <header><div><small>RUSTY ROD</small><h2 id={`${id}-title`}>Switch person</h2></div><button className="icon-button" aria-label="Close person switcher" onClick={() => close(true)}><X size={16} /></button></header>
      {sessions.length ? <nav className="open-desk-sessions" aria-label="Open desk sessions">{sessions.map((session, index) => <button key={index} aria-label={`Open ${session.label}’s desk session`} aria-current={session.selected ? "true" : undefined} onClick={() => { close(); session.onOpen(); }}><span aria-hidden="true">{session.label.split(" ").map((part) => part[0]).join("")}</span>{session.label.split(" ")[0]}</button>)}</nav> : null}
      <button className="new-session-action" onClick={() => { close(); onNewSession(); }}><SquarePen size={18} /><span><strong>New session</strong><small>Fresh chat, same memory</small></span></button>
      <p id={`${id}-hint`}>Switching starts a fresh context.</p>
      <label className="member-search"><Search size={16} aria-hidden="true" /><input ref={search} aria-label="Find a person" placeholder="Find a person or team…" value={query} onChange={(event) => setQuery(event.target.value)} /></label>
      <div className="member-options">{teams.map((group) => {
        const people = matching.filter((person) => person.team === group.slug);
        return people.length ? <section key={group.slug} aria-label={group.label}><h3>{group.label}<span>{people.length}</span></h3>{people.map((person) => <button key={person.path} aria-label={`${person.label} · ${group.label}`} aria-current={person.path === value ? "true" : undefined} onClick={() => { close(true); if (person.path !== value) onChange(person.path); }}>
          <span className="account-avatar" data-team={person.team} aria-hidden="true">{person.label.split(" ").map((part) => part[0]).join("")}</span><span>{person.label}</span>{person.path === value ? <Check size={16} aria-label="Current person" /> : null}
        </button>)}</section> : null;
      })}{!matching.length ? <p className="member-empty" role="status">No people found. Try a name or team.</p> : null}</div>
      <footer>Demo identities</footer>
    </section></div> : null}
  </div>;
}
