import { useState, useEffect, useCallback } from "react";
import { getResults, getDimensionItems } from "../api/client";
import LeaderCharacterVirtueVice from "./LeaderCharacterVirtueVice";
import DualChartLayout from "./DualChartLayout";
import ItemDetailPanel from "./ItemDetailPanel";
import DownloadReports from "./DownloadReports";

export default function ResultsScreen({
  sessionId,
  session,
  onNewChat,
  embedded = false,
  resultsRefreshKey = 0,
}) {
  const [results, setResults] = useState(null);
  const [mode, setMode] = useState("dashboard");
  const [assessmentSelected, setAssessmentSelected] = useState(null);
  const [exploreSelected, setExploreSelected] = useState(null);
  const [items, setItems] = useState([]);
  const [itemsLoading, setItemsLoading] = useState(false);
  const [itemSource, setItemSource] = useState("refined");

  const showDual = session?.ui_screen === "results_with_followup" && session?.has_refined;

  useEffect(() => {
    getResults(sessionId)
      .then(setResults)
      .catch(console.error);
  }, [sessionId, resultsRefreshKey, session?.has_refined, session?.followup_phase]);

  useEffect(() => {
    if (showDual) setItemSource("refined");
    else setItemSource("baseline");
  }, [showDual]);

  const chartBaseline = results?.baseline;
  const chartRefined = results?.refined;

  const exploreChart = showDual && itemSource === "refined" ? chartRefined : chartBaseline;

  const dimensionColor =
    exploreChart?.dimensions?.find((d) => d.name === exploreSelected)?.color ||
    exploreChart?.judgment?.color ||
    "#8A8680";

  const loadItems = useCallback(
    async (dim, source) => {
      if (!dim) return;
      setItemsLoading(true);
      try {
        const data = await getDimensionItems(sessionId, dim, source);
        setItems(data.items || []);
      } catch (e) {
        console.error(e);
        setItems([]);
      } finally {
        setItemsLoading(false);
      }
    },
    [sessionId]
  );

  useEffect(() => {
    if (mode === "explore" && exploreSelected) {
      loadItems(exploreSelected, itemSource);
    }
  }, [mode, exploreSelected, itemSource, loadItems]);

  const handleAssessmentSelect = (name) => {
    setAssessmentSelected(name);
  };

  const handleExploreSelect = (name) => {
    setExploreSelected(name);
  };

  const outerStyle = embedded
    ? {
        height: "100%",
        background: "#0C0C0E",
        color: "#E8E6E1",
        fontFamily: "'Cormorant Garamond', serif",
        padding: "12px 16px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        overflow: "auto",
        boxSizing: "border-box",
      }
    : {
        minHeight: "100vh",
        background: "#0C0C0E",
        color: "#E8E6E1",
        fontFamily: "'Cormorant Garamond', serif",
        padding: "20px 12px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
      };

  return (
    <div style={outerStyle}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;0,700&family=JetBrains+Mono:wght@400;500;600&display=swap');
      `}</style>

      <header
        style={{
          textAlign: "center",
          marginBottom: embedded ? 12 : 20,
          width: "100%",
          maxWidth: embedded ? "100%" : 1000,
          flexShrink: 0,
        }}
      >
        <h1
          style={{
            fontSize: embedded ? 22 : 30,
            fontWeight: 700,
            background: "linear-gradient(135deg, #E8E6E1, #8A8680)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            margin: 0,
          }}
        >
          Leader Character Assessment
        </h1>
        <p style={{ fontSize: embedded ? 12 : 14, color: "#6A6660", fontStyle: "italic", margin: "4px 0 0" }}>
          Virtue & Vice Framework — Deficit · Virtue · Excess
        </p>
        {onNewChat && (
          <button
            type="button"
            onClick={onNewChat}
            style={{
              marginTop: 10,
              padding: "8px 16px",
              borderRadius: 8,
              border: "1px solid #2A2A30",
              background: "#141416",
              color: "#8A8680",
              cursor: "pointer",
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 10,
            }}
          >
            New conversation
          </button>
        )}
      </header>

      <div
        style={{
          display: "flex",
          gap: 4,
          background: "#141416",
          borderRadius: 10,
          padding: 4,
          marginBottom: 20,
          border: "1px solid #1E1E22",
        }}
      >
        {[
          { key: "dashboard", label: "Summary" },
          { key: "explore", label: "Detailed Analysis" },
        ].map((m) => (
          <button
            key={m.key}
            type="button"
            onClick={() => {
              setMode(m.key);
              if (m.key === "dashboard") setExploreSelected(null);
              if (m.key === "explore") setAssessmentSelected(null);
            }}
            style={{
              padding: "9px 22px",
              borderRadius: 7,
              border: "none",
              cursor: "pointer",
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: 0.8,
              textTransform: "uppercase",
              background: mode === m.key ? "#2A2A30" : "transparent",
              color: mode === m.key ? "#E8E6E1" : "#5A5650",
            }}
          >
            {m.label}
          </button>
        ))}
      </div>

      {results && (
        <DownloadReports
          sessionId={sessionId}
          showBaseline
          showRefined={Boolean(session?.has_refined)}
        />
      )}

      <div style={{ display: "flex", gap: 20, marginBottom: 16 }}>
        {[
          { color: "#EF4444", label: "Deficit Vice", icon: "D" },
          { color: "#34D399", label: "Virtue", icon: "V" },
          { color: "#F59E0B", label: "Excess Vice", icon: "E" },
        ].map((l) => (
          <div key={l.label} style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div
              style={{
                width: 14,
                height: 14,
                borderRadius: "50%",
                background: l.color,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 7,
                color: "#fff",
                fontWeight: 700,
                fontFamily: "'JetBrains Mono', monospace",
              }}
            >
              {l.icon}
            </div>
            <span style={{ fontSize: 11, color: "#8A8680", fontFamily: "'JetBrains Mono', monospace" }}>
              {l.label}
            </span>
          </div>
        ))}
      </div>

      {!results ? (
        <p style={{ color: "#8A8680" }}>Loading results…</p>
      ) : mode === "dashboard" ? (
        <DualChartLayout
          baseline={chartBaseline}
          refined={chartRefined}
          hasDual={showDual}
          selectedName={assessmentSelected}
          onSelectDimension={handleAssessmentSelect}
        />
      ) : (
        <div style={{ width: "100%", maxWidth: 1000 }}>
          <LeaderCharacterVirtueVice
            chartData={exploreChart}
            viewMode="explore"
            selectedName={exploreSelected}
            onSelectDimension={handleExploreSelect}
            detailPanel={
              <ItemDetailPanel
                dimensionName={exploreSelected}
                dimensionColor={dimensionColor}
                items={items}
                loading={itemsLoading}
                source={itemSource}
                onSourceChange={setItemSource}
                showSourceToggle={showDual}
              />
            }
          />
        </div>
      )}

      {!embedded && (
        <footer style={{ marginTop: 28, textAlign: "center" }}>
          <p style={{ fontSize: 11, color: "#2A2630", fontFamily: "'JetBrains Mono', monospace" }}>
            Leader Character Assessment · Virtue & Vice Framework · LangGraph v.7
          </p>
        </footer>
      )}
    </div>
  );
}
