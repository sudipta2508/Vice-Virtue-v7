import { useState, useEffect } from "react";

const ZONE_WIDTH = 100 / 3;
/** Inset within each zone so markers don't sit on zone boundaries (percent of full bar). */
const ZONE_INSET = 4;

function hasScore(score) {
  return score != null && score !== "" && !Number.isNaN(Number(score));
}

function clampScore(score) {
  if (!hasScore(score)) return 0;
  const s = Number(score);
  return Math.max(0, Math.min(5, s));
}

/** Map 0–5 score to horizontal % within zone z (0=deficit, 1=virtue, 2=excess). */
function zonePosition(score, zoneIndex) {
  const zoneStart = zoneIndex * ZONE_WIDTH;
  const innerWidth = ZONE_WIDTH - 2 * ZONE_INSET;
  return zoneStart + ZONE_INSET + (clampScore(score) / 5) * innerWidth;
}

function formatScore(score) {
  if (!hasScore(score)) return "-";
  const s = clampScore(score);
  return s === Math.floor(s) ? String(Math.floor(s)) : s.toFixed(1);
}

function Marker({ pos, anim, color, letter, size, score, scoreColor, scoreBelow }) {
  return (
    <div
      style={{
        position: "absolute",
        left: `${anim ? pos : 0}%`,
        top: "50%",
        transform: "translate(-50%, -50%)",
        zIndex: 5,
        transition: "left 1.2s cubic-bezier(0.22, 1, 0.36, 1)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
      }}
    >
      {!scoreBelow && (
        <span
          style={{
            position: "absolute",
            bottom: "100%",
            marginBottom: 6,
            fontSize: 10,
            fontWeight: 700,
            color: scoreColor,
            fontFamily: "'JetBrains Mono', monospace",
            whiteSpace: "nowrap",
            lineHeight: 1,
          }}
        >
          {formatScore(score)}
        </span>
      )}
      <div
        style={{
          width: size,
          height: size,
          borderRadius: "50%",
          background: color,
          border: "2px solid #18181B",
          boxShadow: `0 0 8px ${color}60`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
        }}
      >
        <span style={{ fontSize: size > 20 ? 9 : 7, color: "#fff", fontWeight: 700 }}>{letter}</span>
      </div>
      {scoreBelow && (
        <span
          style={{
            position: "absolute",
            top: "100%",
            marginTop: 5,
            fontSize: 10,
            fontWeight: 700,
            color: scoreColor,
            fontFamily: "'JetBrains Mono', monospace",
            whiteSpace: "nowrap",
            lineHeight: 1,
          }}
        >
          {formatScore(score)}
        </span>
      )}
    </div>
  );
}

export default function SpectrumGauge({ dim, compact = false }) {
  const [anim, setAnim] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setAnim(true), 80);
    return () => clearTimeout(t);
  }, [dim?.name]);

  if (!dim) return null;

  const deficitPos = zonePosition(dim.deficit?.score, 0);
  const virtuePos = zonePosition(dim.virtue?.score, 1);
  const excessPos = zonePosition(dim.excess?.score, 2);
  const trackH = compact ? 28 : 40;
  const padTop = compact ? 4 : 8;
  const padBottom = compact ? 4 : 22;

  return (
    <div style={{ width: "100%", marginBottom: compact ? 0 : 16 }}>
      {!compact && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr 1fr",
            gap: 8,
            marginBottom: 10,
            alignItems: "end",
          }}
        >
          <span
            style={{
              fontSize: 10,
              color: "#EF4444",
              fontFamily: "'Cormorant Garamond', serif",
              fontStyle: "italic",
              fontWeight: 600,
              textAlign: "left",
              lineHeight: 1.3,
              paddingRight: 4,
            }}
          >
            {dim.deficit?.name}
          </span>
          <span
            style={{
              fontSize: 13,
              color: dim.color,
              fontFamily: "'Cormorant Garamond', serif",
              fontWeight: 700,
              textAlign: "center",
              lineHeight: 1.3,
            }}
          >
            {dim.name}
          </span>
          <span
            style={{
              fontSize: 10,
              color: "#F59E0B",
              fontFamily: "'Cormorant Garamond', serif",
              fontStyle: "italic",
              fontWeight: 600,
              textAlign: "right",
              lineHeight: 1.3,
              paddingLeft: 4,
            }}
          >
            {dim.excess?.name}
          </span>
        </div>
      )}

      <div
        style={{
          position: "relative",
          paddingTop: padTop,
          paddingBottom: padBottom,
          overflow: "visible",
        }}
      >
        <div
          style={{
            position: "relative",
            height: trackH,
            width: "100%",
            borderRadius: trackH / 2,
            overflow: "visible",
          }}
        >
          <div
            style={{
              position: "absolute",
              inset: 0,
              borderRadius: trackH / 2,
              overflow: "hidden",
              background: "#18181B",
              border: "1px solid #2A2A30",
            }}
          >
            <div
              style={{
                position: "absolute",
                inset: 0,
                background: `linear-gradient(90deg, 
                  #EF444412 0%, #EF444406 18%, 
                  ${dim.color}12 33%, ${dim.color}22 50%, ${dim.color}12 67%, 
                  #F59E0B06 82%, #F59E0B12 100%)`,
              }}
            />
            <div
              style={{
                position: "absolute",
                top: 0,
                bottom: 0,
                left: `${ZONE_WIDTH}%`,
                width: 1,
                background: "#2A2A30",
                opacity: 0.8,
              }}
            />
            <div
              style={{
                position: "absolute",
                top: 0,
                bottom: 0,
                left: `${ZONE_WIDTH * 2}%`,
                width: 1,
                background: "#2A2A30",
                opacity: 0.8,
              }}
            />
          </div>

          <Marker
            pos={deficitPos}
            anim={anim}
            color="#EF4444"
            letter="D"
            size={compact ? 14 : 18}
            score={dim.deficit?.score}
            scoreColor="#EF4444"
            scoreBelow={!compact}
          />
          <Marker
            pos={virtuePos}
            anim={anim}
            color={dim.color}
            letter="V"
            size={compact ? 18 : 22}
            score={dim.virtue?.score}
            scoreColor={dim.color}
            scoreBelow={!compact}
          />
          <Marker
            pos={excessPos}
            anim={anim}
            color="#F59E0B"
            letter="E"
            size={compact ? 14 : 18}
            score={dim.excess?.score}
            scoreColor="#F59E0B"
            scoreBelow={!compact}
          />
        </div>

        {!compact && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr",
              marginTop: 6,
              pointerEvents: "none",
            }}
          >
            <span
              style={{
                fontSize: 8,
                color: "#EF444440",
                fontFamily: "'JetBrains Mono', monospace",
                letterSpacing: 0.5,
                textAlign: "center",
              }}
            >
              DEFICIT
            </span>
            <span
              style={{
                fontSize: 8,
                color: `${dim.color}50`,
                fontFamily: "'JetBrains Mono', monospace",
                letterSpacing: 0.5,
                textAlign: "center",
              }}
            >
              VIRTUE
            </span>
            <span
              style={{
                fontSize: 8,
                color: "#F59E0B40",
                fontFamily: "'JetBrains Mono', monospace",
                letterSpacing: 0.5,
                textAlign: "center",
              }}
            >
              EXCESS
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
