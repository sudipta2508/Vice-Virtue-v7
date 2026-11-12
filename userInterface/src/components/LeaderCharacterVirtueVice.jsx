import { useState, useEffect, useMemo } from "react";
import SpectrumGauge from "./SpectrumGauge";

function formatDisplayScore(score) {
  if (score == null || score === "" || Number.isNaN(Number(score))) return "-";
  const s = Number(score);
  return s === Math.floor(s) ? String(Math.floor(s)) : s.toFixed(1);
}

const ScoreCard = ({ label, score, color, icon, desc }) => (
  <div
    style={{
      background: "#18181B",
      borderRadius: 12,
      padding: "14px 16px",
      border: `1px solid ${color}20`,
      position: "relative",
      overflow: "hidden",
    }}
  >
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: `${((score == null ? 0 : Number(score) || 0) / 5) * 100}%`,
        height: "100%",
        background: `${color}08`,
        transition: "width 1s ease",
      }}
    />
    <div style={{ position: "relative", zIndex: 1 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
        <span style={{ fontSize: 16 }}>{icon}</span>
        <span
          style={{
            fontSize: 11,
            color,
            fontFamily: "'JetBrains Mono', monospace",
            fontWeight: 600,
            letterSpacing: 0.5,
            textTransform: "uppercase",
          }}
        >
          {label}
        </span>
        <span
          style={{
            marginLeft: "auto",
            fontSize: 18,
            fontWeight: 800,
            color,
            fontFamily: "'JetBrains Mono', monospace",
          }}
        >
          {formatDisplayScore(score)}
        </span>
      </div>
      {desc ? (
        <p
          style={{
            fontSize: 13,
            color: "#8A8680",
            lineHeight: 1.6,
            fontFamily: "'Cormorant Garamond', serif",
          }}
        >
          {desc}
        </p>
      ) : null}
    </div>
  </div>
);

function DimensionDetail({ activeDim, viewMode }) {
  return (
    <div key={activeDim.name} style={{ animation: "fadeUp 0.35s ease-out" }}>
      <div
        style={{
          background: "#141416",
          borderRadius: 14,
          padding: "20px 22px",
          border: `1px solid ${activeDim.color}20`,
          marginBottom: 14,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
          <div
            style={{
              width: 10,
              height: 10,
              borderRadius: "50%",
              background: activeDim.color,
              boxShadow: `0 0 10px ${activeDim.color}50`,
            }}
          />
          <h2
            style={{
              fontSize: 24,
              fontWeight: 700,
              color: activeDim.color,
              letterSpacing: 0.5,
              margin: 0,
            }}
          >
            {activeDim.name}
          </h2>
        </div>
        <p style={{ fontSize: 14, color: "#8A8680", lineHeight: 1.7, fontStyle: "italic" }}>
          {activeDim.description}
        </p>
        <div style={{ marginTop: 16 }}>
          <SpectrumGauge dim={activeDim} />
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <ScoreCard
          label={`Deficit — ${activeDim.deficit?.name}`}
          score={activeDim.deficit?.score}
          color="#EF4444"
          icon="◉"
          desc={activeDim.deficit?.desc}
        />
        <ScoreCard
          label="Virtue"
          score={activeDim.virtue?.score}
          color={activeDim.color}
          icon="◆"
          desc={activeDim.virtue?.desc}
        />
        <ScoreCard
          label={`Excess — ${activeDim.excess?.name}`}
          score={activeDim.excess?.score}
          color="#F59E0B"
          icon="◉"
          desc={activeDim.excess?.desc}
        />
      </div>

      {viewMode === "explore" && activeDim.traits?.length > 0 && (
        <div
          style={{
            background: "#141416",
            borderRadius: 14,
            padding: "16px 20px",
            border: "1px solid #1E1E22",
            marginTop: 14,
          }}
        >
          <span
            style={{
              fontSize: 10,
              color: "#5A5650",
              fontFamily: "'JetBrains Mono', monospace",
              letterSpacing: 1,
              textTransform: "uppercase",
              fontWeight: 600,
              display: "block",
              marginBottom: 10,
            }}
          >
            Character Elements ({activeDim.traits.length})
          </span>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {activeDim.traits.map((t, i) => (
              <span
                key={i}
                style={{
                  padding: "5px 12px",
                  borderRadius: 20,
                  fontSize: 12,
                  fontFamily: "'Cormorant Garamond', serif",
                  fontWeight: 600,
                  background: activeDim.color + "12",
                  color: activeDim.color,
                  border: `1px solid ${activeDim.color}25`,
                }}
              >
                {t}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function LeaderCharacterVirtueVice({
  chartData,
  chartLabel,
  viewMode = "dashboard",
  showWheelScores = false,
  selectedName = null,
  onSelectDimension,
  detailPanel = null,
}) {
  const [hovered, setHovered] = useState(null);
  const [animate, setAnimate] = useState(false);

  const DIMENSIONS = chartData?.dimensions || [];
  const JUDGMENT = chartData?.judgment;
  const gradientId = `bg-${(chartLabel || "main").replace(/\s+/g, "-")}`;

  useEffect(() => {
    setAnimate(false);
    const t = setTimeout(() => setAnimate(true), 200);
    return () => clearTimeout(t);
  }, [chartData]);

  const cx = 220;
  const cy = 220;
  const outerR = 165;
  const innerR = 52;
  const svgSize = 440;

  const getDimPos = (d) => {
    const rad = (d.angle * Math.PI) / 180;
    return { x: cx + outerR * Math.cos(rad), y: cy - outerR * Math.sin(rad) };
  };

  const getRadarPos = (d, score) => {
    const rad = (d.angle * Math.PI) / 180;
    const r = innerR + 10 + ((score / 5) * (outerR - innerR - 45));
    return { x: cx + r * Math.cos(rad), y: cy - r * Math.sin(rad) };
  };

  const makePolygon = (scoreKey) =>
    DIMENSIONS.map((d) => {
      const s =
        scoreKey === "virtue"
          ? d.virtue?.score ?? 0
          : scoreKey === "deficit"
            ? d.deficit?.score ?? 0
            : d.excess?.score ?? 0;
      const p = getRadarPos(d, s);
      return `${p.x},${p.y}`;
    }).join(" ");

  const spectrumDimensions = useMemo(() => {
    const sorted = [...DIMENSIONS].sort(
      (a, b) => (b.virtue?.score ?? 0) - (a.virtue?.score ?? 0)
    );
    return JUDGMENT ? [JUDGMENT, ...sorted] : sorted;
  }, [DIMENSIONS, JUDGMENT]);

  const activeDim = useMemo(() => {
    if (selectedName === "Judgment") return JUDGMENT;
    if (selectedName) return DIMENSIONS.find((x) => x.name === selectedName) || null;
    if (hovered === "judgment") return JUDGMENT;
    if (typeof hovered === "number") return DIMENSIONS[hovered] ?? null;
    return null;
  }, [selectedName, hovered, DIMENSIONS, JUDGMENT]);

  const selected =
    selectedName === "Judgment"
      ? "judgment"
      : selectedName
        ? DIMENSIONS.findIndex((d) => d.name === selectedName)
        : null;

  const handleDimClick = (idx) => {
    const name = DIMENSIONS[idx]?.name;
    if (!onSelectDimension) return;
    onSelectDimension(selected === idx ? null : name);
  };

  const handleJudgmentClick = () => {
    if (!onSelectDimension) return;
    onSelectDimension(selected === "judgment" ? null : "Judgment");
  };

  const showRadar = viewMode === "dashboard";

  if (!chartData) {
    return (
      <div style={{ color: "#5A5650", textAlign: "center", padding: 40 }}>Loading chart data…</div>
    );
  }

  return (
    <div style={{ width: "100%", maxWidth: 1000 }}>
      <style>{`
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(16px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes drawIn {
          from { stroke-dashoffset: 3000; }
          to { stroke-dashoffset: 0; }
        }
      `}</style>

      {chartLabel && (
        <p
          style={{
            textAlign: "center",
            fontSize: 11,
            color: "#8A8680",
            fontFamily: "'JetBrains Mono', monospace",
            letterSpacing: 1,
            textTransform: "uppercase",
            marginBottom: 12,
          }}
        >
          {chartLabel}
        </p>
      )}

      <div
        style={{
          display: "flex",
          gap: 20,
          width: "100%",
          flexWrap: "wrap",
          justifyContent: "center",
          animation: "fadeUp 0.7s ease-out 0.2s both",
        }}
      >
        <div style={{ width: svgSize, height: svgSize, flexShrink: 0 }}>
          <svg viewBox="0 0 440 440" width={svgSize} height={svgSize}>
            <defs>
              <radialGradient id={gradientId} cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#161618" />
                <stop offset="100%" stopColor="#0C0C0E" />
              </radialGradient>
            </defs>
            <circle cx={cx} cy={cy} r={210} fill={`url(#${gradientId})`} />

            {[1, 2, 3, 4, 5].map((r) => (
              <circle
                key={r}
                cx={cx}
                cy={cy}
                r={innerR + 10 + (r / 5) * (outerR - innerR - 45)}
                fill="none"
                stroke="#fff"
                strokeOpacity={0.03}
                strokeWidth={0.5}
              />
            ))}

            {DIMENSIONS.map((d, i) => {
              const p = getDimPos(d);
              return (
                <line
                  key={i}
                  x1={cx}
                  y1={cy}
                  x2={p.x}
                  y2={p.y}
                  stroke="#fff"
                  strokeOpacity={0.03}
                  strokeWidth={0.5}
                />
              );
            })}

            {showRadar && animate && (
              <>
                <polygon
                  points={makePolygon("deficit")}
                  fill="#EF444408"
                  stroke="#EF4444"
                  strokeWidth={1}
                  strokeOpacity={0.25}
                  strokeDasharray="4 4"
                />
                <polygon
                  points={makePolygon("virtue")}
                  fill="rgba(52,211,153,0.06)"
                  stroke="#34D399"
                  strokeWidth={1.5}
                  strokeOpacity={0.4}
                  strokeLinejoin="round"
                />
                <polygon
                  points={makePolygon("excess")}
                  fill="#3B82F608"
                  stroke="#3B82F6"
                  strokeWidth={1}
                  strokeOpacity={0.25}
                  strokeDasharray="4 4"
                />
              </>
            )}

            {DIMENSIONS.map((d, i) => {
              const pos = getDimPos(d);
              const active = selected === i || hovered === i;
              const nodeR = active ? 38 : 33;
              return (
                <g
                  key={d.name}
                  style={{ cursor: onSelectDimension ? "pointer" : "default" }}
                  onClick={() => handleDimClick(i)}
                  onMouseEnter={() => setHovered(i)}
                  onMouseLeave={() => setHovered(null)}
                >
                  {active && <circle cx={pos.x} cy={pos.y} r={nodeR + 10} fill={d.color + "12"} />}
                  <circle
                    cx={pos.x}
                    cy={pos.y}
                    r={nodeR}
                    fill={active ? d.color + "18" : "#111113"}
                    stroke={d.color}
                    strokeWidth={active ? 2.5 : 1.2}
                    strokeOpacity={active ? 1 : 0.4}
                  />
                  <text
                    x={pos.x}
                    y={pos.y - (showWheelScores ? 5 : 0)}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fill={active ? "#fff" : d.color}
                    fontSize={8.5}
                    fontWeight={700}
                    fontFamily="'JetBrains Mono', monospace"
                    letterSpacing="0.2"
                  >
                    {d.name.length > 12 ? d.name.slice(0, 11) + "…" : d.name}
                  </text>
                  {showWheelScores && (
                    <text
                      x={pos.x}
                      y={pos.y + 10}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fill={d.color}
                      fontSize={12}
                      fontWeight={800}
                      fontFamily="'JetBrains Mono', monospace"
                    >
                      {formatDisplayScore(d.virtue?.score)}
                    </text>
                  )}
                </g>
              );
            })}

            {JUDGMENT && (
              <g
                style={{ cursor: onSelectDimension ? "pointer" : "default" }}
                onClick={handleJudgmentClick}
                onMouseEnter={() => setHovered("judgment")}
                onMouseLeave={() => setHovered(null)}
              >
                {(selected === "judgment" || hovered === "judgment") && (
                  <circle cx={cx} cy={cy} r={innerR + 8} fill="rgba(255,255,255,0.03)" />
                )}
                <circle
                  cx={cx}
                  cy={cy}
                  r={innerR}
                  fill={selected === "judgment" || hovered === "judgment" ? "#1A1A1E" : "#111113"}
                  stroke="#A09C94"
                  strokeWidth={selected === "judgment" ? 2 : 1}
                  strokeOpacity={selected === "judgment" || hovered === "judgment" ? 0.7 : 0.25}
                />
                <text
                  x={cx}
                  y={cy - (showWheelScores ? 6 : 0)}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill="#E8E6E1"
                  fontSize={10}
                  fontWeight={700}
                  fontFamily="'JetBrains Mono', monospace"
                  letterSpacing="0.5"
                >
                  Judgment
                </text>
                {showWheelScores && (
                  <text
                    x={cx}
                    y={cy + 11}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fill="#A09C94"
                    fontSize={14}
                    fontWeight={800}
                    fontFamily="'JetBrains Mono', monospace"
                  >
                    {formatDisplayScore(JUDGMENT.virtue?.score)}
                  </text>
                )}
              </g>
            )}
          </svg>
        </div>

        <div
          style={{
            flex: 1,
            minWidth: 300,
            maxWidth: 500,
            display: "flex",
            flexDirection: "column",
            gap: 14,
          }}
        >
          {viewMode === "explore" && detailPanel ? (
            detailPanel
          ) : activeDim ? (
            <DimensionDetail activeDim={activeDim} viewMode={viewMode} />
          ) : (
            <div
              style={{
                background: "#141416",
                borderRadius: 14,
                padding: 36,
                border: "1px solid #1E1E22",
                textAlign: "center",
                minHeight: 240,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <div style={{ fontSize: 28, marginBottom: 12, opacity: 0.3 }}>⚖</div>
              <p style={{ fontSize: 15, color: "#5A5650", fontWeight: 600 }}>Select a dimension</p>
              <p style={{ fontSize: 12, color: "#3A3630", marginTop: 6, fontStyle: "italic" }}>
                Click on the wheel to view deficit, virtue & excess scores
              </p>
            </div>
          )}

          {viewMode === "dashboard" && !activeDim && (
            <div
              style={{
                background: "#141416",
                borderRadius: 14,
                padding: "16px 18px",
                border: "1px solid #1E1E22",
              }}
            >
              <span
                style={{
                  fontSize: 10,
                  color: "#5A5650",
                  fontFamily: "'JetBrains Mono', monospace",
                  letterSpacing: 1,
                  textTransform: "uppercase",
                  fontWeight: 600,
                  display: "block",
                  marginBottom: 14,
                }}
              >
                All Dimensions — Virtue Scores
              </span>
              <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
                {spectrumDimensions.map((d) => (
                  <div
                    key={d.name}
                    style={{ cursor: onSelectDimension ? "pointer" : "default" }}
                    onClick={() => onSelectDimension?.(d.name)}
                  >
                    <SpectrumGauge dim={d} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
