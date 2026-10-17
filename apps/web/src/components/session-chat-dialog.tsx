"use client";

import { useEffect, useRef, useState, type ReactNode, type RefObject } from "react";
import { ArrowLeft, Brain } from "lucide-react";
import { memberForReader, teamForReader } from "@/lib/sample-company";

export function SessionChatDialog({ open, reader, onClose, onFile, fileOpen, onCloseInspection, inspection, brain, children, returnFocus }: {
  open: boolean; reader: string; onClose: () => void; onFile: () => void; fileOpen: boolean;
  onCloseInspection: () => void; inspection?: ReactNode; brain?: (onClose?: () => void) => ReactNode; children: ReactNode; returnFocus: RefObject<HTMLButtonElement | null>;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const fileButton = useRef<HTMLButtonElement>(null);
  const wasInspecting = useRef(false);
  const [compact, setCompact] = useState(false);
  const [showBrain, setShowBrain] = useState(false);
  const brainVisible = !compact || showBrain || Boolean(inspection);
  function closeBrain() { setShowBrain(false); onCloseInspection(); fileButton.current?.focus(); }
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
    onKeyDownCapture={(event) => { if (event.key === "Escape" && (inspection || compact && showBrain)) { event.preventDefault(); event.stopPropagation(); if (inspection) onCloseInspection(); else closeBrain(); } }}
    onCancel={(event) => { event.preventDefault(); if (inspection) onCloseInspection(); else if (compact && showBrain) closeBrain(); else onClose(); }}>
    <header className="session-chat-header">
      <button className="back-to-brain" aria-label="Back to brain" onClick={onClose}><ArrowLeft size={18} /><span>Back to brain</span></button>
      <div className="session-identity"><span className="member-avatar" aria-hidden="true">{member?.label.split(" ").map((name) => name[0]).join("")}</span><div><strong>{member?.label}</strong><small>{teamForReader(reader)?.label} · Rusty Rod</small></div></div>
      <button ref={fileButton} className="session-file-toggle" aria-label={compact && brain ? "Brain & memory" : "Memory"} aria-expanded={compact && brain ? brainVisible : fileOpen} onClick={() => { if (compact && brain) { if (brainVisible) closeBrain(); else setShowBrain(true); } else onFile(); }}><Brain size={18} /><span>{compact && brain ? "Brain & memory" : "Memory"}</span></button>
    </header>
    <div className="session-chat-workspace" data-inspecting={Boolean(inspection)} data-brain={Boolean(brain)}>
      <div className="session-conversation" inert={compact && brainVisible}>{children}</div>
      {brain ? <aside className="session-brain-sidebar" hidden={!brainVisible}>{brain(compact ? closeBrain : undefined)}</aside> : inspection ? <div className="session-chat-inspection">{inspection}</div> : null}
    </div>
  </dialog>;
}
