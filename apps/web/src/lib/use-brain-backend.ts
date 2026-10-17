"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { eventsUrl, backendEventSchema, brainApi } from "./brain-api";
import { acceptBackendEvent, emptyBackendState, type BackendState } from "./backend-state";
import type { StoredEvent } from "./brain-api";

export function useBrainBackend(member: string, onLive: (event: StoredEvent, state: BackendState) => void) {
  const [state, setState] = useState(emptyBackendState);
  const [connection, setConnection] = useState<"connecting" | "syncing" | "live" | "offline">("connecting");
  const [error, setError] = useState("");
  const store = useRef(state);
  const listener = useRef(onLive);
  useEffect(() => { listener.current = onLive; }, [onLive]);
  const synchronizeMissing = useCallback(async (signal?: AbortSignal) => {
    const snapshot = await brainApi.memories(member, signal);
    if (signal?.aborted) return;
    // The event log owns known records; a later HTTP snapshot must not overwrite newer SSE changes.
    const memories = { ...store.current.memories };
    for (const memory of snapshot) if (!memories[memory.id]) memories[memory.id] = memory;
    store.current = { ...store.current, memories };
    setState(store.current);
  }, [member]);

  useEffect(() => {
    let source: EventSource | undefined, retry: ReturnType<typeof setTimeout> | undefined;
    let frame = 0, closed = false;
    const abort = new AbortController();
    const publish = () => { if (!frame) frame = requestAnimationFrame(() => { frame = 0; setState(store.current); }); };
    const connect = () => {
      if (closed) return;
      store.current = { ...store.current, replaying: true };
      source = new EventSource(eventsUrl(member, store.current.seq));
      source.onopen = () => { if (closed) return; setConnection("syncing"); setError(""); };
      source.onmessage = (message) => {
        if (closed) return;
        try {
          const event = backendEventSchema.parse(JSON.parse(message.data));
          const accepted = acceptBackendEvent(store.current, event);
          store.current = accepted.state;
          publish();
          if (event.type === "replay.done") {
            setConnection("live");
            void synchronizeMissing(abort.signal).catch((err) => { if (!closed) setError(err.message); });
          } else if (accepted.animate) listener.current(event, store.current);
        } catch (err) {
          setError(err instanceof Error && !err.message.startsWith("[") ? err.message : "An event did not match the backend contract. Reload after syncing versions.");
          setConnection("offline"); source?.close();
        }
      };
      source.onerror = () => {
        source?.close();
        if (closed) return;
        setConnection("offline");
        store.current = { ...store.current, replaying: true };
        publish();
        retry = setTimeout(connect, 3000);
      };
    };
    connect();
    return () => { closed = true; source?.close(); clearTimeout(retry); cancelAnimationFrame(frame); abort.abort(); };
  }, [member, synchronizeMissing]);
  return { state, connection, error };
}
