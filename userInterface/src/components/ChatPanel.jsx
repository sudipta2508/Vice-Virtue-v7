import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";

const styles = {
  container: {
    display: "flex",
    flexDirection: "column",
    height: "100%",
    maxWidth: 720,
    width: "100%",
    margin: "0 auto",
  },
  messages: {
    flex: 1,
    overflowY: "auto",
    padding: "24px 16px",
    display: "flex",
    flexDirection: "column",
    gap: 16,
  },
  bubble: (role) => ({
    alignSelf: role === "user" ? "flex-end" : "flex-start",
    maxWidth: "85%",
    padding: "14px 18px",
    borderRadius: 12,
    background: role === "user" ? "#2A2A30" : "#141416",
    border: `1px solid ${role === "user" ? "#3A3A42" : "#1E1E22"}`,
    color: "#E8E6E1",
    fontFamily: "'Cormorant Garamond', serif",
    fontSize: 15,
    lineHeight: 1.65,
  }),
  inputRow: {
    display: "flex",
    gap: 10,
    padding: "16px",
    borderTop: "1px solid #1E1E22",
    background: "#0C0C0E",
  },
  input: {
    flex: 1,
    padding: "12px 16px",
    borderRadius: 8,
    border: "1px solid #2A2A30",
    background: "#141416",
    color: "#E8E6E1",
    fontFamily: "'Cormorant Garamond', serif",
    fontSize: 15,
    outline: "none",
  },
  button: {
    padding: "12px 20px",
    borderRadius: 8,
    border: "none",
    background: "#2A2A30",
    color: "#E8E6E1",
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 11,
    fontWeight: 600,
    letterSpacing: 0.5,
    cursor: "pointer",
  },
  progress: {
    padding: "8px 16px",
    fontSize: 12,
    color: "#8A8680",
    fontFamily: "'JetBrains Mono', monospace",
  },
  quickRow: {
    display: "flex",
    gap: 8,
    padding: "0 16px 12px",
    background: "#0C0C0E",
    flexWrap: "wrap",
  },
  quickBtn: {
    padding: "8px 16px",
    borderRadius: 8,
    border: "1px solid #3A3A42",
    background: "#18181B",
    color: "#E8E6E1",
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 11,
    fontWeight: 600,
    letterSpacing: 0.4,
    cursor: "pointer",
  },
};

function getPlaceholder(session) {
  if (!session) return "Loading…";
  if (session.chat_phase === "await_api_key") return "Enter your Claude API key…";
  if (session.chat_phase === "await_narrative") return "Share your leader character journey…";
  if (session.chat_phase === "await_pre_add_more_consent") return "Reply yes or no…";
  if (session.chat_phase === "await_pre_optional_dimension") return "Name a leader character dimension…";
  if (session.chat_phase === "await_pre_optional_narrative") return "Tell me more about that dimension…";
  if (session.chat_phase === "await_pre_add_more_again") return "Reply yes or no…";
  if (session.followup_phase === "await_gap_dim_add_more") return "Reply yes or no…";
  if (session.followup_phase === "await_gap_dim_more_text")
    return "Add more about this dimension…";
  if (session.chat_phase === "analyzing" || session.followup_phase === "reassessing")
    return "Please wait…";
  return "Your message… (or say e.g. 'show me the report' to finish)";
}

function quickReplyPayload(label) {
  const t = (label || "").trim().toLowerCase();
  if (t === "skip") return "skip";
  if (t === "yes") return "yes";
  if (t === "no") return "no";
  return label;
}

export default function ChatPanel({ session, onSend, disabled, narrow = false }) {
  const [text, setText] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [session?.messages, session?.progress]);

  const isDisabled =
    disabled ||
    !session ||
    session.chat_input_enabled === false ||
    session.chat_phase === "analyzing" ||
    session.followup_phase === "reassessing";

  const quickReplies = session?.quick_replies || [];

  const handleSubmit = (e) => {
    e.preventDefault();
    const t = text.trim();
    if (!t || isDisabled) return;
    onSend(t);
    setText("");
  };

  const handleQuick = (label) => {
    if (isDisabled) return;
    onSend(quickReplyPayload(label));
  };

  const progress = session?.progress;

  const containerStyle = {
    ...styles.container,
    maxWidth: narrow ? "100%" : styles.container.maxWidth,
    margin: narrow ? 0 : styles.container.margin,
    height: narrow ? "100%" : undefined,
  };

  return (
    <div style={containerStyle}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500;600&display=swap');
      `}</style>
      <div style={styles.messages}>
        {(session?.messages || []).map((msg, i) => (
          <div key={i} style={styles.bubble(msg.role)}>
            <ReactMarkdown
              components={{
                p: ({ children }) => <p style={{ margin: 0 }}>{children}</p>,
                strong: ({ children }) => (
                  <strong style={{ color: "#E8E6E1" }}>{children}</strong>
                ),
              }}
            >
              {msg.content}
            </ReactMarkdown>
          </div>
        ))}
        {progress?.message &&
          (session?.chat_phase === "analyzing" || session?.followup_phase === "reassessing") && (
            <div style={styles.progress}>
              {progress.message}
              {progress.percent > 0 && ` (${Math.round(progress.percent * 100)}%)`}
            </div>
          )}
        <div ref={bottomRef} />
      </div>
      {quickReplies.length > 0 && !isDisabled && (
        <div style={styles.quickRow}>
          {quickReplies.map((label) => (
            <button
              key={label}
              type="button"
              style={styles.quickBtn}
              onClick={() => handleQuick(label)}
            >
              {label}
            </button>
          ))}
        </div>
      )}
      <form style={styles.inputRow} onSubmit={handleSubmit}>
        <input
          style={styles.input}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={getPlaceholder(session)}
          disabled={isDisabled}
        />
        <button type="submit" style={styles.button} disabled={isDisabled}>
          Send
        </button>
      </form>
    </div>
  );
}
