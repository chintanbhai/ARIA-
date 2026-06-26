// ══════════════════════════════════════════
//  ARIA — Main Application Logic
// ══════════════════════════════════════════

// ── State ───────────────────────────────
const state = {
  sessionId: generateSessionId(),
  messages: [],
  isLoading: false,
  agentLogs: [],
  backendOnline: false,
};

// ── Init ────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('sessionId').textContent = state.sessionId.slice(0, 8) + '...';
  checkBackend();
  setInterval(checkBackend, 10000);

  // sidebar toggle
  document.getElementById('sidebarToggle').addEventListener('click', toggleSidebar);

  // auto-resize textarea on load
  const inp = document.getElementById('chatInput');
  inp.addEventListener('input', () => autoResize(inp));
});

async function checkBackend() {
  try {
    await Api.health();
    setBackendStatus(true);
  } catch {
    setBackendStatus(false);
  }
}

function setBackendStatus(online) {
  state.backendOnline = online;
  const dot = document.getElementById('backendStatus');
  const lbl = document.getElementById('backendLabel');
  dot.className = 'status-dot ' + (online ? 'online' : 'offline');
  lbl.textContent = online ? 'Backend online' : 'Backend offline';
}

// ── Sidebar ─────────────────────────────
function toggleSidebar() {
  const sb = document.getElementById('sidebar');
  const main = document.getElementById('main');
  const btn = document.getElementById('sidebarToggle');
  const collapsed = sb.classList.toggle('collapsed');
  main.classList.toggle('sidebar-collapsed', collapsed);
  btn.textContent = collapsed ? '⟩' : '⟨';
}

// ── View switching ───────────────────────
function switchView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('view-' + name).classList.add('active');
  document.querySelector(`[data-view="${name}"]`).classList.add('active');

  // lazy-load data for each view
  if (name === 'history') loadHistory();
  if (name === 'memory') loadMemory();
  if (name === 'vectordb') loadVectorStats();
  if (name === 'agents') loadAgentLogs();
}

// ── Chat ─────────────────────────────────
function handleInputKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 160) + 'px';
}

async function sendMessage() {
  const input = document.getElementById('chatInput');
  const text = input.value.trim();
  if (!text || state.isLoading) return;

  if (!state.backendOnline) {
    showToast('Backend is offline. Start the FastAPI server first.', 'error');
    return;
  }

  input.value = '';
  autoResize(input);
  appendMessage('user', text);

  setLoading(true);
  showPipeline();

  try {
    const webSearch = document.getElementById('webSearch').checked;
    const useRag = document.getElementById('useRag').checked;

    const response = await Api.chat({
      message: text,
      session_id: state.sessionId,
      use_web_search: webSearch,
      use_rag: useRag,
    });

    hidePipeline();
    appendAssistantMessage(response);
    appendLog('orchestrator', 'Response delivered to user');

  } catch (err) {
    hidePipeline();
    appendMessage('assistant', '⚠ Error: ' + err.message + '\n\nMake sure the backend is running on port 8000.');
  } finally {
    setLoading(false);
  }
}

function sendSuggestion(text) {
  document.getElementById('chatInput').value = text;
  sendMessage();
}

function appendMessage(role, text) {
  // Hide welcome state
  const ws = document.getElementById('welcomeState');
  if (ws) ws.remove();

  const msgs = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = 'message ' + role;

  const avatar = role === 'user' ? '◇' : '◈';
  const roleLabel = role === 'user' ? 'You' : 'ARIA';

  div.innerHTML = `
    <div class="message-avatar">${avatar}</div>
    <div class="message-body">
      <div class="message-role">${roleLabel}</div>
      <div class="message-bubble">${formatText(text)}</div>
    </div>`;

  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
  state.messages.push({ role, content: text });
  return div;
}

function appendAssistantMessage(response) {
  const msgs = document.getElementById('messages');
  const div = document.createElement('div');
  div.className = 'message assistant';

  const citationsHtml = buildCitationsHtml(response.citations);
  const traceHtml = buildTraceHtml(response.agent_trace);

  div.innerHTML = `
    <div class="message-avatar">◈</div>
    <div class="message-body">
      <div class="message-role">ARIA</div>
      <div class="message-bubble">
        ${formatText(response.answer)}
        ${citationsHtml}
        ${traceHtml}
      </div>
    </div>`;

  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
  state.messages.push({ role: 'assistant', content: response.answer });
}

function buildCitationsHtml(citations) {
  if (!citations || citations.length === 0) return '';
  const items = citations.map((c, i) => `
    <div class="citation-item">
      <span class="citation-num">[${i + 1}]</span>
      <span>${c.title ? `<a href="${c.url}" target="_blank">${c.title}</a>` : `<a href="${c.url}" target="_blank">${c.url}</a>`}</span>
    </div>`).join('');
  return `<div class="citations"><div class="citations-label">Sources</div><div class="citation-list">${items}</div></div>`;
}

function buildTraceHtml(trace) {
  if (!trace || trace.length === 0) return '';
  const lines = trace.map(t => `<div>• [${t.agent}] ${t.action}</div>`).join('');
  return `<div class="agent-trace">
    <button class="agent-trace-toggle" onclick="toggleTrace(this)">▶ Agent trace (${trace.length} steps)</button>
    <div class="agent-trace-body">${lines}</div>
  </div>`;
}

function toggleTrace(btn) {
  const body = btn.nextElementSibling;
  const open = body.classList.toggle('open');
  btn.textContent = (open ? '▼' : '▶') + btn.textContent.slice(1);
}

function showTyping() {
  const ws = document.getElementById('welcomeState');
  if (ws) ws.remove();
  const msgs = document.getElementById('messages');
  const div = document.createElement('div');
  div.id = 'typingIndicator';
  div.className = 'message assistant';
  div.innerHTML = `
    <div class="message-avatar">◈</div>
    <div class="message-body">
      <div class="message-role">ARIA</div>
      <div class="message-bubble">
        <div class="typing-indicator">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
      </div>
    </div>`;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

function removeTyping() {
  const t = document.getElementById('typingIndicator');
  if (t) t.remove();
}

function setLoading(loading) {
  state.isLoading = loading;
  const btn = document.getElementById('sendBtn');
  btn.disabled = loading;
  if (loading) showTyping(); else removeTyping();
}

function clearChat() {
  state.messages = [];
  state.sessionId = generateSessionId();
  document.getElementById('sessionId').textContent = state.sessionId.slice(0, 8) + '...';
  document.getElementById('messages').innerHTML = `
    <div class="welcome-state" id="welcomeState">
      <div class="welcome-icon">◈</div>
      <h2 class="welcome-title">Ready to Research</h2>
      <p class="welcome-text">Ask anything. ARIA will orchestrate multiple agents to research, retrieve, and synthesise an answer with citations.</p>
      <div class="suggestion-chips">
        <button class="chip" onclick="sendSuggestion('What are the latest breakthroughs in quantum computing?')">Quantum computing breakthroughs</button>
        <button class="chip" onclick="sendSuggestion('Explain how large language models work')">How LLMs work</button>
        <button class="chip" onclick="sendSuggestion('What is retrieval-augmented generation?')">What is RAG?</button>
        <button class="chip" onclick="sendSuggestion('Compare transformer vs RNN architectures')">Transformers vs RNNs</button>
      </div>
    </div>`;
  showToast('Chat cleared', 'success');
}

// ── Pipeline bar ─────────────────────────
const PIPELINE_STEPS = ['orchestrator', 'researcher', 'retriever', 'writer'];
let pipelineInterval = null;
let pipelineIdx = 0;

function showPipeline() {
  const bar = document.getElementById('pipelineBar');
  bar.style.display = 'flex';
  PIPELINE_STEPS.forEach(s => {
    const el = document.getElementById('step-' + s);
    if (el) el.className = 'pipeline-step';
  });
  pipelineIdx = 0;
  activateStep(pipelineIdx);
  pipelineInterval = setInterval(() => {
    if (pipelineIdx < PIPELINE_STEPS.length - 1) {
      const el = document.getElementById('step-' + PIPELINE_STEPS[pipelineIdx]);
      if (el) el.className = 'pipeline-step done';
      pipelineIdx++;
      activateStep(pipelineIdx);
    }
  }, 1200);
}

function activateStep(idx) {
  const step = PIPELINE_STEPS[idx];
  const el = document.getElementById('step-' + step);
  if (el) el.className = 'pipeline-step active';
  // sync agent cards
  document.querySelectorAll('.agent-card').forEach(c => {
    c.classList.remove('active');
    const s = c.querySelector('.agent-status');
    if (s && s.classList.contains('running')) { s.className = 'agent-status done'; s.textContent = 'done'; }
  });
  const card = document.getElementById('agent-' + step);
  if (card) {
    card.classList.add('active');
    const s = card.querySelector('.agent-status');
    if (s) { s.className = 'agent-status running'; s.textContent = 'running'; }
  }
  appendLog(step, getStepLog(step));
}

function getStepLog(step) {
  const logs = {
    orchestrator: 'Planning research task and delegating to sub-agents...',
    researcher: 'Searching the web and gathering source documents...',
    retriever: 'Running semantic search over vector DB...',
    writer: 'Synthesising answer with citations...',
  };
  return logs[step] || 'Processing...';
}

function hidePipeline() {
  clearInterval(pipelineInterval);
  PIPELINE_STEPS.forEach(s => {
    const el = document.getElementById('step-' + s);
    if (el) el.className = 'pipeline-step done';
  });
  setTimeout(() => {
    document.getElementById('pipelineBar').style.display = 'none';
    PIPELINE_STEPS.forEach(s => {
      const el = document.getElementById('step-' + s);
      if (el) el.className = 'pipeline-step';
      const card = document.getElementById('agent-' + s);
      if (card) {
        card.classList.remove('active');
        const st = card.querySelector('.agent-status');
        if (st) { st.className = 'agent-status idle'; st.textContent = 'idle'; }
      }
    });
  }, 1500);
}

// ── Research Modal ────────────────────────
function openResearchModal() {
  document.getElementById('researchModal').classList.add('open');
  setTimeout(() => document.getElementById('researchTopic').focus(), 100);
}

function closeResearchModal(e) {
  if (e && e.target !== document.getElementById('researchModal')) return;
  document.getElementById('researchModal').classList.remove('open');
}

async function startResearch() {
  const topic = document.getElementById('researchTopic').value.trim();
  if (!topic) { showToast('Please enter a research topic', 'error'); return; }
  const depth = document.querySelector('input[name="depth"]:checked').value;

  closeResearchModal();
  switchView('chat');

  appendMessage('user', `🔬 Research request: "${topic}" (depth: ${depth})`);
  setLoading(true);
  showPipeline();

  try {
    const res = await Api.startResearch(topic, depth, state.sessionId);
    hidePipeline();
    appendAssistantMessage(res);
    showToast(`Research complete! ${res.sources_indexed || 0} sources indexed.`, 'success');
  } catch (err) {
    hidePipeline();
    appendMessage('assistant', '⚠ Research failed: ' + err.message);
    showToast('Research failed', 'error');
  } finally {
    setLoading(false);
  }
}

// ── History view ──────────────────────────
async function loadHistory() {
  const grid = document.getElementById('historyGrid');
  grid.innerHTML = '<div class="empty-state"><p class="muted">Loading...</p></div>';
  try {
    const data = await Api.getHistory();
    if (!data.sessions || data.sessions.length === 0) {
      grid.innerHTML = '<div class="empty-state"><p>No research sessions yet.</p><p class="muted">Start a conversation to build your knowledge base.</p></div>';
      return;
    }
    grid.innerHTML = data.sessions.map(s => `
      <div class="history-card" onclick="loadSession('${s.id}')">
        <div class="history-card-title">${escHtml(s.topic || s.id)}</div>
        <div class="history-card-meta">${formatDate(s.created_at)} · ${s.message_count || 0} messages</div>
        <div class="history-card-preview">${escHtml(s.preview || 'No preview available')}</div>
      </div>`).join('');
  } catch {
    grid.innerHTML = '<div class="empty-state"><p class="muted">Could not load history. Is the backend running?</p></div>';
  }
}

function loadSession(id) {
  showToast(`Loading session ${id.slice(0, 8)}...`);
  switchView('chat');
}

// ── Memory view ───────────────────────────
async function loadMemory() {
  // Short-term
  const stEl = document.getElementById('shortTermList');
  stEl.innerHTML = '<div class="empty-state"><p class="muted">Loading...</p></div>';
  try {
    const st = await Api.getShortTermMemory(state.sessionId);
    if (!st.messages || st.messages.length === 0) {
      stEl.innerHTML = '<div class="empty-state"><p class="muted">No messages in current session</p></div>';
    } else {
      stEl.innerHTML = st.messages.map(m => `
        <div class="memory-item">
          <div class="memory-item-label">${m.role}</div>
          ${escHtml(m.content.slice(0, 120))}${m.content.length > 120 ? '...' : ''}
        </div>`).join('');
    }
  } catch {
    stEl.innerHTML = '<div class="empty-state"><p class="muted">No active session</p></div>';
  }

  // Long-term
  const ltEl = document.getElementById('longTermList');
  ltEl.innerHTML = '<div class="empty-state"><p class="muted">Loading...</p></div>';
  try {
    const lt = await Api.getLongTermMemory();
    if (!lt.memories || lt.memories.length === 0) {
      ltEl.innerHTML = '<div class="empty-state"><p class="muted">No long-term memories yet</p></div>';
    } else {
      ltEl.innerHTML = lt.memories.map(m => `
        <div class="memory-item">
          <div class="memory-item-label">${m.type || 'fact'} · ${formatDate(m.created_at)}</div>
          ${escHtml(m.content)}
        </div>`).join('');
    }
  } catch {
    ltEl.innerHTML = '<div class="empty-state"><p class="muted">Could not load long-term memory</p></div>';
  }
}

async function clearLongTermMemory() {
  if (!confirm('Clear all long-term memories? This cannot be undone.')) return;
  try {
    await Api.clearLongTermMemory();
    showToast('Long-term memory cleared', 'success');
    loadMemory();
  } catch {
    showToast('Failed to clear memory', 'error');
  }
}

// ── Vector DB view ────────────────────────
async function loadVectorStats() {
  try {
    const stats = await Api.getVectorStats();
    document.getElementById('statDocs').textContent = stats.total_documents ?? '0';
    document.getElementById('statChunks').textContent = stats.total_chunks ?? '0';
    document.getElementById('statTopics').textContent = stats.unique_topics ?? '0';
  } catch {
    ['statDocs', 'statChunks', 'statTopics'].forEach(id => document.getElementById(id).textContent = '—');
  }

  const docsList = document.getElementById('docsList');
  try {
    const data = await Api.getDocuments();
    if (!data.documents || data.documents.length === 0) {
      docsList.innerHTML = '<div class="empty-state"><p class="muted">No documents indexed yet</p></div>';
    } else {
      docsList.innerHTML = data.documents.map(d => `
        <div class="doc-item">
          <div class="doc-info">
            <div class="doc-title">${escHtml(d.title || 'Untitled')}</div>
            <div class="doc-meta">${escHtml(d.source || '')} · ${formatDate(d.created_at)}</div>
          </div>
          <div class="doc-chunks">${d.chunks} chunks</div>
        </div>`).join('');
    }
  } catch {
    docsList.innerHTML = '<div class="empty-state"><p class="muted">Could not load documents</p></div>';
  }
}

async function testVectorSearch() {
  const query = document.getElementById('vectorSearchInput').value.trim();
  if (!query) { showToast('Enter a search query', 'error'); return; }
  const resultsEl = document.getElementById('searchResults');
  resultsEl.innerHTML = '<div class="empty-state"><p class="muted">Searching...</p></div>';
  try {
    const data = await Api.vectorSearch(query);
    if (!data.results || data.results.length === 0) {
      resultsEl.innerHTML = '<div class="empty-state"><p class="muted">No results found</p></div>';
      return;
    }
    resultsEl.innerHTML = data.results.map(r => `
      <div class="search-result-item">
        <div class="result-score">Score: ${(r.score * 100).toFixed(1)}%</div>
        <div class="result-text">${escHtml(r.text)}</div>
        <div class="result-source">${escHtml(r.source || 'Unknown source')}</div>
      </div>`).join('');
  } catch {
    resultsEl.innerHTML = '<div class="empty-state"><p class="muted">Search failed. Is backend running?</p></div>';
  }
}

// ── Agent logs view ───────────────────────
async function loadAgentLogs() {
  const box = document.getElementById('agentLogs');
  if (state.agentLogs.length === 0) {
    box.innerHTML = '<p class="muted mono">Waiting for agent activity...</p>';
    return;
  }
  box.innerHTML = state.agentLogs.map(l => `
    <div class="log-line">
      <span class="log-time">${l.time}</span>
      <span class="log-agent ${l.agent}">[${l.agent.toUpperCase()}]</span>
      <span class="log-msg">${escHtml(l.msg)}</span>
    </div>`).join('');
  box.scrollTop = box.scrollHeight;
}

function appendLog(agent, msg) {
  const now = new Date();
  const time = now.toTimeString().slice(0, 8);
  state.agentLogs.push({ time, agent, msg });
  if (state.agentLogs.length > 200) state.agentLogs.shift();
  // update live if on agents view
  const agentsView = document.getElementById('view-agents');
  if (agentsView.classList.contains('active')) loadAgentLogs();
}

// ── Utilities ─────────────────────────────
function generateSessionId() {
  return 'sess_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 7);
}

function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatText(text) {
  if (!text) return '';
  return escHtml(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/###\s(.+)/g, '<h3>$1</h3>')
    .replace(/##\s(.+)/g, '<h3>$1</h3>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>')
    .replace(/^/, '<p>')
    .replace(/$/, '</p>');
}

function formatDate(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
  } catch { return iso; }
}

let toastTimer;
function showToast(msg, type = '') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show ' + type;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.className = 'toast'; }, 3000);
}
