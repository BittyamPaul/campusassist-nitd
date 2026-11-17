/**
 * CampusAssist: Student Chat UI Controller & Conversation Manager.
 * Production-ready client logic for the NIT Durgapur AI Student Assistant.
 *
 * Capabilities:
 * - Real-time communication with Flask backend (/api/chat, /api/conversations, /api/feedback)
 * - Complete conversation management (create, switch, view previous, continue, delete, clear all)
 * - Persistent conversation sessions via localStorage and SQLite
 * - Conversational context support for follow-up questions
 * - Markdown-lite rendering for rich, readable responses
 * - Verified knowledge metadata display & official portal links
 * - Helpful / Unhelpful feedback reporting
 * - Auto-resizing textarea with Enter-to-send and Shift+Enter newline
 * - Error banner with instant retry capability
 * - Interactive suggestion chips and topic explore cards
 * - Mobile responsive drawer toggle and backdrop handling
 */

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const chatForm = document.getElementById('chatForm');
  const queryInput = document.getElementById('queryInput');
  const sendBtn = document.getElementById('sendBtn');
  const chatMessages = document.getElementById('chatMessages');
  const welcomeScreen = document.getElementById('welcomeScreen');
  const sessionDisplay = document.getElementById('sessionDisplay');
  const clearChatBtn = document.getElementById('clearChatBtn');
  const headerClearBtn = document.getElementById('headerClearBtn');
  const chatErrorBanner = document.getElementById('chatErrorBanner');
  const errorMessageText = document.getElementById('errorMessageText');
  const errorRetryBtn = document.getElementById('errorRetryBtn');
  const errorDismissBtn = document.getElementById('errorDismissBtn');
  const toggleSidebarBtn = document.getElementById('toggleSidebarBtn');
  const closeSidebarBtn = document.getElementById('closeSidebarBtn');
  const sidebarBackdrop = document.getElementById('sidebarBackdrop');
  const chatSidebar = document.getElementById('chatSidebar');

  // Sidebar Tabs & Conversation Elements
  const tabBtnConversations = document.getElementById('tabBtnConversations');
  const tabBtnExplore = document.getElementById('tabBtnExplore');
  const tabPaneConversations = document.getElementById('tabPaneConversations');
  const tabPaneExplore = document.getElementById('tabPaneExplore');
  const conversationList = document.getElementById('conversationList');
  const clearAllConversationsBtn = document.getElementById('clearAllConversationsBtn');

  // State
  let lastFailedQuery = '';
  let isSending = false;
  let lastConversationsFetchTime = 0;
  const CONVERSATIONS_CACHE_TTL_MS = 5000;

  // 1. Session & History Initialization
  let sessionId = getOrCreateSessionId();
  updateSessionDisplay(sessionId);
  loadConversationHistory(sessionId);
  loadConversationsList();

  // 2. Sidebar Tab Controls
  if (tabBtnConversations && tabBtnExplore) {
    tabBtnConversations.addEventListener('click', () => {
      tabBtnConversations.classList.add('active');
      tabBtnConversations.setAttribute('aria-selected', 'true');
      tabBtnExplore.classList.remove('active');
      tabBtnExplore.setAttribute('aria-selected', 'false');
      if (tabPaneConversations) tabPaneConversations.style.display = 'block';
      if (tabPaneExplore) tabPaneExplore.style.display = 'none';
      loadConversationsList();
    });

    tabBtnExplore.addEventListener('click', () => {
      tabBtnExplore.classList.add('active');
      tabBtnExplore.setAttribute('aria-selected', 'true');
      tabBtnConversations.classList.remove('active');
      tabBtnConversations.setAttribute('aria-selected', 'false');
      if (tabPaneExplore) tabPaneExplore.style.display = 'block';
      if (tabPaneConversations) tabPaneConversations.style.display = 'none';
    });
  }

  // 3. Event Listeners for Chat Submission & Keyboard Controls
  if (chatForm) {
    chatForm.addEventListener('submit', (e) => {
      e.preventDefault();
      handleSend();
    });
  }

  if (queryInput) {
    // Auto-grow textarea height
    queryInput.addEventListener('input', () => {
      queryInput.style.height = 'auto';
      queryInput.style.height = Math.min(queryInput.scrollHeight, 120) + 'px';
      if (sendBtn) {
        sendBtn.disabled = queryInput.value.trim().length === 0 || isSending;
      }
    });

    // Enter to send (Shift+Enter for newline)
    queryInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (!isSending && queryInput.value.trim()) {
          handleSend();
        }
      }
    });
  }

  // 4. New Chat / Reset Conversation Listeners
  if (clearChatBtn) {
    clearChatBtn.addEventListener('click', startNewConversation);
  }
  if (headerClearBtn) {
    headerClearBtn.addEventListener('click', startNewConversation);
  }

  // 5. Clear All Conversations Button
  if (clearAllConversationsBtn) {
    clearAllConversationsBtn.addEventListener('click', clearAllConversations);
  }

  // 6. Error Banner Actions
  if (errorRetryBtn) {
    errorRetryBtn.addEventListener('click', () => {
      hideErrorBanner();
      if (lastFailedQuery) {
        queryInput.value = lastFailedQuery;
        handleSend();
      }
    });
  }

  if (errorDismissBtn) {
    errorDismissBtn.addEventListener('click', hideErrorBanner);
  }

  // 7. Mobile Drawer Toggle Listeners & Keyboard Accessibility
  if (toggleSidebarBtn && chatSidebar) {
    toggleSidebarBtn.addEventListener('click', () => {
      chatSidebar.classList.add('open');
      if (sidebarBackdrop) {
        sidebarBackdrop.classList.add('open');
        sidebarBackdrop.classList.add('active');
      }
      if (closeSidebarBtn) {
        closeSidebarBtn.focus();
      }
    });
  }

  function closeSidebar() {
    if (chatSidebar) chatSidebar.classList.remove('open');
    if (sidebarBackdrop) {
      sidebarBackdrop.classList.remove('open');
      sidebarBackdrop.classList.remove('active');
    }
    if (toggleSidebarBtn) {
      toggleSidebarBtn.focus();
    }
  }

  if (closeSidebarBtn) closeSidebarBtn.addEventListener('click', closeSidebar);
  if (sidebarBackdrop) sidebarBackdrop.addEventListener('click', closeSidebar);

  // Global Escape key listener: closes drawer or error banner
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (chatSidebar && chatSidebar.classList.contains('open')) {
        closeSidebar();
      } else if (chatErrorBanner && chatErrorBanner.style.display !== 'none') {
        hideErrorBanner();
      }
    }
  });

  // 8. Suggestion Chips & Feature Cards
  setupInteractivePrompts();

  // =========================================================================
  // Core Chat Handlers
  // =========================================================================

  function handleSend() {
    if (isSending) return;
    const query = queryInput.value.trim();
    if (!query) return;

    // Reset input state
    queryInput.value = '';
    queryInput.style.height = 'auto';
    if (sendBtn) sendBtn.disabled = true;

    // Trigger pipeline request
    submitQuery(query);
  }

  function submitQuery(query) {
    hideErrorBanner();
    hideWelcomeScreen();

    // Render student question immediately
    appendMessage(query, 'user');

    // Show animated typing loading indicator
    const loadingId = appendLoadingIndicator();
    setSendingState(true);

    fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: query,
        session_id: sessionId,
      }),
    })
      .then(async (response) => {
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(data.message || `Server error (${response.status})`);
        }
        return data;
      })
      .then((data) => {
        removeLoadingIndicator(loadingId);
        appendMessage(data.answer, 'bot', data);
        lastFailedQuery = '';
        // Refresh conversation history list in sidebar immediately
        loadConversationsList(true);
      })
      .catch((error) => {
        removeLoadingIndicator(loadingId);
        lastFailedQuery = query;
        showErrorBanner(`Failed to connect to CampusAssist: ${error.message}`);
        console.error('Chat error:', error);
      })
      .finally(() => {
        setSendingState(false);
        if (queryInput) queryInput.focus();
      });
  }

  // =========================================================================
  // Message Rendering & Formatting
  // =========================================================================

  function appendMessage(text, sender, meta = null) {
    hideWelcomeScreen();

    const bubble = document.createElement('div');
    bubble.className = `message-bubble ${sender}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    if (sender === 'bot') {
      avatar.classList.add('bot-avatar');
      avatar.innerHTML = '<img src="/static/images/download.svg" alt="NIT Durgapur" class="avatar-logo-img" width="34" height="34">';
    } else {
      avatar.textContent = '👤';
    }

    const content = document.createElement('div');
    content.className = 'message-content';

    if (sender === 'bot') {
      // 1. Verification status header badge
      const isVerified = meta && meta.is_verified;
      const statusTag = document.createElement('div');
      statusTag.className = `msg-status-tag ${isVerified ? 'verified' : 'unverified'}`;
      statusTag.innerHTML = isVerified
        ? '<span>🛡️ Verified NIT Record</span>'
        : '<span>⚠️ General Assistance / Unverified</span>';
      content.appendChild(statusTag);

      // 2. Render structured markdown content
      const textContainer = document.createElement('div');
      textContainer.className = 'msg-body';
      textContainer.innerHTML = parseMarkdownLite(text);
      content.appendChild(textContainer);

      // 3. Render verified knowledge metadata card
      if (isVerified) {
        const metaBox = document.createElement('div');
        metaBox.className = 'knowledge-meta-box';

        let metaHtml = '';
        if (meta.topic) {
          metaHtml += `
            <div class="meta-row">
              <span class="meta-label">Domain:</span>
              <span class="meta-val">${escapeHtml(meta.topic)}</span>
              ${meta.intent ? `&bull; <span class="meta-val">${escapeHtml(meta.intent)}</span>` : ''}
            </div>`;
        }

        if (meta.authority_contact) {
          metaHtml += `
            <div class="meta-row">
              <span class="meta-label">Authority:</span>
              <span class="meta-val">${escapeHtml(meta.authority_contact)}</span>
            </div>`;
        }

        if (meta.official_url) {
          const safeUrl = String(meta.official_url).trim();
          if (/^https?:\/\//i.test(safeUrl) || /^\/[^\/]/.test(safeUrl)) {
            metaHtml += `
              <a href="${escapeHtml(safeUrl)}" target="_blank" rel="noopener noreferrer" class="meta-portal-btn">
                <span>NITD Portal Link</span> ↗
              </a>`;
          }
        }

        // 4. Feedback actions
        const messageId = meta.message_id || meta.chat_log_id;
        if (messageId) {
          metaHtml += `
            <div class="meta-feedback-row" data-message-id="${messageId}">
              <span class="feedback-label">Was this answer helpful?</span>
              <div class="feedback-buttons">
                <button type="button" class="btn-feedback btn-helpful" title="Yes, helpful">👍 Yes</button>
                <button type="button" class="btn-feedback btn-unhelpful" title="No, unhelpful">👎 No</button>
              </div>
            </div>`;
        }

        metaBox.innerHTML = metaHtml;
        content.appendChild(metaBox);

        // Attach feedback click handlers if feedback row rendered
        setupFeedbackButtons(metaBox, messageId);
      }
    } else {
      // User message
      const textContainer = document.createElement('div');
      textContainer.className = 'msg-body';
      textContainer.textContent = text;
      content.appendChild(textContainer);
    }

    bubble.appendChild(avatar);
    bubble.appendChild(content);
    chatMessages.appendChild(bubble);

    scrollToBottom();
  }

  // =========================================================================
  // Loading Indicator
  // =========================================================================

  function appendLoadingIndicator() {
    const id = 'loading_' + Date.now();
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble bot loading-bubble-container';
    bubble.id = id;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar bot-avatar';
    avatar.innerHTML = '<img src="/static/images/download.svg" alt="NIT Durgapur" class="avatar-logo-img pulse-glow" width="34" height="34">';

    const content = document.createElement('div');
    content.className = 'message-content loading-bubble';
    content.innerHTML = `
      <div class="typing-dots">
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
      </div>
      <span class="loading-text">Finding information for you...</span>
    `;

    bubble.appendChild(avatar);
    bubble.appendChild(content);
    chatMessages.appendChild(bubble);
    scrollToBottom();
    return id;
  }

  function removeLoadingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  // =========================================================================
  // Conversation List & Session Lifecycle Management
  // =========================================================================

  function getOrCreateSessionId() {
    let sid = localStorage.getItem('campusassist_session_id');
    if (!sid || sid.trim() === '') {
      sid = 'session_' + Math.random().toString(36).substring(2, 9) + '_' + Date.now();
      localStorage.setItem('campusassist_session_id', sid);
    }
    return sid;
  }

  function updateSessionDisplay(sid) {
    if (sessionDisplay) {
      const shortId = sid.length > 18 ? sid.substring(0, 16) + '…' : sid;
      sessionDisplay.textContent = shortId;
      sessionDisplay.title = sid;
    }
  }

  function startNewConversation() {
    fetch('/api/conversations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: 'New Conversation' }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.status === 'success' && data.conversation_id) {
          switchConversation(data.conversation_id);
        } else {
          // Fallback client-generated session id
          const newSid = 'session_' + Math.random().toString(36).substring(2, 9) + '_' + Date.now();
          switchConversation(newSid);
        }
      })
      .catch(() => {
        const newSid = 'session_' + Math.random().toString(36).substring(2, 9) + '_' + Date.now();
        switchConversation(newSid);
      });
  }

  function switchConversation(newSid) {
    sessionId = newSid;
    localStorage.setItem('campusassist_session_id', sessionId);
    updateSessionDisplay(sessionId);

    // Clear current chat messages
    chatMessages.innerHTML = '';
    if (welcomeScreen) {
      chatMessages.appendChild(welcomeScreen);
    }

    hideErrorBanner();
    if (queryInput) {
      queryInput.value = '';
      queryInput.style.height = 'auto';
      queryInput.focus();
    }

    loadConversationHistory(sessionId);
    loadConversationsList();
    closeSidebar();
  }

  function loadConversationsList(force = false) {
    if (!conversationList) return;

    const now = Date.now();
    if (!force && (now - lastConversationsFetchTime < CONVERSATIONS_CACHE_TTL_MS)) {
      return; // Deduplicate rapid tab toggling or redundant fetches
    }

    fetch('/api/conversations?limit=30')
      .then((res) => res.json())
      .then((data) => {
        if (data.status === 'success' && data.conversations) {
          lastConversationsFetchTime = Date.now();
          renderConversationsList(data.conversations);
        }
      })
      .catch((err) => {
        console.warn('Could not load conversations list:', err);
      });
  }


  function renderConversationsList(conversations) {
    if (!conversationList) return;

    conversationList.innerHTML = '';

    if (!conversations || conversations.length === 0) {
      conversationList.innerHTML = `
        <div class="conversations-empty-state">
          <span class="empty-icon">💭</span>
          <span>No saved conversations yet.</span>
        </div>`;
      return;
    }

    conversations.forEach((conv) => {
      const item = document.createElement('div');
      item.className = `conversation-item ${conv.id === sessionId ? 'active' : ''}`;
      item.setAttribute('role', 'listitem');
      item.setAttribute('data-conv-id', conv.id);

      const content = document.createElement('div');
      content.className = 'conv-item-content';

      const title = document.createElement('span');
      title.className = 'conv-item-title';
      title.textContent = conv.title || 'Conversation';
      title.title = conv.title || 'Conversation';

      const meta = document.createElement('div');
      meta.className = 'conv-item-meta';

      const count = document.createElement('span');
      count.className = 'conv-badge';
      count.textContent = `${conv.message_count || 0} msgs`;

      const timeStr = formatRelativeTime(conv.updated_at || conv.created_at);
      const timeSpan = document.createElement('span');
      timeSpan.className = 'conv-time';
      timeSpan.textContent = timeStr;

      meta.appendChild(count);
      meta.appendChild(timeSpan);
      content.appendChild(title);
      content.appendChild(meta);

      const delBtn = document.createElement('button');
      delBtn.type = 'button';
      delBtn.className = 'btn-delete-conv';
      delBtn.innerHTML = '✕';
      delBtn.title = 'Delete this conversation';
      delBtn.setAttribute('aria-label', `Delete conversation ${conv.title}`);

      delBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        deleteConversation(conv.id);
      });

      item.appendChild(content);
      item.appendChild(delBtn);

      item.addEventListener('click', () => {
        if (conv.id !== sessionId) {
          switchConversation(conv.id);
        }
      });

      conversationList.appendChild(item);
    });
  }

  function deleteConversation(convId) {
    fetch(`/api/conversations/${encodeURIComponent(convId)}`, {
      method: 'DELETE',
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.status === 'success') {
          if (convId === sessionId) {
            // Deleted the currently open conversation -> Start fresh
            startNewConversation();
          } else {
            loadConversationsList(true);
          }

        }
      })
      .catch((err) => {
        console.error('Delete conversation error:', err);
      });
  }

  function clearAllConversations() {
    if (!confirm('Are you sure you want to delete all previous conversations?')) {
      return;
    }

    fetch('/api/conversations', {
      method: 'DELETE',
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.status === 'success') {
          startNewConversation();
        }
      })
      .catch((err) => {
        console.error('Clear all conversations error:', err);
      });
  }

  function loadConversationHistory(sid) {
    fetch(`/api/conversations/${encodeURIComponent(sid)}/messages`)
      .then((res) => {
        if (!res.ok) throw new Error('History fetch error');
        return res.json();
      })
      .then((data) => {
        if (data.status === 'success' && data.messages && data.messages.length > 0) {
          hideWelcomeScreen();
          data.messages.forEach((msg) => {
            const role = msg.role === 'assistant' ? 'bot' : 'user';
            const meta = {
              is_verified: Boolean(msg.is_verified),
              topic: msg.intent_name ? 'NIT Durgapur' : null,
              intent: msg.intent_name || null,
              message_id: msg.id,
            };
            appendMessage(msg.content, role, meta);
          });
        } else {
          showWelcomeScreen();
        }
      })
      .catch((err) => {
        console.warn('Could not restore message history:', err);
        showWelcomeScreen();
      });
  }

  function hideWelcomeScreen() {
    if (welcomeScreen) {
      welcomeScreen.style.display = 'none';
    }
  }

  function showWelcomeScreen() {
    if (welcomeScreen) {
      welcomeScreen.style.display = 'flex';
    }
  }

  function formatRelativeTime(dateStr) {
    if (!dateStr) return '';
    try {
      // Normalize SQLite timestamp to UTC
      const date = new Date(dateStr.replace(' ', 'T') + 'Z');
      const now = new Date();
      const diffSec = Math.floor((now - date) / 1000);

      if (isNaN(diffSec) || diffSec < 60) return 'Just now';
      if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
      if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
      return `${Math.floor(diffSec / 86400)}d ago`;
    } catch {
      return '';
    }
  }

  // =========================================================================
  // Feedback Submissions
  // =========================================================================

  function setupFeedbackButtons(container, messageId) {
    const helpfulBtn = container.querySelector('.btn-helpful');
    const unhelpfulBtn = container.querySelector('.btn-unhelpful');
    const feedbackRow = container.querySelector('.meta-feedback-row');

    if (helpfulBtn) {
      helpfulBtn.addEventListener('click', () => {
        sendFeedback(messageId, 'helpful', helpfulBtn, unhelpfulBtn, feedbackRow);
      });
    }

    if (unhelpfulBtn) {
      unhelpfulBtn.addEventListener('click', () => {
        sendFeedback(messageId, 'unhelpful', unhelpfulBtn, helpfulBtn, feedbackRow);
      });
    }
  }

  function sendFeedback(messageId, type, activeBtn, otherBtn, rowElement) {
    activeBtn.disabled = true;
    otherBtn.disabled = true;

    fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_log_id: messageId,
        feedback: type,
      }),
    })
      .then((res) => res.json())
      .then((res) => {
        if (res.status === 'success') {
          activeBtn.classList.add(type === 'helpful' ? 'active-helpful' : 'active-unhelpful');
          const label = rowElement.querySelector('.feedback-label');
          if (label) {
            label.textContent = 'Thank you for your feedback! ✓';
            label.style.color = '#34d399';
          }
        }
      })
      .catch((err) => {
        console.error('Feedback submission error:', err);
        activeBtn.disabled = false;
        otherBtn.disabled = false;
      });
  }

  // =========================================================================
  // Error States
  // =========================================================================

  function showErrorBanner(msg) {
    if (chatErrorBanner && errorMessageText) {
      errorMessageText.textContent = msg;
      chatErrorBanner.style.display = 'flex';
    }
  }

  function hideErrorBanner() {
    if (chatErrorBanner) {
      chatErrorBanner.style.display = 'none';
    }
  }

  function setSendingState(sending) {
    isSending = sending;
    if (sendBtn) {
      sendBtn.disabled = sending;
      sendBtn.setAttribute('aria-busy', sending ? 'true' : 'false');
    }
    if (queryInput) {
      if (sending) {
        queryInput.setAttribute('readonly', 'true');
        queryInput.setAttribute('aria-busy', 'true');
      } else {
        queryInput.removeAttribute('readonly');
        queryInput.removeAttribute('aria-busy');
      }
    }
    if (chatMessages) {
      chatMessages.setAttribute('aria-busy', sending ? 'true' : 'false');
    }
  }

  function scrollToBottom() {
    requestAnimationFrame(() => {
      chatMessages.scrollTop = chatMessages.scrollHeight;
    });
  }

  // =========================================================================
  // Interactive Chips & Feature Cards
  // =========================================================================

  function setupInteractivePrompts() {
    // Sidebar suggestion chips
    document.querySelectorAll('.suggestion-chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        const queryText = chip.getAttribute('data-query') || chip.textContent.trim();
        if (queryText) {
          closeSidebar();
          submitQuery(queryText);
        }
      });
    });

    // Welcome hero cards
    document.querySelectorAll('.welcome-card').forEach((card) => {
      card.addEventListener('click', () => {
        const queryText = card.getAttribute('data-query');
        if (queryText) {
          submitQuery(queryText);
        }
      });
    });

    // Welcome prompt pills
    document.querySelectorAll('.welcome-prompt-pill').forEach((pill) => {
      pill.addEventListener('click', () => {
        const queryText = pill.getAttribute('data-query') || pill.textContent.trim().replace(/^"|"$/g, '');
        if (queryText) {
          submitQuery(queryText);
        }
      });
    });

    // Topic pills in sidebar
    document.querySelectorAll('.topic-pill').forEach((pill) => {
      pill.addEventListener('click', () => {
        const topicSlug = pill.getAttribute('data-topic-slug');
        closeSidebar();
        if (topicSlug === 'hostel') {
          submitQuery('What information is available about hostel facilities?');
        } else if (topicSlug === 'academics') {
          submitQuery('How do I find examination information?');
        } else {
          submitQuery('Tell me about ' + (pill.querySelector('.topic-name')?.textContent || 'this topic'));
        }
      });
    });
  }

  // =========================================================================
  // Markdown-Lite Formatter & Helpers
  // =========================================================================

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function parseMarkdownLite(rawText) {
    if (!rawText) return '';

    // First escape raw HTML to prevent XSS
    let escaped = escapeHtml(rawText);

    // Parse links: [label](url)
    escaped = escaped.replace(
      /\[(.*?)\]\((https?:\/\/[^\s)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
    );

    // Parse bold: **text**
    escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Parse italic: *text* or _text_
    escaped = escaped.replace(/(^|[^\*])\*([^\*]+)\*([^\*]|$)/g, '$1<em>$2</em>$3');

    // Break into lines to parse lists and paragraphs
    const lines = escaped.split('\n');
    let htmlResult = '';
    let inUl = false;
    let inOl = false;

    lines.forEach((line) => {
      const trimmed = line.trim();

      // Check bullet list: * or -
      const bulletMatch = trimmed.match(/^[-*]\s+(.*)/);
      // Check numbered list: 1. or 2.
      const numberMatch = trimmed.match(/^(\d+)\.\s+(.*)/);

      if (bulletMatch) {
        if (inOl) {
          htmlResult += '</ol>';
          inOl = false;
        }
        if (!inUl) {
          htmlResult += '<ul>';
          inUl = true;
        }
        htmlResult += `<li>${bulletMatch[1]}</li>`;
      } else if (numberMatch) {
        if (inUl) {
          htmlResult += '</ul>';
          inUl = false;
        }
        if (!inOl) {
          htmlResult += '<ol>';
          inOl = true;
        }
        htmlResult += `<li>${numberMatch[2]}</li>`;
      } else {
        if (inUl) {
          htmlResult += '</ul>';
          inUl = false;
        }
        if (inOl) {
          htmlResult += '</ol>';
          inOl = false;
        }
        if (trimmed.length > 0) {
          htmlResult += `<p>${trimmed}</p>`;
        }
      }
    });

    if (inUl) htmlResult += '</ul>';
    if (inOl) htmlResult += '</ol>';

    return htmlResult;
  }
});
