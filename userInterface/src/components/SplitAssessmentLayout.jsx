import ChatPanel from "./ChatPanel";
import ResultsScreen from "./ResultsScreen";

export default function SplitAssessmentLayout({
  sessionId,
  session,
  onSend,
  sending,
  onNewChat,
  resultsRefreshKey,
}) {
  return (
    <div
      style={{
        height: "100vh",
        width: "100vw",
        display: "flex",
        background: "#0C0C0E",
        color: "#E8E6E1",
        overflow: "hidden",
      }}
    >
      <aside
        style={{
          width: "33.333%",
          minWidth: 280,
          maxWidth: 420,
          flexShrink: 0,
          display: "flex",
          flexDirection: "column",
          borderRight: "1px solid #1E1E22",
          background: "#0C0C0E",
        }}
      >
        <div
          style={{
            padding: "12px 16px",
            borderBottom: "1px solid #1E1E22",
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 10,
            color: "#6A6660",
            letterSpacing: 0.8,
            textTransform: "uppercase",
          }}
        >
          Conversation
        </div>
        <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
          <ChatPanel
            session={session}
            onSend={onSend}
            disabled={sending}
            narrow
          />
        </div>
      </aside>
      <main
        style={{
          flex: 1,
          minWidth: 0,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        <ResultsScreen
          embedded
          sessionId={sessionId}
          session={session}
          onNewChat={onNewChat}
          resultsRefreshKey={resultsRefreshKey}
        />
      </main>
    </div>
  );
}
