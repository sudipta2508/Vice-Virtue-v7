import { useState, useEffect, useCallback } from "react";

const DIMENSIONS = [
  {
    name: "Transcendence", color: "#F5A623", angle: 90,
    traits: ["Appreciative", "Inspired", "Purposive", "Optimistic", "Creative", "Future-oriented"],
    description: "Seeing beyond the immediate to inspire others with vision and purpose.",
    deficit: { name: "Indifference", score: 1.2, desc: "Lack of vision or purpose; cynical detachment from meaning and aspiration." },
    virtue: { score: 4.2, desc: "Balanced sense of purpose with grounded optimism; inspires without losing touch with reality." },
    excess: { name: "Grandiosity", score: 2.1, desc: "Unrealistic idealism; disconnected visions that ignore practical constraints." },
  },
  {
    name: "Drive", color: "#C6960F", angle: 54,
    traits: ["Passionate", "Vigorous", "Results-oriented", "Demonstrates initiative", "Strives for excellence"],
    description: "Energy, ambition, and relentless pursuit of excellence.",
    deficit: { name: "Apathy", score: 0.8, desc: "Lack of initiative and energy; acceptance of mediocrity." },
    virtue: { score: 3.8, desc: "Strong initiative balanced with sustainable effort and realistic goal-setting." },
    excess: { name: "Obsessiveness", score: 2.6, desc: "Relentless drive that burns out self and others; unable to disengage." },
  },
  {
    name: "Collaboration", color: "#2E8B57", angle: 18,
    traits: ["Cooperative", "Collegial", "Open-minded", "Flexible", "Interconnected"],
    description: "Building bridges and fostering environments where diverse perspectives thrive.",
    deficit: { name: "Insularity", score: 1.0, desc: "Closed off, siloed thinking; resistance to others' input or partnership." },
    virtue: { score: 4.5, desc: "Actively seeks input while maintaining decisive leadership and clear direction." },
    excess: { name: "Compliance", score: 1.5, desc: "Over-accommodation that sacrifices direction; consensus paralysis." },
  },
  {
    name: "Humanity", color: "#008B8B", angle: -18,
    traits: ["Considerate", "Empathetic", "Compassionate", "Magnanimous", "Forgiving"],
    description: "Genuine care for others' wellbeing through empathy and compassion.",
    deficit: { name: "Callousness", score: 0.6, desc: "Disregard for others' feelings; cold transactional relationships." },
    virtue: { score: 3.6, desc: "Genuine empathy balanced with the ability to make tough people decisions." },
    excess: { name: "Permissiveness", score: 2.8, desc: "Over-empathy that avoids hard conversations and enables poor performance." },
  },
  {
    name: "Humility", color: "#4A90D9", angle: -54,
    traits: ["Self-aware", "Modest", "Reflective", "Curious", "Continuous learner", "Respectful", "Grateful", "Vulnerable"],
    description: "Knowing one's limitations, remaining open to learning, and crediting others.",
    deficit: { name: "Arrogance", score: 1.4, desc: "Inflated self-importance; dismissive of others' contributions and feedback." },
    virtue: { score: 4.0, desc: "Self-aware and open to growth while maintaining appropriate confidence." },
    excess: { name: "Self-deprecation", score: 1.1, desc: "Excessive self-doubt that undermines authority and decision-making." },
  },
  {
    name: "Integrity", color: "#7B2D8B", angle: -90,
    traits: ["Authentic", "Candid", "Transparent", "Principled", "Consistent"],
    description: "Aligning actions with values and maintaining transparency.",
    deficit: { name: "Deceitfulness", score: 0.4, desc: "Misalignment between words and actions; hidden agendas and manipulation." },
    virtue: { score: 4.7, desc: "Consistent alignment of words and actions with principled flexibility." },
    excess: { name: "Dogmatism", score: 1.8, desc: "Rigid adherence to principles without contextual adaptation; inflexible moralizing." },
  },
  {
    name: "Temperance", color: "#C2185B", angle: -126,
    traits: ["Patient", "Calm", "Composed", "Self-controlled", "Prudent"],
    description: "Maintaining composure under pressure and making measured decisions.",
    deficit: { name: "Volatility", score: 2.4, desc: "Emotional reactivity; unpredictable responses that destabilize teams." },
    virtue: { score: 3.4, desc: "Composed under pressure while remaining emotionally present and responsive." },
    excess: { name: "Detachment", score: 1.3, desc: "Emotional suppression that appears cold; disengaged from team dynamics." },
  },
  {
    name: "Justice", color: "#E91E63", angle: -162,
    traits: ["Fair", "Equitable", "Proportionate", "Even-handed", "Socially responsible"],
    description: "Ensuring fairness and holding everyone to consistent standards.",
    deficit: { name: "Partiality", score: 0.9, desc: "Favoritism, bias, and inconsistent application of standards." },
    virtue: { score: 4.1, desc: "Consistent fairness with the wisdom to recognize when equity requires differentiation." },
    excess: { name: "Rigidity", score: 1.6, desc: "Legalistic rule-following that ignores context and human complexity." },
  },
  {
    name: "Accountability", color: "#9C27B0", angle: -198,
    traits: ["Takes ownership", "Accepts consequences", "Conscientious", "Responsible"],
    description: "Owning decisions and outcomes without deflecting blame.",
    deficit: { name: "Negligence", score: 0.7, desc: "Blame-shifting, excuse-making, and abdication of responsibility." },
    virtue: { score: 3.9, desc: "Owns outcomes while empowering others to share responsibility appropriately." },
    excess: { name: "Martyrdom", score: 2.0, desc: "Absorbing all blame including others'; self-sacrificial to the point of dysfunction." },
  },
  {
    name: "Courage", color: "#E65100", angle: 126,
    traits: ["Brave", "Determined", "Tenacious", "Resilient", "Confident"],
    description: "Facing difficult situations head-on and standing up for what's right.",
    deficit: { name: "Cowardice", score: 0.5, desc: "Avoidance of conflict, risk, and difficult conversations." },
    virtue: { score: 4.3, desc: "Willingness to take calculated risks and speak truth to power with tact." },
    excess: { name: "Recklessness", score: 1.9, desc: "Impulsive risk-taking without regard for consequences; bravado over bravery." },
  },
];

const JUDGMENT = {
  name: "Judgment", color: "#A09C94", angle: 0,
  traits: ["Situationally aware", "Cognitively complex", "Analytical", "Decisive", "Critical thinker", "Intuitive", "Insightful", "Pragmatic", "Adaptable"],
  description: "The integrative core that enables all other dimensions — navigating complexity with wisdom.",
  deficit: { name: "Indecisiveness", score: 1.0, desc: "Paralysis in the face of ambiguity; inability to commit to a course of action." },
  virtue: { score: 4.4, desc: "Wise discernment that integrates analysis with intuition for timely decisions." },
  excess: { name: "Stubbornness", score: 1.5, desc: "Over-confidence in own analysis; closed to new information once decided." },
};

const ALL_DIMS = [...DIMENSIONS, JUDGMENT];

/* ─── Spectrum Gauge Component ─── */
const SpectrumGauge = ({ dim, compact = false }) => {
  const [anim, setAnim] = useState(false);
  useEffect(() => { const t = setTimeout(() => setAnim(true), 80); return () => clearTimeout(t); }, []);

  const virtuePos = (dim.virtue.score / 5) * 100;
  const deficitPos = (dim.deficit.score / 5) * 100;
  const excessPos = (dim.excess.score / 5) * 100;
  const h = compact ? 28 : 36;

  return (
    <div style={{ width: "100%", marginBottom: compact ? 0 : 8 }}>
      {!compact && (
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6, alignItems: "baseline" }}>
          <span style={{ fontSize: 10, color: "#EF4444", fontFamily: "'Cormorant Garamond', serif", fontStyle: "italic", fontWeight: 600, letterSpacing: 0.3 }}>
            {dim.deficit.name}
          </span>
          <span style={{ fontSize: 13, color: dim.color, fontFamily: "'Cormorant Garamond', serif", fontWeight: 700, letterSpacing: 0.5 }}>
            {dim.name}
          </span>
          <span style={{ fontSize: 10, color: "#F59E0B", fontFamily: "'Cormorant Garamond', serif", fontStyle: "italic", fontWeight: 600, letterSpacing: 0.3 }}>
            {dim.excess.name}
          </span>
        </div>
      )}
      <div style={{ position: "relative", height: h, width: "100%", borderRadius: h / 2 }}>
        {/* Track background */}
        <div style={{
          position: "absolute", inset: 0, borderRadius: h / 2, overflow: "hidden",
          background: "#18181B",
          border: "1px solid #2A2A30",
        }}>
          {/* Gradient zones */}
          <div style={{
            position: "absolute", inset: 0,
            background: `linear-gradient(90deg, 
              #EF444415 0%, #EF444408 20%, 
              ${dim.color}15 35%, ${dim.color}25 50%, ${dim.color}15 65%, 
              #F59E0B08 80%, #F59E0B15 100%)`,
          }} />
          {/* Center virtue zone highlight */}
          <div style={{
            position: "absolute", top: 0, bottom: 0,
            left: "30%", width: "40%",
            background: `${dim.color}10`,
            borderLeft: `1px dashed ${dim.color}25`,
            borderRight: `1px dashed ${dim.color}25`,
          }} />
        </div>

        {/* Zone labels inside track */}
        {!compact && (
          <>
            <span style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", fontSize: 9, color: "#EF444450", fontFamily: "'JetBrains Mono', monospace", zIndex: 2 }}>DEFICIT</span>
            <span style={{ position: "absolute", left: "50%", top: "50%", transform: "translate(-50%, -50%)", fontSize: 9, color: `${dim.color}40`, fontFamily: "'JetBrains Mono', monospace", zIndex: 2 }}>VIRTUE</span>
            <span style={{ position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)", fontSize: 9, color: "#F59E0B50", fontFamily: "'JetBrains Mono', monospace", zIndex: 2 }}>EXCESS</span>
          </>
        )}

        {/* Deficit marker */}
        <div style={{
          position: "absolute", left: `${anim ? deficitPos : 0}%`, top: "50%",
          transform: "translate(-50%, -50%)", zIndex: 5,
          transition: "left 1.2s cubic-bezier(0.22, 1, 0.36, 1)",
        }}>
          <div style={{
            width: compact ? 14 : 18, height: compact ? 14 : 18, borderRadius: "50%",
            background: "#EF4444", border: "2px solid #18181B",
            boxShadow: "0 0 8px #EF444460",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <span style={{ fontSize: 7, color: "#fff", fontWeight: 700 }}>D</span>
          </div>
          {!compact && (
            <span style={{
              position: "absolute", top: -16, left: "50%", transform: "translateX(-50%)",
              fontSize: 10, fontWeight: 700, color: "#EF4444",
              fontFamily: "'JetBrains Mono', monospace",
            }}>{dim.deficit.score.toFixed(1)}</span>
          )}
        </div>

        {/* Virtue marker */}
        <div style={{
          position: "absolute", left: `${anim ? virtuePos : 0}%`, top: "50%",
          transform: "translate(-50%, -50%)", zIndex: 6,
          transition: "left 1.2s cubic-bezier(0.22, 1, 0.36, 1) 0.15s",
        }}>
          <div style={{
            width: compact ? 18 : 24, height: compact ? 18 : 24, borderRadius: "50%",
            background: dim.color, border: "3px solid #18181B",
            boxShadow: `0 0 12px ${dim.color}80`,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <span style={{ fontSize: compact ? 7 : 9, color: "#fff", fontWeight: 700 }}>V</span>
          </div>
          {!compact && (
            <span style={{
              position: "absolute", top: -16, left: "50%", transform: "translateX(-50%)",
              fontSize: 11, fontWeight: 700, color: dim.color,
              fontFamily: "'JetBrains Mono', monospace",
            }}>{dim.virtue.score.toFixed(1)}</span>
          )}
        </div>

        {/* Excess marker */}
        <div style={{
          position: "absolute", left: `${anim ? excessPos : 0}%`, top: "50%",
          transform: "translate(-50%, -50%)", zIndex: 5,
          transition: "left 1.2s cubic-bezier(0.22, 1, 0.36, 1) 0.3s",
        }}>
          <div style={{
            width: compact ? 14 : 18, height: compact ? 14 : 18, borderRadius: "50%",
            background: "#F59E0B", border: "2px solid #18181B",
            boxShadow: "0 0 8px #F59E0B60",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <span style={{ fontSize: 7, color: "#fff", fontWeight: 700 }}>E</span>
          </div>
          {!compact && (
            <span style={{
              position: "absolute", top: -16, left: "50%", transform: "translateX(-50%)",
              fontSize: 10, fontWeight: 700, color: "#F59E0B",
              fontFamily: "'JetBrains Mono', monospace",
            }}>{dim.excess.score.toFixed(1)}</span>
          )}
        </div>
      </div>
    </div>
  );
};

/* ─── Score Card for detail view ─── */
const ScoreCard = ({ label, score, color, icon, desc }) => (
  <div style={{
    background: "#18181B", borderRadius: 12, padding: "14px 16px",
    border: `1px solid ${color}20`, position: "relative", overflow: "hidden",
  }}>
    <div style={{
      position: "absolute", top: 0, left: 0, width: `${(score / 5) * 100}%`, height: "100%",
      background: `${color}08`, transition: "width 1s ease",
    }} />
    <div style={{ position: "relative", zIndex: 1 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
        <span style={{ fontSize: 16 }}>{icon}</span>
        <span style={{ fontSize: 11, color: color, fontFamily: "'JetBrains Mono', monospace", fontWeight: 600, letterSpacing: 0.5, textTransform: "uppercase" }}>{label}</span>
        <span style={{ marginLeft: "auto", fontSize: 18, fontWeight: 800, color, fontFamily: "'JetBrains Mono', monospace" }}>{score.toFixed(1)}</span>
      </div>
      <p style={{ fontSize: 12, color: "#8A8680", lineHeight: 1.6, fontFamily: "'Cormorant Garamond', serif", fontSize: 13 }}>{desc}</p>
    </div>
  </div>
);

/* ─── Main Component ─── */
export default function LeaderCharacterVirtueVice() {
  const [mode, setMode] = useState("dashboard");
  const [selected, setSelected] = useState(null);
  const [hovered, setHovered] = useState(null);
  const [animate, setAnimate] = useState(false);

  useEffect(() => { setTimeout(() => setAnimate(true), 200); }, []);

  const cx = 220, cy = 220, outerR = 165, innerR = 52;

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
    DIMENSIONS.map(d => {
      const s = scoreKey === "virtue" ? d.virtue.score : scoreKey === "deficit" ? d.deficit.score : d.excess.score;
      const p = getRadarPos(d, s);
      return `${p.x},${p.y}`;
    }).join(" ");

  const activeDim = selected !== null
    ? (selected === "judgment" ? JUDGMENT : DIMENSIONS[selected])
    : hovered !== null
      ? (hovered === "judgment" ? JUDGMENT : DIMENSIONS[hovered])
      : null;

  const isSelected = (idx) => selected === idx;

  return (
    <div style={{
      minHeight: "100vh", background: "#0C0C0E", color: "#E8E6E1",
      fontFamily: "'Cormorant Garamond', serif", padding: "20px 12px",
      display: "flex", flexDirection: "column", alignItems: "center",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;0,700;1,400;1,600&family=JetBrains+Mono:wght@400;500;600;700;800&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        @keyframes fadeUp { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes drawIn { from { stroke-dashoffset: 3000; } to { stroke-dashoffset: 0; } }
        @keyframes gentlePulse { 0%,100% { opacity: 0.6; } 50% { opacity: 1; } }
      `}</style>

      {/* Header */}
      <div style={{ textAlign: "center", marginBottom: 20, animation: "fadeUp 0.7s ease-out" }}>
        <h1 style={{ fontSize: 30, fontWeight: 700, letterSpacing: 1, marginBottom: 4,
          background: "linear-gradient(135deg, #E8E6E1, #8A8680)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
        }}>
          Leader Character Assessment
        </h1>
        <p style={{ fontSize: 14, color: "#6A6660", fontStyle: "italic", fontWeight: 400 }}>
          Virtue & Vice Framework — Deficit · Virtue · Excess
        </p>
      </div>

      {/* Mode Toggle */}
      <div style={{
        display: "flex", gap: 4, background: "#141416", borderRadius: 10, padding: 4,
        marginBottom: 20, border: "1px solid #1E1E22", animation: "fadeUp 0.7s ease-out 0.1s both",
      }}>
        {[{ key: "dashboard", label: "Assessment" }, { key: "explore", label: "Explore" }].map(m => (
          <button key={m.key} onClick={() => { setMode(m.key); setSelected(null); }} style={{
            padding: "9px 22px", borderRadius: 7, border: "none", cursor: "pointer",
            fontFamily: "'JetBrains Mono', monospace", fontSize: 11, fontWeight: 600,
            letterSpacing: 0.8, textTransform: "uppercase",
            background: mode === m.key ? "#2A2A30" : "transparent",
            color: mode === m.key ? "#E8E6E1" : "#5A5650",
            transition: "all 0.3s ease",
          }}>{m.label}</button>
        ))}
      </div>

      {/* Legend */}
      <div style={{
        display: "flex", gap: 20, marginBottom: 16, animation: "fadeUp 0.7s ease-out 0.15s both",
      }}>
        {[
          { color: "#EF4444", label: "Deficit Vice", icon: "D" },
          { color: "#34D399", label: "Virtue", icon: "V" },
          { color: "#F59E0B", label: "Excess Vice", icon: "E" },
        ].map(l => (
          <div key={l.label} style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{
              width: 14, height: 14, borderRadius: "50%", background: l.color,
              display: "flex", alignItems: "center", justifyContent: "center",
              border: "2px solid #0C0C0E", fontSize: 7, color: "#fff", fontWeight: 700,
              fontFamily: "'JetBrains Mono', monospace",
            }}>{l.icon}</div>
            <span style={{ fontSize: 11, color: "#8A8680", fontFamily: "'JetBrains Mono', monospace", letterSpacing: 0.3 }}>{l.label}</span>
          </div>
        ))}
      </div>

      {/* Main */}
      <div style={{
        display: "flex", gap: 20, width: "100%", maxWidth: 1000,
        flexWrap: "wrap", justifyContent: "center",
        animation: "fadeUp 0.7s ease-out 0.2s both",
      }}>
        {/* SVG Wheel */}
        <div style={{ width: 440, height: 440, flexShrink: 0, position: "relative" }}>
          <svg viewBox="0 0 440 440" width="440" height="440">
            <defs>
              <radialGradient id="bg2" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#161618" />
                <stop offset="100%" stopColor="#0C0C0E" />
              </radialGradient>
            </defs>
            <circle cx={cx} cy={cy} r={210} fill="url(#bg2)" />

            {/* Grid rings */}
            {[1,2,3,4,5].map(r => (
              <circle key={r} cx={cx} cy={cy}
                r={innerR + 10 + ((r/5) * (outerR - innerR - 45))}
                fill="none" stroke="#fff" strokeOpacity={0.03} strokeWidth={0.5} />
            ))}

            {/* Spokes */}
            {DIMENSIONS.map((d, i) => {
              const p = getDimPos(d);
              return <line key={i} x1={cx} y1={cy} x2={p.x} y2={p.y} stroke="#fff" strokeOpacity={0.03} strokeWidth={0.5} />;
            })}

            {/* Radar polygons */}
            {mode === "dashboard" && animate && (
              <>
                <polygon points={makePolygon("deficit")} fill="#EF444408" stroke="#EF4444"
                  strokeWidth={1} strokeOpacity={0.25} strokeDasharray="4 4"
                  strokeDashoffset="3000" style={{ animation: "drawIn 2s ease-out 0.3s both" }} />
                <polygon points={makePolygon("virtue")} fill={`rgba(52,211,153,0.06)`} stroke="#34D399"
                  strokeWidth={1.5} strokeOpacity={0.4} strokeLinejoin="round"
                  strokeDasharray="3000" strokeDashoffset="3000"
                  style={{ animation: "drawIn 2s ease-out 0.5s both" }} />
                <polygon points={makePolygon("excess")} fill="#F59E0B08" stroke="#F59E0B"
                  strokeWidth={1} strokeOpacity={0.25} strokeDasharray="4 4"
                  strokeDashoffset="3000" style={{ animation: "drawIn 2s ease-out 0.7s both" }} />
              </>
            )}

            {/* Dimension nodes */}
            {DIMENSIONS.map((d, i) => {
              const pos = getDimPos(d);
              const active = selected === i || hovered === i;
              const nodeR = active ? 38 : 33;
              return (
                <g key={i} style={{ cursor: "pointer" }}
                  onClick={() => setSelected(selected === i ? null : i)}
                  onMouseEnter={() => setHovered(i)}
                  onMouseLeave={() => setHovered(null)}>
                  {active && <circle cx={pos.x} cy={pos.y} r={nodeR + 10} fill={d.color + "12"} />}
                  <circle cx={pos.x} cy={pos.y} r={nodeR}
                    fill={active ? d.color + "18" : "#111113"}
                    stroke={d.color} strokeWidth={active ? 2.5 : 1.2}
                    strokeOpacity={active ? 1 : 0.4}
                    style={{ transition: "all 0.3s ease" }} />
                  <text x={pos.x} y={pos.y - (mode === "dashboard" ? 5 : 0)}
                    textAnchor="middle" dominantBaseline="middle"
                    fill={active ? "#fff" : d.color} fontSize={8.5} fontWeight={700}
                    fontFamily="'JetBrains Mono', monospace" letterSpacing="0.2">
                    {d.name.length > 12 ? d.name.slice(0, 11) + "…" : d.name}
                  </text>
                  {mode === "dashboard" && (
                    <text x={pos.x} y={pos.y + 10}
                      textAnchor="middle" dominantBaseline="middle"
                      fill={d.color} fontSize={12} fontWeight={800}
                      fontFamily="'JetBrains Mono', monospace">
                      {d.virtue.score.toFixed(1)}
                    </text>
                  )}
                </g>
              );
            })}

            {/* Center Judgment */}
            <g style={{ cursor: "pointer" }}
              onClick={() => setSelected(selected === "judgment" ? null : "judgment")}
              onMouseEnter={() => setHovered("judgment")}
              onMouseLeave={() => setHovered(null)}>
              {(selected === "judgment" || hovered === "judgment") && (
                <circle cx={cx} cy={cy} r={innerR + 8} fill="rgba(255,255,255,0.03)" />
              )}
              <circle cx={cx} cy={cy} r={innerR}
                fill={selected === "judgment" || hovered === "judgment" ? "#1A1A1E" : "#111113"}
                stroke="#A09C94"
                strokeWidth={selected === "judgment" ? 2 : 1}
                strokeOpacity={selected === "judgment" || hovered === "judgment" ? 0.7 : 0.25}
                style={{ transition: "all 0.3s ease" }} />
              <text x={cx} y={cy - (mode === "dashboard" ? 6 : 0)}
                textAnchor="middle" dominantBaseline="middle"
                fill="#E8E6E1" fontSize={10} fontWeight={700}
                fontFamily="'JetBrains Mono', monospace" letterSpacing="0.5">
                Judgment
              </text>
              {mode === "dashboard" && (
                <text x={cx} y={cy + 11} textAnchor="middle" dominantBaseline="middle"
                  fill="#A09C94" fontSize={14} fontWeight={800}
                  fontFamily="'JetBrains Mono', monospace">
                  {JUDGMENT.virtue.score.toFixed(1)}
                </text>
              )}
            </g>
          </svg>
        </div>

        {/* Detail Panel */}
        <div style={{ flex: 1, minWidth: 300, maxWidth: 500, display: "flex", flexDirection: "column", gap: 14 }}>
          {activeDim ? (
            <div key={activeDim.name} style={{ animation: "fadeUp 0.35s ease-out" }}>
              {/* Header card */}
              <div style={{
                background: "#141416", borderRadius: 14, padding: "20px 22px",
                border: `1px solid ${activeDim.color}20`, marginBottom: 14,
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                  <div style={{
                    width: 10, height: 10, borderRadius: "50%", background: activeDim.color,
                    boxShadow: `0 0 10px ${activeDim.color}50`,
                  }} />
                  <h2 style={{ fontSize: 24, fontWeight: 700, color: activeDim.color, letterSpacing: 0.5 }}>
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

              {/* Three score cards */}
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <ScoreCard label={`Deficit — ${activeDim.deficit.name}`} score={activeDim.deficit.score}
                  color="#EF4444" icon="◉" desc={activeDim.deficit.desc} />
                <ScoreCard label="Virtue" score={activeDim.virtue.score}
                  color={activeDim.color} icon="◆" desc={activeDim.virtue.desc} />
                <ScoreCard label={`Excess — ${activeDim.excess.name}`} score={activeDim.excess.score}
                  color="#F59E0B" icon="◉" desc={activeDim.excess.desc} />
              </div>

              {/* Traits */}
              {mode === "explore" && (
                <div style={{
                  background: "#141416", borderRadius: 14, padding: "16px 20px",
                  border: "1px solid #1E1E22", marginTop: 14,
                }}>
                  <span style={{
                    fontSize: 10, color: "#5A5650", fontFamily: "'JetBrains Mono', monospace",
                    letterSpacing: 1, textTransform: "uppercase", fontWeight: 600,
                    display: "block", marginBottom: 10,
                  }}>Character Elements ({activeDim.traits.length})</span>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                    {activeDim.traits.map((t, i) => (
                      <span key={i} style={{
                        padding: "5px 12px", borderRadius: 20, fontSize: 12,
                        fontFamily: "'Cormorant Garamond', serif", fontWeight: 600,
                        background: activeDim.color + "12", color: activeDim.color,
                        border: `1px solid ${activeDim.color}25`,
                      }}>{t}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* Empty state */
            <div style={{
              background: "#141416", borderRadius: 14, padding: 36,
              border: "1px solid #1E1E22", textAlign: "center", minHeight: 240,
              display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
            }}>
              <div style={{ fontSize: 28, marginBottom: 12, opacity: 0.3 }}>⚖</div>
              <p style={{ fontSize: 15, color: "#5A5650", fontWeight: 600 }}>
                Select a dimension
              </p>
              <p style={{ fontSize: 12, color: "#3A3630", marginTop: 6, fontStyle: "italic" }}>
                Click on the wheel to view deficit, virtue & excess scores
              </p>
            </div>
          )}

          {/* All-dimensions overview (dashboard mode) */}
          {mode === "dashboard" && !activeDim && (
            <div style={{
              background: "#141416", borderRadius: 14, padding: "16px 18px",
              border: "1px solid #1E1E22",
            }}>
              <span style={{
                fontSize: 10, color: "#5A5650", fontFamily: "'JetBrains Mono', monospace",
                letterSpacing: 1, textTransform: "uppercase", fontWeight: 600,
                display: "block", marginBottom: 14,
              }}>All Dimensions — Virtue Scores</span>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {[...DIMENSIONS].sort((a, b) => b.virtue.score - a.virtue.score).map((d, i) => (
                  <div key={i} style={{ cursor: "pointer" }}
                    onClick={() => setSelected(DIMENSIONS.indexOf(d))}>
                    <SpectrumGauge dim={d} compact={false} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div style={{ marginTop: 28, textAlign: "center", animation: "fadeUp 0.7s ease-out 0.5s both" }}>
        <p style={{ fontSize: 11, color: "#2A2630", fontFamily: "'JetBrains Mono', monospace", letterSpacing: 1 }}>
          Leader Character Assessment · Virtue & Vice Framework · Multi-Agent AI Pipeline
        </p>
      </div>
    </div>
  );
}
