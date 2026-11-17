/**
 * CampusAssist: Administrator Portal Controller.
 * Handles Knowledge Base CRUD, Taxonomy (Topics & Intents),
 * Unresolved Query Inspection & Triage, and Audit Trail searching.
 */

document.addEventListener('DOMContentLoaded', () => {

  // =========================================================================
  // 1. Knowledge Base Management
  // =========================================================================
  const knowledgeModal = document.getElementById('knowledge-modal');
  const knowledgeForm = document.getElementById('knowledge-form');
  const btnOpenCreateKnowledge = document.getElementById('btn-open-create-knowledge');
  const btnCloseKnowledgeModal = document.getElementById('btn-close-knowledge-modal');
  const btnCancelKnowledgeModal = document.getElementById('btn-cancel-knowledge-modal');
  const knowledgeModalTitle = document.getElementById('knowledge-modal-title');

  if (knowledgeModal && knowledgeForm) {
    // Open Create Modal
    btnOpenCreateKnowledge?.addEventListener('click', () => {
      knowledgeForm.reset();
      document.getElementById('knowledge-id').value = '';
      knowledgeModalTitle.textContent = 'Create Knowledge Entry';
      knowledgeModal.style.display = 'flex';
    });

    // Close Modal helpers
    const closeKnowledgeModal = () => { knowledgeModal.style.display = 'none'; };
    btnCloseKnowledgeModal?.addEventListener('click', closeKnowledgeModal);
    btnCancelKnowledgeModal?.addEventListener('click', closeKnowledgeModal);

    // Edit Knowledge Buttons
    document.querySelectorAll('.btn-edit-knowledge').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const row = e.target.closest('.knowledge-row');
        if (!row) return;

        document.getElementById('knowledge-id').value = row.dataset.id;
        document.getElementById('knowledge-intent-select').value = row.dataset.intentId;
        document.getElementById('knowledge-status-select').value = row.dataset.status;
        document.getElementById('knowledge-title-input').value = row.dataset.title;
        document.getElementById('knowledge-summary-input').value = row.dataset.summary;
        document.getElementById('knowledge-content-input').value = row.dataset.content;
        document.getElementById('knowledge-authority-input').value = row.dataset.authority;
        document.getElementById('knowledge-portal-url-input').value = row.dataset.portalUrl;
        document.getElementById('knowledge-keywords-input').value = row.dataset.keywords;
        document.getElementById('knowledge-source-reference-input').value = row.dataset.sourceReference;

        knowledgeModalTitle.textContent = `Edit Knowledge Entry #${row.dataset.id}`;
        knowledgeModal.style.display = 'flex';
      });
    });

    // Submit Create / Edit Knowledge Form
    knowledgeForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const id = document.getElementById('knowledge-id').value;
      const isEdit = Boolean(id);
      const url = isEdit ? `/api/admin/knowledge/${id}` : '/api/admin/knowledge';
      const method = isEdit ? 'PUT' : 'POST';

      const payload = {
        intent_id: parseInt(document.getElementById('knowledge-intent-select').value, 10),
        verification_status: document.getElementById('knowledge-status-select').value,
        title: document.getElementById('knowledge-title-input').value.trim(),
        summary: document.getElementById('knowledge-summary-input').value.trim(),
        content: document.getElementById('knowledge-content-input').value.trim(),
        contact_authority: document.getElementById('knowledge-authority-input').value.trim(),
        official_portal_url: document.getElementById('knowledge-portal-url-input').value.trim(),
        keywords: document.getElementById('knowledge-keywords-input').value.trim(),
        source_reference: document.getElementById('knowledge-source-reference-input').value.trim()
      };

      fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          alert(`Knowledge entry ${isEdit ? 'updated' : 'created'} and indexed successfully!`);
          window.location.reload();
        } else {
          alert('Error: ' + (data.message || data.error || 'Operation failed'));
        }
      })
      .catch(err => {
        console.error(err);
        alert('Network error saving knowledge entry.');
      });
    });

    // Verify Knowledge Button
    document.querySelectorAll('.btn-verify-knowledge').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.dataset.id;
        if (!confirm(`Verify knowledge entry #${id}? It will be indexed for student retrieval.`)) return;

        fetch(`/api/admin/knowledge/${id}/verify`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' }
        })
        .then(res => res.json())
        .then(data => {
          if (data.status === 'success') {
            alert('Knowledge entry verified and indexed!');
            window.location.reload();
          } else {
            alert('Error: ' + (data.message || 'Verification failed'));
          }
        })
        .catch(err => console.error(err));
      });
    });

    // Toggle Active / Inactive Button
    document.querySelectorAll('.btn-toggle-active-knowledge').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.dataset.id;
        const action = btn.dataset.action;
        fetch(`/api/admin/knowledge/${id}/toggle-active`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        })
        .then(res => res.json())
        .then(data => {
          if (data.status === 'success') {
            window.location.reload();
          } else {
            alert('Error: ' + (data.message || 'Status toggle failed'));
          }
        })
        .catch(err => console.error(err));
      });
    });

    // Client-side Filter for Knowledge
    const searchInput = document.getElementById('knowledge-search-input');
    const topicFilter = document.getElementById('knowledge-filter-topic');
    const statusFilter = document.getElementById('knowledge-filter-status');
    const activeFilter = document.getElementById('knowledge-filter-active');
    const countBadge = document.getElementById('knowledge-count');

    const filterKnowledgeRows = () => {
      const query = (searchInput?.value || '').toLowerCase().trim();
      const topic = topicFilter?.value || '';
      const status = statusFilter?.value || '';
      const active = activeFilter?.value || '';

      const rows = document.querySelectorAll('#knowledge-table tbody tr.knowledge-row');
      let visible = 0;

      rows.forEach(row => {
        const rowTitle = (row.dataset.title || '').toLowerCase();
        const rowSummary = (row.dataset.summary || '').toLowerCase();
        const rowKeywords = (row.dataset.keywords || '').toLowerCase();
        const rowTopic = row.dataset.topic || '';
        const rowStatus = row.dataset.status || '';
        const rowActive = row.dataset.isActive === '1' ? 'active' : 'inactive';

        const matchesQuery = !query || rowTitle.includes(query) || rowSummary.includes(query) || rowKeywords.includes(query);
        const matchesTopic = !topic || rowTopic === topic;
        const matchesStatus = !status || rowStatus === status;
        const matchesActive = !active || rowActive === active;

        if (matchesQuery && matchesTopic && matchesStatus && matchesActive) {
          row.style.display = '';
          visible++;
        } else {
          row.style.display = 'none';
        }
      });

      if (countBadge) countBadge.textContent = visible;
    };

    searchInput?.addEventListener('input', filterKnowledgeRows);
    topicFilter?.addEventListener('change', filterKnowledgeRows);
    statusFilter?.addEventListener('change', filterKnowledgeRows);
    activeFilter?.addEventListener('change', filterKnowledgeRows);
  }


  // =========================================================================
  // 2. Taxonomy Management (Topics & Intents)
  // =========================================================================
  const topicModal = document.getElementById('topic-modal');
  const topicForm = document.getElementById('topic-form');
  const btnOpenCreateTopic = document.getElementById('btn-open-create-topic');
  const btnCloseTopicModal = document.getElementById('btn-close-topic-modal');
  const btnCancelTopicModal = document.getElementById('btn-cancel-topic-modal');
  const topicModalTitle = document.getElementById('topic-modal-title');

  if (topicModal && topicForm) {
    btnOpenCreateTopic?.addEventListener('click', () => {
      topicForm.reset();
      document.getElementById('topic-id').value = '';
      topicModalTitle.textContent = 'Create Topic';
      topicModal.style.display = 'flex';
    });

    const closeTopicModal = () => { topicModal.style.display = 'none'; };
    btnCloseTopicModal?.addEventListener('click', closeTopicModal);
    btnCancelTopicModal?.addEventListener('click', closeTopicModal);

    document.querySelectorAll('.btn-edit-topic').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const row = e.target.closest('.topic-row');
        if (!row) return;

        document.getElementById('topic-id').value = row.dataset.id;
        document.getElementById('topic-name-input').value = row.dataset.name;
        document.getElementById('topic-slug-input').value = row.dataset.slug;
        document.getElementById('topic-desc-input').value = row.dataset.description;
        document.getElementById('topic-icon-input').value = row.dataset.icon;
        document.getElementById('topic-active-select').value = row.dataset.isActive;

        topicModalTitle.textContent = `Edit Topic #${row.dataset.id}`;
        topicModal.style.display = 'flex';
      });
    });

    topicForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const id = document.getElementById('topic-id').value;
      const isEdit = Boolean(id);
      const url = isEdit ? `/api/admin/topics/${id}` : '/api/admin/topics';
      const method = isEdit ? 'PUT' : 'POST';

      const payload = {
        name: document.getElementById('topic-name-input').value.trim(),
        slug: document.getElementById('topic-slug-input').value.trim(),
        description: document.getElementById('topic-desc-input').value.trim(),
        icon: document.getElementById('topic-icon-input').value.trim(),
        is_active: document.getElementById('topic-active-select').value === '1'
      };

      fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          alert(`Topic ${isEdit ? 'updated' : 'created'} successfully!`);
          window.location.reload();
        } else {
          alert('Error: ' + (data.message || data.error || 'Operation failed'));
        }
      })
      .catch(err => console.error(err));
    });
  }

  // Intents
  const intentModal = document.getElementById('intent-modal');
  const intentForm = document.getElementById('intent-form');
  const btnOpenCreateIntent = document.getElementById('btn-open-create-intent');
  const btnCloseIntentModal = document.getElementById('btn-close-intent-modal');
  const btnCancelIntentModal = document.getElementById('btn-cancel-intent-modal');
  const intentModalTitle = document.getElementById('intent-modal-title');

  if (intentModal && intentForm) {
    btnOpenCreateIntent?.addEventListener('click', () => {
      intentForm.reset();
      document.getElementById('intent-id').value = '';
      intentModalTitle.textContent = 'Create Semantic Intent';
      intentModal.style.display = 'flex';
    });

    const closeIntentModal = () => { intentModal.style.display = 'none'; };
    btnCloseIntentModal?.addEventListener('click', closeIntentModal);
    btnCancelIntentModal?.addEventListener('click', closeIntentModal);

    document.querySelectorAll('.btn-edit-intent').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const row = e.target.closest('.intent-row');
        if (!row) return;

        document.getElementById('intent-id').value = row.dataset.id;
        document.getElementById('intent-topic-select').value = row.dataset.topicId;
        document.getElementById('intent-name-input').value = row.dataset.name;
        document.getElementById('intent-slug-input').value = row.dataset.slug;
        document.getElementById('intent-desc-input').value = row.dataset.description;
        document.getElementById('intent-active-select').value = row.dataset.isActive;

        intentModalTitle.textContent = `Edit Intent #${row.dataset.id}`;
        intentModal.style.display = 'flex';
      });
    });

    intentForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const id = document.getElementById('intent-id').value;
      const isEdit = Boolean(id);
      const url = isEdit ? `/api/admin/intents/${id}` : '/api/admin/intents';
      const method = isEdit ? 'PUT' : 'POST';

      const payload = {
        topic_id: parseInt(document.getElementById('intent-topic-select').value, 10),
        name: document.getElementById('intent-name-input').value.trim(),
        slug: document.getElementById('intent-slug-input').value.trim(),
        description: document.getElementById('intent-desc-input').value.trim(),
        is_active: document.getElementById('intent-active-select').value === '1'
      };

      fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          alert(`Intent ${isEdit ? 'updated' : 'created'} successfully!`);
          window.location.reload();
        } else {
          alert('Error: ' + (data.message || data.error || 'Operation failed'));
        }
      })
      .catch(err => console.error(err));
    });

    // Filter Intents by Topic Select
    const filterIntentTopic = document.getElementById('filter-intent-topic');
    filterIntentTopic?.addEventListener('change', () => {
      const selected = filterIntentTopic.value;
      const rows = document.querySelectorAll('#intents-table tbody tr.intent-row');
      let visible = 0;
      rows.forEach(row => {
        if (!selected || row.dataset.topicName === selected) {
          row.style.display = '';
          visible++;
        } else {
          row.style.display = 'none';
        }
      });
      const countEl = document.getElementById('intents-count');
      if (countEl) countEl.textContent = visible;
    });
  }


  // =========================================================================
  // 3. Unresolved Queries Triage & Inspection
  // =========================================================================
  const inspectModal = document.getElementById('inspect-modal');
  const btnCloseInspectModal = document.getElementById('btn-close-inspect-modal');
  let currentInspectedId = null;

  if (inspectModal) {
    const closeInspectModal = () => { inspectModal.style.display = 'none'; };
    btnCloseInspectModal?.addEventListener('click', closeInspectModal);

    // Click Inspect on any row
    document.querySelectorAll('.btn-inspect-query').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const row = e.target.closest('.unresolved-row');
        if (!row) return;

        currentInspectedId = row.dataset.id;
        document.getElementById('inspect-id-badge').textContent = `(#${row.dataset.id})`;
        document.getElementById('inspect-query-text').textContent = `"${row.dataset.queryText}"`;
        document.getElementById('inspect-topic').textContent = row.dataset.topic || 'General';
        document.getElementById('inspect-intent').textContent = row.dataset.intent || 'Unknown';

        const classConf = parseFloat(row.dataset.classConf) || 0;
        document.getElementById('inspect-class-conf-text').textContent = `${classConf}%`;
        document.getElementById('inspect-class-conf-bar').style.width = `${Math.min(100, Math.max(0, classConf))}%`;

        const retConf = parseFloat(row.dataset.retrievalConf) || 0;
        document.getElementById('inspect-retrieval-conf-text').textContent = `${retConf}%`;
        document.getElementById('inspect-retrieval-conf-bar').style.width = `${Math.min(100, Math.max(0, retConf))}%`;

        document.getElementById('inspect-status-badge').textContent = row.dataset.status.toUpperCase();
        document.getElementById('inspect-created-at').textContent = row.dataset.createdAt || '-';
        document.getElementById('inspect-conv-id').textContent = row.dataset.conversationId || 'None';
        document.getElementById('inspect-notes').textContent = row.dataset.adminNotes || 'No triage notes yet.';

        inspectModal.style.display = 'flex';
      });
    });

    // Inspect Modal Quick Status Actions:
    const updateQueryStatus = (id, newStatus, notes = '') => {
      fetch(`/api/admin/unresolved/${id}/status`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus, notes: notes })
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          alert(`Query status updated to '${newStatus}'.`);
          window.location.reload();
        } else {
          alert('Error: ' + (data.message || data.error || 'Failed to update status'));
        }
      })
      .catch(err => console.error(err));
    };

    document.getElementById('btn-inspect-under-review')?.addEventListener('click', () => {
      if (currentInspectedId) updateQueryStatus(currentInspectedId, 'under_review', 'Under evaluation by administrator.');
    });

    document.getElementById('btn-inspect-reject')?.addEventListener('click', () => {
      if (!currentInspectedId) return;
      const notes = prompt('Enter rejection reason / administrative note:');
      if (notes !== null) updateQueryStatus(currentInspectedId, 'rejected', notes || 'Irrelevant or out of scope for NIT Durgapur.');
    });

    document.getElementById('btn-inspect-close')?.addEventListener('click', () => {
      if (!currentInspectedId) return;
      const notes = prompt('Enter closure reason:');
      if (notes !== null) updateQueryStatus(currentInspectedId, 'closed', notes || 'Resolved externally or closed without action.');
    });

    document.getElementById('btn-inspect-resolve-direct')?.addEventListener('click', () => {
      if (!currentInspectedId) return;
      const row = document.querySelector(`.unresolved-row[data-id="${currentInspectedId}"]`);
      closeInspectModal();
      if (row) openResolveModal(row);
    });

    // Client-side search for unresolved queries
    const searchUnresolved = document.getElementById('unresolved-search-input');
    const unresolvedCountBadge = document.getElementById('unresolved-count');
    searchUnresolved?.addEventListener('input', () => {
      const q = searchUnresolved.value.toLowerCase().trim();
      const rows = document.querySelectorAll('#unresolved-table tbody tr.unresolved-row');
      let visible = 0;
      rows.forEach(r => {
        const text = (r.dataset.queryText || '').toLowerCase();
        const topic = (r.dataset.topic || '').toLowerCase();
        const intent = (r.dataset.intent || '').toLowerCase();
        if (!q || text.includes(q) || topic.includes(q) || intent.includes(q)) {
          r.style.display = '';
          visible++;
        } else {
          r.style.display = 'none';
        }
      });
      if (unresolvedCountBadge) unresolvedCountBadge.textContent = visible;
    });
  }

  // Resolve Modal & Submissions
  const resolveModal = document.getElementById('resolve-modal');
  const btnCloseResolveModal = document.getElementById('btn-close-resolve-modal');
  const btnCancelResolveModal = document.getElementById('btn-cancel-resolve-modal');
  const btnCancelMapModal = document.getElementById('btn-cancel-map-modal');

  const tabBtnAddKnowledge = document.getElementById('tab-btn-add-knowledge');
  const tabBtnMapIntent = document.getElementById('tab-btn-map-intent');
  const formNewKnowledge = document.getElementById('resolve-new-knowledge-form');
  const formMapIntent = document.getElementById('resolve-map-intent-form');

  const openResolveModal = (row) => {
    if (!resolveModal) return;
    const queryId = row.dataset.id;
    const queryText = row.dataset.queryText;

    document.getElementById('resolve-modal-id-badge').textContent = `(#${queryId})`;
    document.getElementById('resolve-modal-query-text').textContent = `"${queryText}"`;
    document.getElementById('resolve-query-id').value = queryId;
    document.getElementById('resolve-map-query-id').value = queryId;

    // Reset forms
    formNewKnowledge?.reset();
    formMapIntent?.reset();
    document.getElementById('resolve-query-id').value = queryId;
    document.getElementById('resolve-map-query-id').value = queryId;

    // Show Panel 1 by default
    if (tabBtnAddKnowledge && tabBtnMapIntent) {
      tabBtnAddKnowledge.className = 'btn-action btn-primary resolve-tab-btn';
      tabBtnMapIntent.className = 'btn-action btn-secondary resolve-tab-btn';
      formNewKnowledge.style.display = 'block';
      formMapIntent.style.display = 'none';
    }

    resolveModal.style.display = 'flex';
  };

  if (resolveModal) {
    const closeResolveModal = () => { resolveModal.style.display = 'none'; };
    btnCloseResolveModal?.addEventListener('click', closeResolveModal);
    btnCancelResolveModal?.addEventListener('click', closeResolveModal);
    btnCancelMapModal?.addEventListener('click', closeResolveModal);

    document.querySelectorAll('.btn-open-resolve-modal').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const row = e.target.closest('.unresolved-row');
        if (row) openResolveModal(row);
      });
    });

    // Tab switching
    tabBtnAddKnowledge?.addEventListener('click', () => {
      tabBtnAddKnowledge.className = 'btn-action btn-primary resolve-tab-btn';
      tabBtnMapIntent.className = 'btn-action btn-secondary resolve-tab-btn';
      formNewKnowledge.style.display = 'block';
      formMapIntent.style.display = 'none';
    });

    tabBtnMapIntent?.addEventListener('click', () => {
      tabBtnMapIntent.className = 'btn-action btn-primary resolve-tab-btn';
      tabBtnAddKnowledge.className = 'btn-action btn-secondary resolve-tab-btn';
      formNewKnowledge.style.display = 'none';
      formMapIntent.style.display = 'block';
    });

    // Submit Panel 1: New Knowledge Resolution
    formNewKnowledge?.addEventListener('submit', (e) => {
      e.preventDefault();
      const queryId = document.getElementById('resolve-query-id').value;
      const payload = {
        action: 'new_knowledge',
        intent_id: parseInt(document.getElementById('resolve-intent-select').value, 10),
        title: document.getElementById('resolve-title-input').value.trim(),
        summary: document.getElementById('resolve-summary-input').value.trim(),
        content: document.getElementById('resolve-content-input').value.trim(),
        contact_authority: document.getElementById('resolve-authority-input').value.trim(),
        official_portal_url: document.getElementById('resolve-url-input').value.trim(),
        notes: document.getElementById('resolve-notes-input').value.trim()
      };

      fetch(`/api/admin/unresolved/${queryId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          alert('Verified knowledge created, indexed into semantic search, and query marked verified!');
          window.location.reload();
        } else {
          alert('Error: ' + (data.message || data.error || 'Failed to resolve query'));
        }
      })
      .catch(err => {
        console.error(err);
        alert('Network error submitting verified knowledge resolution.');
      });
    });

    // Submit Panel 2: Map to Existing Intent
    formMapIntent?.addEventListener('submit', (e) => {
      e.preventDefault();
      const queryId = document.getElementById('resolve-map-query-id').value;
      const payload = {
        action: 'map_intent',
        intent_id: parseInt(document.getElementById('resolve-map-intent-select').value, 10),
        notes: document.getElementById('resolve-map-notes-input').value.trim()
      };

      fetch(`/api/admin/unresolved/${queryId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          alert('Query successfully linked to intent and indexed!');
          window.location.reload();
        } else {
          alert('Error: ' + (data.message || data.error || 'Failed to link intent'));
        }
      })
      .catch(err => {
        console.error(err);
        alert('Network error linking intent.');
      });
    });
  }


  // =========================================================================
  // 4. Audit Trail Search
  // =========================================================================
  const auditSearchInput = document.getElementById('audit-search-input');
  auditSearchInput?.addEventListener('input', () => {
    const q = auditSearchInput.value.toLowerCase().trim();
    const rows = document.querySelectorAll('#audit-table tbody tr.audit-row');
    rows.forEach(r => {
      const admin = (r.dataset.admin || '').toLowerCase();
      const action = (r.dataset.action || '').toLowerCase();
      const target = (r.dataset.target || '').toLowerCase();
      const details = (r.dataset.details || '').toLowerCase();
      if (!q || admin.includes(q) || action.includes(q) || target.includes(q) || details.includes(q)) {
        r.style.display = '';
      } else {
        r.style.display = 'none';
      }
    });
  });

});
