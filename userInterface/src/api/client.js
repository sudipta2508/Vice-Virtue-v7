const API_BASE = "/api";

export async function createSession() {
  const res = await fetch(`${API_BASE}/sessions`, { method: "POST" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getSession(sessionId) {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function sendMessage(sessionId, content) {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getResults(sessionId) {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/results`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getDimensionItems(sessionId, dimension, source = "refined") {
  const res = await fetch(
    `${API_BASE}/sessions/${sessionId}/dimensions/${encodeURIComponent(dimension)}/items?source=${source}`
  );
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getCatalog() {
  const res = await fetch(`${API_BASE}/catalog`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

const REPORT_FILENAMES = {
  baseline: { json: "vice_virtue_baseline.json", pdf: "vice_virtue_baseline.pdf" },
  refined: { json: "vice_virtue_refined.json", pdf: "vice_virtue_refined.pdf" },
};

export async function downloadReport(sessionId, reportType, format) {
  const res = await fetch(
    `${API_BASE}/sessions/${sessionId}/reports/${reportType}/${format}`
  );
  if (!res.ok) throw new Error(await res.text());
  const blob = await res.blob();
  const disp = res.headers.get("Content-Disposition") || "";
  const match = /filename="?([^";]+)"?/.exec(disp);
  const filename =
    match?.[1] || REPORT_FILENAMES[reportType]?.[format] || `report.${format}`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function pollSession(sessionId, onUpdate, intervalMs = 2500) {
  let active = true;
  const tick = async () => {
    if (!active) return;
    try {
      const data = await getSession(sessionId);
      onUpdate(data);
    } catch (_) {
      /* ignore transient errors */
    }
    if (active) setTimeout(tick, intervalMs);
  };
  tick();
  return () => {
    active = false;
  };
}
