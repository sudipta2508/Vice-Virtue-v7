import { useState } from "react";

const clsLabel = { virtue: "Virtue", deficit_vice: "Deficit Vice", excess_vice: "Excess Vice" };

function formatItemScore(score) {
  if (score == null || score === "") return "-";
  return String(score);
}

function dominantLabelFromScores(virtue, deficit, excess) {
  const hasAny = [virtue, deficit, excess].some((s) => s != null && s !== "");
  if (!hasAny) return "Uncertain";
  const v = Number(virtue) || 0;
  const d = Number(deficit) || 0;
  const e = Number(excess) || 0;
  const max = Math.max(v, d, e);
  if (max === 0) return "Uncertain";
  const tops = [];
  if (virtue != null && v === max) tops.push("Virtue");
  if (deficit != null && d === max) tops.push("Deficit");
  if (excess != null && e === max) tops.push("Excess");
  return tops.length === 1 ? tops[0] : "Uncertain";
}

const TIER_ORDER = ["explicit", "strong_implicit", "weak"];

const TIER_LABEL = {
  explicit: "Explicit",
  strong_implicit: "Strong-implicit",
  weak: "Weak",
};

const TIER_COLOR = {
  explicit: "#34D399",
  strong_implicit: "#60A5FA",
  weak: "#A8A29E",
};

const TIER_FALLBACK = "strong_implicit";

function normalizeTier(tier) {
  if (!tier || typeof tier !== "string") return TIER_FALLBACK;
  const key = tier.trim().toLowerCase().replace(/-/g, "_").replace(/ /g, "_");
  if (key === "explicit") return "explicit";
  if (key === "strong_implicit" || key === "strongimplicit" || key === "implicit") return "strong_implicit";
  if (key === "weak" || key === "weak_implicit") return "weak";
  return TIER_FALLBACK;
}

function TierBadge({ tier, reasoning, weight }) {
  const normalized = normalizeTier(tier);
  const label = TIER_LABEL[normalized] || normalized;
  const color = TIER_COLOR[normalized] || "#8A8680";
  const weightText = weight != null && weight !== "" ? ` · w${Number(weight).toFixed(1)}` : "";
  return (
    <span
      title={reasoning || label}
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: 10,
        fontFamily: "'JetBrains Mono', monospace",
        letterSpacing: 0.3,
        color: "#0C0C0E",
        background: color,
        verticalAlign: "middle",
        fontWeight: 600,
      }}
    >
      {label}
      {weightText}
    </span>
  );
}

function AlsoUsedTags({ locations }) {
  if (!locations?.length) return null;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
      {locations.map((loc, i) => {
        const label = `#${loc.dimension} #${loc.item} #${loc.cls}`;
        return (
          <span
            key={`${loc.dimension}-${loc.item}-${loc.cls}-${i}`}
            title={`Also used as ${loc.cls} evidence for ${loc.item} under ${loc.dimension}`}
            style={{
              display: "inline-block",
              padding: "2px 8px",
              borderRadius: 4,
              fontSize: 10,
              fontFamily: "'JetBrains Mono', monospace",
              letterSpacing: 0.2,
              color: "#C4B5FD",
              background: "#1E1B2E",
              border: "1px solid #4C1D95",
            }}
          >
            {label}
          </span>
        );
      })}
    </div>
  );
}

function EvidenceSnippet({ ev, color }) {
  const tier = normalizeTier(ev.strength_tier);
  return (
    <li
      style={{
        marginBottom: 8,
        padding: "10px 12px",
        background: "#18181B",
        borderRadius: 8,
        borderLeft: `3px solid ${TIER_COLOR[tier] || color}`,
        fontSize: 12,
        color: "#C8C6C0",
        lineHeight: 1.5,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
        <TierBadge tier={tier} reasoning={ev.tier_reasoning} weight={ev.weight} />
        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#5A5650" }}>
          {ev.id}
          {ev.source_position ? ` · ${ev.source_position}` : ""}
        </span>
      </div>
      <p style={{ marginTop: 6, marginBottom: 0 }}>{ev.text}</p>
      <AlsoUsedTags locations={ev.also_used} />
      {ev.tier_reasoning ? (
        <p style={{ marginTop: 6, marginBottom: 0, fontSize: 11, color: "#5A5650", fontStyle: "italic" }}>
          Tier: {ev.tier_reasoning}
        </p>
      ) : null}
    </li>
  );
}

function EvidenceList({ items, color }) {
  if (!items?.length) return <p style={{ fontSize: 12, color: "#5A5650", fontStyle: "italic" }}>No evidence</p>;

  const grouped = { explicit: [], strong_implicit: [], weak: [] };
  for (const ev of items) {
    const tier = normalizeTier(ev.strength_tier);
    grouped[tier].push(ev);
  }

  return (
    <div style={{ marginTop: 6 }}>
      {TIER_ORDER.map((tier) => {
        const bucket = grouped[tier];
        if (!bucket.length) return null;
        return (
          <div key={tier} style={{ marginBottom: 10 }}>
            <p
              style={{
                margin: "0 0 6px",
                fontSize: 10,
                fontFamily: "'JetBrains Mono', monospace",
                letterSpacing: 0.6,
                textTransform: "uppercase",
                color: TIER_COLOR[tier],
              }}
            >
              {TIER_LABEL[tier]} ({bucket.length})
            </p>
            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {bucket.map((ev, i) => (
                <EvidenceSnippet key={`${tier}-${i}`} ev={ev} color={color} />
              ))}
            </ul>
          </div>
        );
      })}
    </div>
  );
}

function FlagsBlock({ flags }) {
  if (!flags || Object.keys(flags).length === 0) return null;
  return (
    <div style={{ fontSize: 12, color: "#8A8680", lineHeight: 1.6 }}>
      {flags.socialDesirability && (
        <p>
          <strong style={{ color: "#F59E0B" }}>Social desirability:</strong>{" "}
          {flags.socialDesirabilityReasoning || "flagged"}
        </p>
      )}
      {flags.negativeBehavior && (
        <p>
          <strong style={{ color: "#EF4444" }}>Negative behavior:</strong>{" "}
          {flags.negativeBehaviorReasoning || "flagged"}
        </p>
      )}
      {flags.situationalInconsistency > 0 && (
        <p>Situational inconsistency count: {flags.situationalInconsistency}</p>
      )}
      {flags.consistency && <p>Consistency: {flags.consistency}</p>}
      {flags.frequency && (
        <p>
          Frequency — supporting: {flags.frequency.supporting ?? 0}, contradictory:{" "}
          {flags.frequency.contradictory ?? 0}
        </p>
      )}
    </div>
  );
}

function ItemCard({ item, dimensionColor }) {
  const [open, setOpen] = useState(false);
  const co = item.scores || {};

  return (
    <div
      style={{
        background: "#141416",
        borderRadius: 12,
        border: "1px solid #1E1E22",
        marginBottom: 12,
        overflow: "hidden",
      }}
    >
      <button
        type="button"
        onClick={() => setOpen(!open)}
        style={{
          width: "100%",
          padding: "14px 16px",
          background: "transparent",
          border: "none",
          cursor: "pointer",
          textAlign: "left",
          color: "#E8E6E1",
          fontFamily: "'Cormorant Garamond', serif",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontSize: 16, fontWeight: 700, color: dimensionColor }}>{item.virtue}</span>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#8A8680" }}>
            V:{formatItemScore(co.virtue)} D:{formatItemScore(co.deficit_vice)} E:
            {formatItemScore(co.excess_vice)} ·{" "}
            {dominantLabelFromScores(co.virtue, co.deficit_vice, co.excess_vice)}
          </span>
        </div>
        {item.catalog?.item_description && (
          <p style={{ fontSize: 12, color: "#6A6660", marginTop: 6, fontStyle: "italic" }}>
            {item.catalog.item_description}
          </p>
        )}
      </button>
      {open && (
        <div style={{ padding: "0 16px 16px", borderTop: "1px solid #1E1E22" }}>
          {(item.arbitration_reasoning || item.reasoning?.arbitration || item.reasoning?.coordinator) && (
            <div
              style={{
                margin: "12px 0",
                padding: "10px 12px",
                background: "#18181B",
                borderRadius: 8,
                borderLeft: `3px solid ${dimensionColor}`,
              }}
            >
              <p
                style={{
                  fontSize: 11,
                  color: "#5A5650",
                  margin: "0 0 6px",
                  fontFamily: "'JetBrains Mono', monospace",
                }}
              >
                ARBITRATION
              </p>
              <p style={{ fontSize: 13, color: "#C8C6C0", margin: 0, lineHeight: 1.55 }}>
                {item.arbitration_reasoning ||
                  item.reasoning?.arbitration ||
                  item.reasoning?.coordinator}
              </p>
            </div>
          )}
          <p style={{ fontSize: 11, color: "#5A5650", margin: "12px 0 8px", fontFamily: "'JetBrains Mono', monospace" }}>
            REASONING
          </p>
          {Object.entries(item.reasoning || {}).map(([k, v]) =>
            v && k !== "arbitration" && k !== "coordinator" ? (
              <p key={k} style={{ fontSize: 12, color: "#8A8680", marginBottom: 6 }}>
                <strong style={{ color: "#E8E6E1" }}>{k.replace(/_/g, " ")}:</strong> {v}
              </p>
            ) : null
          )}
          <p style={{ fontSize: 11, color: "#5A5650", margin: "14px 0 8px", fontFamily: "'JetBrains Mono', monospace" }}>
            FLAGS
          </p>
          {["virtue", "deficit_vice", "excess_vice"].map((cls) => (
            <div key={cls} style={{ marginBottom: 10 }}>
              <span style={{ fontSize: 11, color: dimensionColor, fontWeight: 600 }}>{clsLabel[cls]}</span>
              <FlagsBlock flags={item.flags?.[cls]} />
            </div>
          ))}
          <p style={{ fontSize: 11, color: "#5A5650", margin: "14px 0 8px", fontFamily: "'JetBrains Mono', monospace" }}>
            EVIDENCE
          </p>
          {["virtue", "deficit_vice", "excess_vice"].map((cls) => (
            <div key={cls} style={{ marginBottom: 12 }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: "#8A8680" }}>
                {clsLabel[cls]}
                {item.evidence_strength?.[cls] != null && (
                  <span
                    style={{
                      marginLeft: 8,
                      fontWeight: 400,
                      fontFamily: "'JetBrains Mono', monospace",
                      color: "#5A5650",
                    }}
                  >
                    strength {Number(item.evidence_strength[cls]).toFixed(1)}
                  </span>
                )}
              </span>
              <EvidenceList
                items={item.evidence?.[cls]}
                color={cls === "virtue" ? dimensionColor : cls === "deficit_vice" ? "#EF4444" : "#F59E0B"}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ItemDetailPanel({
  dimensionName,
  dimensionColor,
  items,
  loading,
  source,
  onSourceChange,
  showSourceToggle,
}) {
  if (!dimensionName) {
    return (
      <div
        style={{
          background: "#141416",
          borderRadius: 14,
          padding: 36,
          border: "1px solid #1E1E22",
          textAlign: "center",
          minHeight: 240,
        }}
      >
        <p style={{ color: "#5A5650" }}>Select a dimension on the wheel to explore items</p>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
        <h2 style={{ fontSize: 22, color: dimensionColor, fontFamily: "'Cormorant Garamond', serif" }}>
          {dimensionName} — Items
        </h2>
        {showSourceToggle && (
          <div style={{ display: "flex", gap: 4, background: "#18181B", borderRadius: 8, padding: 4 }}>
            {["baseline", "refined"].map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => onSourceChange(s)}
                style={{
                  padding: "6px 12px",
                  borderRadius: 6,
                  border: "none",
                  cursor: "pointer",
                  fontSize: 10,
                  fontFamily: "'JetBrains Mono', monospace",
                  background: source === s ? "#2A2A30" : "transparent",
                  color: source === s ? "#E8E6E1" : "#5A5650",
                }}
              >
                {s === "baseline" ? "Initial" : "Refined"}
              </button>
            ))}
          </div>
        )}
      </div>
      {loading ? (
        <p style={{ color: "#8A8680" }}>Loading items…</p>
      ) : (
        items?.map((item) => <ItemCard key={item.virtue} item={item} dimensionColor={dimensionColor} />)
      )}
    </div>
  );
}
