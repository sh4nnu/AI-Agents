import { FormEvent, useEffect, useRef, useState } from "react";
import type { Message } from "../types";

interface ChatPanelProps {
  history: Message[];
  onSend: (message: string) => Promise<void> | void;
  disabled: boolean;
  loading: boolean;
  sessionReady: boolean;
}

const roleLabel: Record<Message["role"], string> = {
  user: "You",
  assistant: "Agent"
};

const ChatPanel = ({
  history,
  onSend,
  disabled,
  loading,
  sessionReady
}: ChatPanelProps) => {
  const [input, setInput] = useState("");
  const logRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    logRef.current?.scrollTo({
      top: logRef.current.scrollHeight,
      behavior: "smooth"
    });
  }, [history, loading]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!input.trim() || disabled || loading) {
      return;
    }
    void onSend(input.trim());
    setInput("");
  };

  return (
    <div className="chat-panel">
      <h2>Chat with your chart agent</h2>
      <p className="panel-hint">
        Ask for insights, chart recommendations, or refinements to existing
        options.
      </p>
      <div className="chat-log" ref={logRef}>
        {!history.length && (
          <p className="panel-hint">
            {sessionReady
              ? "Say hello and describe the insights you want to visualize."
              : "Upload data to unlock the chat interface."}
          </p>
        )}
        {history.map((message, index) => (
          <div
            key={`${message.role}-${index}`}
            className={`chat-bubble ${message.role}`}
          >
            <strong>{roleLabel[message.role]}</strong>
            <p>{message.content}</p>
          </div>
        ))}
        {loading && (
          <div className="chat-bubble assistant">
            <strong>Agent</strong>
            <p>Thinking about new chart ideas…</p>
          </div>
        )}
      </div>
      <form className="chat-input" onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder={
            sessionReady
              ? "e.g. Show me trends over time"
              : "Upload data to start chatting"
          }
          value={input}
          onChange={(event) => setInput(event.target.value)}
          disabled={disabled || loading}
        />
        <button type="submit" disabled={disabled || loading || !input.trim()}>
          {loading ? "Sending…" : "Send"}
        </button>
      </form>
    </div>
  );
};

export default ChatPanel;
