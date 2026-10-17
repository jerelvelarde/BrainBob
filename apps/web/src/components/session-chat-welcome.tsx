"use client";

import { createContext, forwardRef, useContext, type ButtonHTMLAttributes, type ComponentProps } from "react";
import { ArrowUpRight, ListChecks, PencilLine, Search } from "lucide-react";
import { CopilotChatInput, CopilotChatView, useConfigureSuggestions, type CopilotChatSuggestionViewProps } from "@copilotkit/react-core/v2";
import type { SessionPrompt } from "@/lib/session-prompts";

export const SessionWelcomeContext = createContext<{ name: string; prompts: SessionPrompt[]; disabled: boolean }>({ name: "there", prompts: [], disabled: false });

export function SessionSendButton(props: ButtonHTMLAttributes<HTMLButtonElement>) {
  const { disabled } = useContext(SessionWelcomeContext);
  // The installed input supplies its stop icon as children while a run is active.
  return <CopilotChatInput.SendButton {...props} disabled={props.disabled || (disabled && !props.children)} aria-label={props.children ? "Stop response" : "Send message"} />;
}

export function ConfigureSessionPrompts({ prompts, enabled }: { prompts: SessionPrompt[]; enabled: boolean }) {
  useConfigureSuggestions(enabled ? { suggestions: prompts.map(({ title, message }) => ({ title, message })), available: "before-first-message", consumerAgentId: "brainbob" } : null, [prompts, enabled]);
  return null;
}

export function SessionWelcome({ input, suggestionView }: ComponentProps<typeof CopilotChatView.WelcomeScreen>) {
  const { name } = useContext(SessionWelcomeContext);
  return <div className="session-welcome">
    <div className="session-welcome-inner">
      <div className="welcome-bob" aria-hidden="true"><span className="bob-mark"><i /><i /><b /><em /></span><span className="welcome-spark">✦</span></div>
      <h1>Hey {name},<br /><span>Welcome back!</span></h1>
      <div className="welcome-composer">{input}</div>
      {suggestionView}
    </div>
  </div>;
}

const icons = { draft: PencilLine, plan: ListChecks, clarify: Search };
export const SessionPromptCards = forwardRef<HTMLDivElement, CopilotChatSuggestionViewProps>(function SessionPromptCards({ suggestions, onSelectSuggestion }, ref) {
  const { prompts, disabled } = useContext(SessionWelcomeContext);
  if (!suggestions.length) return null;
  return <div ref={ref} className="session-prompt-grid" aria-label="Suggested next actions">{suggestions.slice(0, 3).map((suggestion, index) => {
    const prompt = prompts.find((item) => item.message === suggestion.message);
    if (!prompt) return null;
    const Icon = icons[prompt.action];
    return <button key={prompt.action} className="session-prompt" data-action={prompt.action} disabled={disabled || !onSelectSuggestion} onClick={() => onSelectSuggestion?.(suggestion, index)}>
      <Icon size={18} aria-hidden="true" /><strong>{prompt.title}</strong><ArrowUpRight size={14} aria-hidden="true" />
    </button>;
  })}</div>;
});
