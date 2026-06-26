// ══════════════════════════════════════════
//  ARIA — API Client
//  All calls to FastAPI backend
// ══════════════════════════════════════════

const API_BASE = 'http://localhost:8000';

const Api = {

  // ── Health ──────────────────────────────
  async health() {
    const r = await fetch(`${API_BASE}/health`);
    return r.json();
  },

  // ── Chat ────────────────────────────────
  async chat(payload) {
    const r = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },

  // ── Research ────────────────────────────
  async startResearch(topic, depth, sessionId) {
    const r = await fetch(`${API_BASE}/api/research/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic, depth, session_id: sessionId }),
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  },

  async getHistory() {
    const r = await fetch(`${API_BASE}/api/research/history`);
    return r.json();
  },

  // ── Memory ──────────────────────────────
  async getShortTermMemory(sessionId) {
    const r = await fetch(`${API_BASE}/api/memory/short-term/${sessionId}`);
    return r.json();
  },

  async getLongTermMemory() {
    const r = await fetch(`${API_BASE}/api/memory/long-term`);
    return r.json();
  },

  async clearLongTermMemory() {
    const r = await fetch(`${API_BASE}/api/memory/long-term`, { method: 'DELETE' });
    return r.json();
  },

  // ── Vector DB ───────────────────────────
  async getVectorStats() {
    const r = await fetch(`${API_BASE}/api/vectordb/stats`);
    return r.json();
  },

  async getDocuments() {
    const r = await fetch(`${API_BASE}/api/vectordb/documents`);
    return r.json();
  },

  async vectorSearch(query, topK = 5) {
    const r = await fetch(`${API_BASE}/api/vectordb/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, top_k: topK }),
    });
    return r.json();
  },

  // ── Agents ──────────────────────────────
  async getAgentLogs() {
    const r = await fetch(`${API_BASE}/api/agents/logs`);
    return r.json();
  },
};
