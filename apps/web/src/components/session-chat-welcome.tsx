"use client";

import { createContext, forwardRef, useContext, type ButtonHTMLAttributes, type ComponentProps } from "react";
import { ArrowUpRight, BriefcaseBusiness, Building2, UserRound } from "lucide-react";
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
      <p className="welcome-intro">A little context. A head start. What’s on your mind?</p>
      <div className="welcome-composer">{input}</div>
      {suggestionView}
    </div>
  </div>;
}

const icons = { individual: UserRound, team: BriefcaseBusiness, organization: Building2 };
export const SessionPromptCards = forwardRef<HTMLDivElement, CopilotChatSuggestionViewProps>(function SessionPromptCards({ suggestions, onSelectSuggestion }, ref) {
  const { prompts, disabled } = useContext(SessionWelcomeContext);
  if (!suggestions.length) return null;
  return <div ref={ref} className="session-prompt-grid" aria-label="Memory-based starter prompts">{suggestions.slice(0, 3).map((suggestion, index) => {
    const prompt = prompts.find((item) => item.message === suggestion.message);
    if (!prompt) return null;
    const Icon = icons[prompt.tier];
    return <button key={prompt.tier} className="session-prompt" data-tier={prompt.tier} disabled={disabled || !onSelectSuggestion} onClick={() => onSelectSuggestion?.(suggestion, index)}>
      <span className="prompt-top"><span><Icon size={15} />{prompt.memoryId ? `${prompt.tier} memory` : "Explore " + prompt.tier}</span><ArrowUpRight size={16} /></span>
      <strong>{prompt.title}</strong><span className="prompt-context">{prompt.context}</span>
    </button>;
  })}</div>;
});
