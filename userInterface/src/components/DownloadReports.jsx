import { useState } from "react";
import { downloadReport } from "../api/client";

const btnStyle = {
  padding: "8px 14px",
  borderRadius: 8,
  border: "1px solid #2A2A30",
  background: "#141416",
  color: "#C8C4BC",
  cursor: "pointer",
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 10,
  letterSpacing: 0.3,
  textDecoration: "none",
  display: "inline-block",
};

function DownloadButton({ sessionId, reportType, format, label, disabled }) {
  const [busy, setBusy] = useState(false);

  const handleClick = async (e) => {
    e.preventDefault();
    if (disabled || busy) return;
    setBusy(true);
    try {
      await downloadReport(sessionId, reportType, format);
    } catch (err) {
      console.error(err);
      alert("Download failed. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={disabled || busy}
      style={{
        ...btnStyle,
        opacity: disabled || busy ? 0.45 : 1,
        cursor: disabled || busy ? "not-allowed" : "pointer",
      }}
    >
      {busy ? "…" : label}
    </button>
  );
}

function ReportGroup({ title, subtitle, sessionId, reportType, disabled }) {
  return (
    <div
      style={{
        flex: "1 1 280px",
        minWidth: 260,
        padding: "14px 16px",
        borderRadius: 10,
        border: "1px solid #1E1E22",
        background: "#101012",
      }}
    >
      <div
        style={{
          fontSize: 12,
          fontWeight: 600,
          color: "#E8E6E1",
          marginBottom: 4,
          fontFamily: "'JetBrains Mono', monospace",
          letterSpacing: 0.5,
        }}
      >
        {title}
      </div>
      <p style={{ fontSize: 11, color: "#6A6660", margin: "0 0 12px", fontStyle: "italic" }}>
        {subtitle}
      </p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        <DownloadButton
          sessionId={sessionId}
          reportType={reportType}
          format="json"
          label="Download JSON"
          disabled={disabled}
        />
        <DownloadButton
          sessionId={sessionId}
          reportType={reportType}
          format="pdf"
          label="Download PDF"
          disabled={disabled}
        />
      </div>
    </div>
  );
}

export default function DownloadReports({ sessionId, showBaseline = true, showRefined = false }) {
  if (!showBaseline && !showRefined) return null;

  return (
    <section
      style={{
        width: "100%",
        maxWidth: 1000,
        marginBottom: 20,
      }}
    >
      <h2
        style={{
          fontSize: 13,
          fontWeight: 600,
          color: "#8A8680",
          margin: "0 0 12px",
          fontFamily: "'JetBrains Mono', monospace",
          letterSpacing: 1,
          textTransform: "uppercase",
        }}
      >
        Download reports
      </h2>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 14 }}>
        {showBaseline && (
          <ReportGroup
            title="Initial assessment"
            subtitle="Baseline — narrative only"
            sessionId={sessionId}
            reportType="baseline"
            disabled={false}
          />
        )}
        {showRefined && (
          <ReportGroup
            title="Reassessed"
            subtitle="Refined — after follow-up"
            sessionId={sessionId}
            reportType="refined"
            disabled={false}
          />
        )}
      </div>
    </section>
  );
}
