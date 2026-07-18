export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

/**
 * Exchange the demo staff passcode for a signed JWT so the staff dashboard's
 * protected endpoints (alerts, copilot, chat) work. The landing-page login uses
 * a simple test/test gate for UX; this obtains the real token behind it.
 */
export async function staffLogin() {
  const passcode = import.meta.env.VITE_STAFF_PASSCODE || "fifa2026";
  const res = await fetch(`${API_BASE}/api/v1/auth/staff/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ passcode }),
  });
  if (!res.ok) {
    throw new Error("Staff authentication failed");
  }
  const data = await res.json();
  return data.token;
}

/**
 * A random id scoped to this browser tab session — not tied to any name, email,
 * or other personal identifier — used only to group anonymized interaction events.
 */
function getSessionId() {
  let id = sessionStorage.getItem("ekta_session_id");
  if (!id) {
    id = (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`);
    sessionStorage.setItem("ekta_session_id", id);
  }
  return id;
}

/**
 * Fire-and-forget anonymized interaction logging (login/logout/page views/chat
 * message counts) so staff can see what data the app collects. Never sends raw
 * message text or personal fields, and never blocks or throws for the caller.
 */
export function logInteraction(role, eventType, view, meta) {
  fetch(`${API_BASE}/api/v1/interactions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: getSessionId(), role, event_type: eventType, view, meta: meta || {} }),
  }).catch(() => {});
}
