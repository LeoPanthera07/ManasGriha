/* ══════════════════════════════════════════════════════════
   ManasGriha — Main Application
   Supports: Group chat (The Council) + Individual 1-on-1 chats
   ══════════════════════════════════════════════════════════ */

// ── State ───────────────────────────────────────────────
const state = {
  apiKey: localStorage.getItem('manasgriha_api_key') || '',
  // Chat mode: 'group' or a persona key like 'marcus_aurelius'
  chatMode: localStorage.getItem('manasgriha_chat_mode') || 'group',
  // Session IDs per chat (group has one, each persona has one)
  sessions: JSON.parse(localStorage.getItem('manasgriha_sessions') || '{}'),
  personas: [],
  messages: [],
  replyTo: null,
  isLoading: false,
  abortController: null,
};

// ── DOM refs ────────────────────────────────────────────
const $ = (s) => document.querySelector(s);
const dom = {
  personaList:       $('#persona-list'),
  welcomePersonas:   $('#welcome-personas'),
  welcomeScreen:     $('#welcome-screen'),
  messagesContainer: $('#messages-container'),
  messageInput:      $('#message-input'),
  btnSend:           $('#btn-send'),
  btnMenu:           $('#btn-menu'),
  sidebar:           $('#sidebar'),
  btnSettings:       $('#btn-settings'),
  btnNewChat:        $('#btn-new-chat'),
  btnGroupChat:      $('#btn-group-chat'),
  modalOverlay:      $('#modal-overlay'),
  apiKeyInput:       $('#api-key-input'),
  modalError:        $('#modal-error'),
  btnModalSave:      $('#btn-modal-save'),
  btnModalCancel:    $('#btn-modal-cancel'),
  keyDot:            $('#key-dot'),
  keyLabel:          $('#key-label'),
  chatTitle:         $('#chat-title'),
  chatSubtitle:      $('#chat-subtitle'),
  chatHeaderAvatar:  $('#chat-header-avatar'),
  replyPreview:      $('#reply-preview'),
  replyAuthor:       $('#reply-author'),
  replyText:         $('#reply-text'),
  btnCloseReply:     $('#btn-close-reply'),
  toast:             $('#toast'),
};

const API = '/api';

// ── Init ────────────────────────────────────────────────
async function init() {
  await loadPersonas();
  updateKeyStatus();
  if (!state.apiKey) showModal();
  switchChat(state.chatMode, false);
  bindEvents();
}

// ── Personas ────────────────────────────────────────────
async function loadPersonas() {
  try {
    const res = await fetch(`${API}/personas`);
    state.personas = await res.json();
    renderPersonaList();
  } catch (e) {
    console.error('Failed to load personas:', e);
  }
}

function renderPersonaList() {
  dom.personaList.innerHTML = state.personas.map(p => `
    <div class="persona-item" data-mode="individual" data-key="${p.key}">
      <div class="persona-avatar" style="background:${p.color}20">${p.avatar}</div>
      <div class="persona-info">
        <div class="persona-name" style="color:${p.color}">${p.name}</div>
        <div class="persona-tagline">${p.tagline}</div>
      </div>
    </div>
  `).join('');

  if (dom.welcomePersonas) {
    dom.welcomePersonas.innerHTML = state.personas.map(p =>
      `<span>${p.avatar} ${p.name}</span>`
    ).join('');
  }
}

function getPersona(key) {
  return state.personas.find(p => p.key === key);
}

// ── Chat mode switching ─────────────────────────────────
function switchChat(mode, loadHist = true) {
  state.chatMode = mode;
  state.messages = [];
  state.replyTo = null;
  state.isLoading = false;
  localStorage.setItem('manasgriha_chat_mode', mode);
  clearReply();

  // Cancel any in-flight request
  if (state.abortController) {
    state.abortController.abort();
    state.abortController = null;
  }
  removeTypingIndicator();

  // Update sidebar active state
  document.querySelectorAll('.persona-item').forEach(el => el.classList.remove('active'));
  if (mode === 'group') {
    dom.btnGroupChat.classList.add('active');
  } else {
    const el = document.querySelector(`.persona-item[data-key="${mode}"]`);
    if (el) el.classList.add('active');
  }

  // Update header
  updateChatHeader();

  // Update input placeholder
  if (mode === 'group') {
    dom.messageInput.placeholder = 'Message the council...';
  } else {
    const p = getPersona(mode);
    dom.messageInput.placeholder = p ? `Message ${p.name}...` : 'Type a message...';
  }

  // Load history
  if (loadHist) {
    loadHistory();
  } else {
    renderAllMessages();
  }

  // Close mobile sidebar
  dom.sidebar.classList.remove('open');
}

function updateChatHeader() {
  if (state.chatMode === 'group') {
    dom.chatTitle.textContent = 'The Council';
    dom.chatSubtitle.textContent = `${state.personas.length} personas online`;
    dom.chatHeaderAvatar.textContent = '🏛️';
    dom.chatHeaderAvatar.style.background = 'rgba(124,92,252,0.15)';
  } else {
    const p = getPersona(state.chatMode);
    if (p) {
      dom.chatTitle.textContent = p.name;
      dom.chatSubtitle.textContent = p.tagline;
      dom.chatHeaderAvatar.textContent = p.avatar;
      dom.chatHeaderAvatar.style.background = p.color + '20';
    }
  }
}

// ── Session management ──────────────────────────────────
function getSessionId() {
  return state.sessions[state.chatMode] || '';
}

function setSessionId(id) {
  state.sessions[state.chatMode] = id;
  localStorage.setItem('manasgriha_sessions', JSON.stringify(state.sessions));
}

function clearSessionId() {
  delete state.sessions[state.chatMode];
  localStorage.setItem('manasgriha_sessions', JSON.stringify(state.sessions));
}

// ── Key management ──────────────────────────────────────
function updateKeyStatus() {
  if (state.apiKey) {
    dom.keyDot.className = 'key-status-dot connected';
    dom.keyLabel.textContent = 'Key: ••••' + state.apiKey.slice(-4);
  } else {
    dom.keyDot.className = 'key-status-dot disconnected';
    dom.keyLabel.textContent = 'No API key set';
  }
}

function showModal() {
  dom.modalOverlay.classList.add('active');
  dom.apiKeyInput.value = state.apiKey;
  dom.modalError.classList.remove('visible');
  setTimeout(() => dom.apiKeyInput.focus(), 200);
}

function hideModal() {
  dom.modalOverlay.classList.remove('active');
}

function saveKey() {
  const key = dom.apiKeyInput.value.trim();
  if (!key || key.length < 10) {
    dom.modalError.classList.add('visible');
    return;
  }
  state.apiKey = key;
  localStorage.setItem('manasgriha_api_key', key);
  updateKeyStatus();
  hideModal();
  showToast('API key saved ✓');
}

// ── Load history ────────────────────────────────────────
async function loadHistory() {
  const sessionId = getSessionId();
  if (!sessionId) {
    state.messages = [];
    renderAllMessages();
    return;
  }
  try {
    const endpoint = state.chatMode === 'group'
      ? `${API}/group-history/${sessionId}`
      : `${API}/history/${sessionId}`;
    const res = await fetch(endpoint);
    if (!res.ok) {
      clearSessionId();
      state.messages = [];
      renderAllMessages();
      return;
    }
    const data = await res.json();

    if (state.chatMode === 'group') {
      state.messages = data.messages || [];
    } else {
      // Individual chat history: transform to our message format
      const p = getPersona(state.chatMode);
      state.messages = (data.messages || []).map(m => ({
        id: m.id || Date.now() + Math.random(),
        role: m.role,
        content: m.content,
        timestamp: m.timestamp,
        ...(m.role === 'assistant' && p ? {
          persona_key: state.chatMode,
          persona_name: p.name,
          avatar: p.avatar,
          color: p.color,
        } : {}),
      }));
    }
    renderAllMessages();
  } catch (e) {
    console.error('Failed to load history:', e);
    state.messages = [];
    renderAllMessages();
  }
}

// ── Send message ────────────────────────────────────────
async function sendMessage() {
  const text = dom.messageInput.value.trim();
  if (!text || state.isLoading) return;
  if (!state.apiKey) { showModal(); return; }

  state.isLoading = true;
  dom.messageInput.value = '';
  autoResizeInput();
  updateSendButton();

  // Add user message to UI
  const userMsg = {
    id: Date.now(),
    role: 'user',
    content: text,
    reply_to_id: state.replyTo?.id || null,
    _reply_to_name: state.replyTo?.persona_name || null,
    _reply_to_content: state.replyTo?.content || null,
  };
  state.messages.push(userMsg);
  renderMessage(userMsg);
  hideWelcome();
  clearReply();
  scrollToBottom();

  if (state.chatMode === 'group') {
    await sendGroupMessage(text, userMsg);
  } else {
    await sendIndividualMessage(text, userMsg);
  }

  state.isLoading = false;
  state.abortController = null;
  removeTypingIndicator();
  updateChatHeader();
}

// ── Group chat (SSE) ────────────────────────────────────
async function sendGroupMessage(text, userMsg) {
  const body = {
    message: text,
    session_id: getSessionId() || undefined,
    reply_to_id: userMsg.reply_to_id || undefined,
  };

  try {
    state.abortController = new AbortController();
    const res = await fetch(`${API}/group-chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-API-Key': state.apiKey },
      body: JSON.stringify(body),
      signal: state.abortController.signal,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      let eventType = '';
      for (const line of lines) {
        if (line.startsWith('event:')) {
          eventType = line.slice(6).trim();
        } else if (line.startsWith('data:')) {
          const dataStr = line.slice(5).trim();
          if (!dataStr) continue;
          try {
            handleSSEEvent(eventType, JSON.parse(dataStr));
          } catch (e) { console.warn('SSE parse error:', e); }
          eventType = '';
        }
      }
    }
    removeTypingIndicator();
  } catch (e) {
    if (e.name !== 'AbortError') {
      console.error('Group chat error:', e);
      showToast(e.message || 'Something went wrong', true);
    }
  }
}

function handleSSEEvent(eventType, data) {
  if (eventType === 'session') {
    setSessionId(data.session_id);
    return;
  }
  if (eventType === 'persona_reply' || eventType === 'debate_reply') {
    removeTypingIndicator();
    const msg = {
      id: data.message_id,
      role: 'assistant',
      persona_key: data.persona_key,
      persona_name: data.persona_name,
      avatar: data.avatar,
      color: data.color,
      content: data.reply,
      reply_to_key: data.reply_to_key || null,
      reply_to_name: data.reply_to_name || null,
    };
    state.messages.push(msg);
    renderMessage(msg);
    scrollToBottom();
    showTypingIndicator();
    dom.chatSubtitle.textContent = `${data.persona_name} responded`;
    return;
  }
  if (eventType === 'done') {
    removeTypingIndicator();
    dom.chatSubtitle.textContent = `${state.personas.length} personas online`;
    return;
  }
}

// ── Individual chat ─────────────────────────────────────
async function sendIndividualMessage(text) {
  const personaKey = state.chatMode;
  const p = getPersona(personaKey);
  if (!p) { showToast('Persona not found', true); return; }

  showTypingIndicator(p);

  const body = {
    persona_key: personaKey,
    message: text,
    session_id: getSessionId() || undefined,
  };

  try {
    state.abortController = new AbortController();
    const res = await fetch(`${API}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-API-Key': state.apiKey },
      body: JSON.stringify(body),
      signal: state.abortController.signal,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    removeTypingIndicator();

    setSessionId(data.session_id);

    const msg = {
      id: Date.now() + 1,
      role: 'assistant',
      persona_key: personaKey,
      persona_name: p.name,
      avatar: p.avatar,
      color: p.color,
      content: data.reply,
    };
    state.messages.push(msg);
    renderMessage(msg);
    scrollToBottom();
  } catch (e) {
    removeTypingIndicator();
    if (e.name !== 'AbortError') {
      console.error('Chat error:', e);
      showToast(e.message || 'Something went wrong', true);
    }
  }
}

// ── Render messages ─────────────────────────────────────
function renderAllMessages() {
  dom.messagesContainer.innerHTML = '';
  if (state.messages.length === 0) {
    dom.messagesContainer.appendChild(createWelcomeScreen());
    return;
  }
  state.messages.forEach(msg => renderMessage(msg, false));
  scrollToBottom(false);
}

function createWelcomeScreen() {
  const div = document.createElement('div');
  div.className = 'welcome-screen';
  div.id = 'welcome-screen';

  if (state.chatMode === 'group') {
    div.innerHTML = `
      <div class="welcome-icon">🏛️</div>
      <h2>Welcome to The Council</h2>
      <p>Send a message and all 8 legendary personas will share their perspectives, debate each other, and help you think clearly.</p>
      <div class="welcome-personas">${state.personas.map(p => `<span>${p.avatar} ${p.name}</span>`).join('')}</div>
    `;
  } else {
    const p = getPersona(state.chatMode);
    if (p) {
      div.innerHTML = `
        <div class="welcome-icon">${p.avatar}</div>
        <h2>Chat with ${p.name}</h2>
        <p>${p.tagline}. Start a private conversation and get ${p.name}'s undivided attention and unique perspective.</p>
      `;
    }
  }
  return div;
}

function renderMessage(msg, animate = true) {
  const isUser = msg.role === 'user';
  const el = document.createElement('div');
  el.className = `message ${isUser ? 'is-user' : 'is-assistant'}`;
  el.dataset.messageId = msg.id;
  if (!animate) el.style.animation = 'none';

  // Reply-to badge
  let replyHTML = '';
  if (msg.reply_to_id || msg._reply_to_content) {
    const replyName = msg._reply_to_name || getMessageAuthor(msg.reply_to_id);
    const replyContent = msg._reply_to_content || getMessageContent(msg.reply_to_id);
    const replyColor = msg.color || 'var(--accent)';
    if (replyContent) {
      replyHTML = `
        <div class="msg-reply-badge" style="border-color:${replyColor}">
          <div class="reply-author" style="color:${replyColor}">${replyName || 'User'}</div>
          <div class="reply-text">${escapeHtml(truncate(replyContent, 120))}</div>
        </div>`;
    }
  }
  // Debate reply referencing another persona
  if (msg.reply_to_name && !msg.reply_to_id) {
    const refColor = getPersonaColor(msg.reply_to_key);
    replyHTML = `
      <div class="msg-reply-badge" style="border-color:${refColor}">
        <div class="reply-author" style="color:${refColor}">${msg.reply_to_name}</div>
        <div class="reply-text">responding to their point...</div>
      </div>`;
  }

  // In individual mode, hide persona name/avatar for cleaner look? No — keep it, it looks good.
  const nameHTML = isUser ? '' : `<div class="msg-name" style="color:${msg.color}">${msg.persona_name}</div>`;
  const avatarHTML = isUser ? '' : `<div class="msg-avatar" style="background:${msg.color}20">${msg.avatar}</div>`;
  const timeStr = msg.timestamp ? formatTime(msg.timestamp) : formatTime(new Date().toISOString());

  // Only show reply action in group mode
  const replyActionHTML = state.chatMode === 'group' ? `
    <div class="msg-actions">
      <button class="btn-reply" data-id="${msg.id}" data-name="${isUser ? 'You' : msg.persona_name}" data-content="${escapeAttr(msg.content)}" title="Reply">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="9 17 4 12 9 7"/><path d="M20 18v-2a4 4 0 0 0-4-4H4"/></svg>
      </button>
    </div>` : '';

  el.innerHTML = `
    ${avatarHTML}
    <div class="msg-body">
      ${nameHTML}
      <div class="msg-bubble">
        ${replyHTML}
        ${escapeHtml(msg.content)}
        ${replyActionHTML}
      </div>
      <div class="msg-time">${timeStr}</div>
    </div>
  `;

  dom.messagesContainer.appendChild(el);
}

// ── Typing indicator ────────────────────────────────────
function showTypingIndicator(persona) {
  removeTypingIndicator();
  const el = document.createElement('div');
  el.className = 'typing-indicator';
  el.id = 'typing-indicator';

  const name = persona?.name || 'Someone';
  const avatar = persona?.avatar || '💬';
  const bg = persona?.color ? persona.color + '20' : 'var(--glass-bg-strong)';
  const nameColor = persona?.color || 'var(--text-tertiary)';

  el.innerHTML = `
    <div class="msg-avatar" style="background:${bg}">${avatar}</div>
    <div>
      <div class="typing-name" style="color:${nameColor}">${name} is typing</div>
      <div class="typing-bubble">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div>
  `;
  dom.messagesContainer.appendChild(el);
  scrollToBottom();
}

function removeTypingIndicator() {
  const el = document.getElementById('typing-indicator');
  if (el) el.remove();
}

// ── Reply-to ────────────────────────────────────────────
function setReply(id, name, content) {
  state.replyTo = { id: parseInt(id), persona_name: name, content };
  dom.replyPreview.classList.add('active');
  dom.replyAuthor.textContent = name;
  dom.replyAuthor.style.color = getPersonaColorByName(name);
  dom.replyText.textContent = truncate(content, 80);
  dom.messageInput.focus();
}

function clearReply() {
  state.replyTo = null;
  dom.replyPreview.classList.remove('active');
}

// ── New chat ────────────────────────────────────────────
async function newChat() {
  const sessionId = getSessionId();
  if (sessionId) {
    const endpoint = state.chatMode === 'group'
      ? `${API}/group-history/${sessionId}`
      : `${API}/history/${sessionId}`;
    try { await fetch(endpoint, { method: 'DELETE' }); } catch (e) { /* ignore */ }
  }
  clearSessionId();
  state.messages = [];
  renderAllMessages();
  showToast('New conversation started');
}

// ── Helpers ─────────────────────────────────────────────
function hideWelcome() {
  const ws = document.getElementById('welcome-screen');
  if (ws) ws.remove();
}

function scrollToBottom(smooth = true) {
  requestAnimationFrame(() => {
    dom.messagesContainer.scrollTo({
      top: dom.messagesContainer.scrollHeight,
      behavior: smooth ? 'smooth' : 'auto',
    });
  });
}

function autoResizeInput() {
  const el = dom.messageInput;
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function updateSendButton() {
  const hasText = dom.messageInput.value.trim().length > 0;
  dom.btnSend.classList.toggle('active', hasText && !state.isLoading);
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function escapeAttr(str) {
  return str.replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function truncate(str, len) {
  return str.length > len ? str.slice(0, len) + '…' : str;
}

function formatTime(isoStr) {
  try {
    const d = new Date(isoStr);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch { return ''; }
}

function getMessageAuthor(id) {
  const msg = state.messages.find(m => m.id === id);
  return msg ? (msg.role === 'user' ? 'You' : msg.persona_name) : 'Unknown';
}

function getMessageContent(id) {
  const msg = state.messages.find(m => m.id === id);
  return msg?.content || '';
}

function getPersonaColor(key) {
  return state.personas.find(p => p.key === key)?.color || 'var(--accent)';
}

function getPersonaColorByName(name) {
  if (name === 'You') return 'var(--accent)';
  return state.personas.find(p => p.name === name)?.color || 'var(--accent)';
}

let toastTimer;
function showToast(msg, isError = false) {
  dom.toast.textContent = msg;
  dom.toast.className = `toast visible ${isError ? 'error' : ''}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => dom.toast.classList.remove('visible'), 3000);
}

// ── Event bindings ──────────────────────────────────────
function bindEvents() {
  // Send
  dom.btnSend.addEventListener('click', sendMessage);
  dom.messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });
  dom.messageInput.addEventListener('input', () => { autoResizeInput(); updateSendButton(); });

  // Sidebar toggle (mobile)
  dom.btnMenu.addEventListener('click', () => dom.sidebar.classList.toggle('open'));
  document.addEventListener('click', (e) => {
    if (dom.sidebar.classList.contains('open') && !dom.sidebar.contains(e.target) && e.target !== dom.btnMenu) {
      dom.sidebar.classList.remove('open');
    }
  });

  // Settings modal
  dom.btnSettings.addEventListener('click', showModal);
  dom.btnModalSave.addEventListener('click', saveKey);
  dom.btnModalCancel.addEventListener('click', hideModal);
  dom.modalOverlay.addEventListener('click', (e) => { if (e.target === dom.modalOverlay) hideModal(); });
  dom.apiKeyInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') saveKey(); });

  // New chat
  dom.btnNewChat.addEventListener('click', newChat);

  // Reply buttons (delegated)
  dom.messagesContainer.addEventListener('click', (e) => {
    const btn = e.target.closest('.btn-reply');
    if (btn) setReply(btn.dataset.id, btn.dataset.name, btn.dataset.content);
  });

  // Close reply
  dom.btnCloseReply.addEventListener('click', clearReply);

  // ── Chat switching: group chat button ─────────────────
  dom.btnGroupChat.addEventListener('click', () => switchChat('group'));

  // ── Chat switching: individual persona click (delegated) ──
  dom.personaList.addEventListener('click', (e) => {
    const item = e.target.closest('.persona-item[data-key]');
    if (item) switchChat(item.dataset.key);
  });
}

// ── Boot ────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', init);
