import { useState, useEffect, useCallback } from "react";
import {
  createSession,
  sendMessage,
  pollSession,
} from "./api/client";
import ChatScreen from "./components/ChatScreen";
import ChatPanel from "./components/ChatPanel";
import SplitAssessmentLayout from "./components/SplitAssessmentLayout";

export default function App() {
  const [sessionId, setSessionId] = useState(null);
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [resultsRefreshKey, setResultsRefreshKey] = useState(0);

  useEffect(() => {
    createSession()
      .then((s) => {
        setSessionId(s.id);
        setSession(s);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!sessionId) return;
    const prePhases = [
      "await_pre_add_more_consent",
      "await_pre_optional_dimension",
      "await_pre_optional_narrative",
      "await_pre_add_more_again",
    ];
    const needsPoll =
      session?.chat_phase === "analyzing" ||
      session?.followup_phase === "reassessing" ||
      prePhases.includes(session?.chat_phase) ||
      (session?.chat_phase === "active" && !session?.show_results);
    if (!needsPoll) return;
    return pollSession(sessionId, setSession, 2500);
  }, [sessionId, session?.chat_phase, session?.followup_phase, session?.show_results]);

  useEffect(() => {
    if (session?.followup_phase === "complete" && session?.has_refined) {
      setResultsRefreshKey((k) => k + 1);
    }
  }, [session?.followup_phase, session?.has_refined]);

  const handleSend = useCallback(
    async (text) => {
      if (!sessionId || sending) return;
      setSending(true);
      try {
        const updated = await sendMessage(sessionId, text);
        setSession(updated);
      } catch (e) {
        console.error(e);
      } finally {
        setSending(false);
      }
    },
    [sessionId, sending]
  );

  const handleNewChat = async () => {
    setLoading(true);
    try {
      const s = await createSession();
      setSessionId(s.id);
      setSession(s);
      setResultsRefreshKey(0);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !session) {
    return (
      <div
        style={{
          minHeight: "100vh",
          background: "#0C0C0E",
          color: "#8A8680",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        Loading…
      </div>
    );
  }

  if (session?.show_results) {
    return (
      <SplitAssessmentLayout
        sessionId={sessionId}
        session={session}
        onSend={handleSend}
        sending={sending}
        onNewChat={handleNewChat}
        resultsRefreshKey={resultsRefreshKey}
      />
    );
  }

  return (
    <ChatScreen>
      <ChatPanel session={session} onSend={handleSend} disabled={sending} />
    </ChatScreen>
  );
}
