import { useState } from "react";
import LeaderCharacterVirtueVice from "./LeaderCharacterVirtueVice";

const toggleBtnStyle = (active) => ({
  padding: "8px 18px",
  borderRadius: 7,
  border: "none",
  cursor: "pointer",
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 11,
  fontWeight: 600,
  letterSpacing: 0.8,
  textTransform: "uppercase",
  background: active ? "#2A2A30" : "transparent",
  color: active ? "#E8E6E1" : "#5A5650",
});

export default function DualChartLayout({
  baseline,
  refined,
  hasDual = false,
  selectedName,
  onSelectDimension,
}) {
  const [assessmentSource, setAssessmentSource] = useState("refined");

  if (hasDual && baseline && refined) {
    const chartData = assessmentSource === "refined" ? refined : baseline;
    const chartLabel =
      assessmentSource === "refined" ? "After Follow-up" : "Initial Assessment";

    return (
      <div
        style={{
          width: "100%",
          maxWidth: 1100,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 16,
        }}
      >
        <div
          style={{
            display: "flex",
            gap: 4,
            background: "#141416",
            borderRadius: 10,
            padding: 4,
            border: "1px solid #1E1E22",
          }}
        >
          <button
            type="button"
            style={toggleBtnStyle(assessmentSource === "refined")}
            onClick={() => setAssessmentSource("refined")}
          >
            After Follow-up
          </button>
          <button
            type="button"
            style={toggleBtnStyle(assessmentSource === "baseline")}
            onClick={() => setAssessmentSource("baseline")}
          >
            Initial Assessment
          </button>
        </div>

        <LeaderCharacterVirtueVice
          chartData={chartData}
          chartLabel={chartLabel}
          viewMode="dashboard"
          selectedName={selectedName}
          onSelectDimension={onSelectDimension}
        />
      </div>
    );
  }

  return (
    <LeaderCharacterVirtueVice
      chartData={baseline}
      viewMode="dashboard"
      selectedName={selectedName}
      onSelectDimension={onSelectDimension}
    />
  );
}
