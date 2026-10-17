"use client";

import { useEffect, useRef, useState, type ReactNode, type RefObject } from "react";
import { ArrowLeft, Brain } from "lucide-react";
import { memberForReader, teamForReader } from "@/lib/sample-company";

export function SessionChatDialog({ open, reader, onClose, onFile, fileOpen, onCloseInspection, inspection, children, returnFocus }: {
  open: boolean; reader: string; onClose: () => void; onFile: () => void; fileOpen: boolean;
  onCloseInspection: () => void; inspection?: ReactNode; children: ReactNode; returnFocus: RefObject<HTMLButtonElement | null>;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const fileButton = useRef<HTMLButtonElement>(null);
  const wasInspecting = useRef(false);
  const [compact, setCompact] = useState(false);
  const member = memberForReader(reader);
  useEffect(() => {
    const query = matchMedia("(max-width: 680px)");
    const update = () => setCompact(query.matches);
    update(); query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  useEffect(() => {
    const element = dialog.current;
    if (open && element && !element.open) element.showModal();
    if (!open && element?.open) { element.close(); returnFocus.current?.focus(); }
  }, [open, returnFocus]);
  useEffect(() => {
    if (open && wasInspecting.current && !inspection) fileButton.current?.focus();
    wasInspecting.current = Boolean(inspection);
  }, [open, inspection]);
  return <dialog ref={dialog} className="session-chat-dialog" aria-label={`${member?.label ?? "Your"}’s session chat`}
    onKeyDownCapture={(event) => { if (event.key === "Escape" && inspection) { event.preventDefault(); event.stopPropagation(); onCloseInspection(); } }}
    onCancel={(event) => { event.preventDefault(); if (inspection) onCloseInspection(); else onClose(); }}>
    <header className="session-chat-header">
      <button className="back-to-brain" aria-label="Back to brain" onClick={onClose}><ArrowLeft size={18} /><span>Back to brain</span></button>
      <div className="session-identity"><span className="member-avatar" aria-hidden="true">{member?.label.split(" ").map((name) => name[0]).join("")}</span><div><strong>{member?.label}</strong><small>{teamForReader(reader)?.label} · Rusty Rod</small></div></div>
      <button ref={fileButton} className="session-file-toggle" aria-label="Memory" aria-expanded={fileOpen} onClick={onFile}><Brain size={18} /><span>Memory</span></button>
    </header>
    <div className="session-chat-workspace" data-inspecting={Boolean(inspection)}>
      <div className="session-conversation" inert={compact && Boolean(inspection)}>{children}</div>
      {inspection ? <div className="session-chat-inspection">{inspection}</div> : null}
    </div>
  </dialog>;
}
