/**
 * Agent Hotline Dashboard - Frontend Application
 */
const API_BASE = '/api';
const WS_URL = `ws://${window.location.host}/ws`;

let state = {
    agents: [],
    total: 0,
    page: 1,
    pageSize: 20,
    totalPages: 1,
    search: '',
    statusFilter: '',
    categoryFilter: '',
    languageFilter: '',
    sortBy: 'created_at:desc',
    currentAgent: null,
    ws: null,
    wsReconnectAttempts: 0,
    maxReconnectAttempts: 10,
    reconnectDelay: 1000,
    theme: 'light',
    categories: [],
    languages: [],
};

// Elements will be initialized in init() after DOM is ready
let elements = {};

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func(...args), wait);
    };
}

function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    state.theme = savedTheme || (prefersDark ? 'dark' : 'light');
    applyTheme(state.theme);
}

function applyTheme(theme) {
    state.theme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    if (elements.themeToggleSun && elements.themeToggleMoon) {
        if (theme === 'dark') {
            elements.themeToggleSun.style.display = 'none';
            elements.themeToggleMoon.style.display = 'block';
        } else {
            elements.themeToggleSun.style.display = 'block';
            elements.themeToggleMoon.style.display = 'none';
        }
    }
}

function toggleTheme() {
    applyTheme(state.theme === 'light' ? 'dark' : 'light');
}

async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const config = {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options,
    };
    if (config.body && typeof config.body === 'object') {
        config.body = JSON.stringify(config.body);
    }
    const response = await fetch(url, config);
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }
    if (response.status === 204) return null;
    return response.json();
}

async function fetchAgents() {
    const params = new URLSearchParams({ page: state.page, page_size: state.pageSize });
    if (state.search) params.append('search', state.search);
    if (state.statusFilter !== '') params.append('is_active', state.statusFilter === 'active' ? 'true' : 'false');
    if (state.categoryFilter !== '') params.append('category', state.categoryFilter);
    if (state.languageFilter !== '') params.append('language', state.languageFilter);
    params.append('sort', state.sortBy);
    const data = await apiRequest(`/agents?${params.toString()}`);
    state.agents = data.items;
    state.total = data.total;
    state.page = data.page;
    state.pageSize = data.page_size;
    state.totalPages = data.total_pages;
    updateStats();
    renderAgentsTable();
    updatePagination();
    // Use global filter options from state.categories/languages (populated from /api/agents/filters)
    updateFilterOptions();
}

async function fetchFilterOptions() {
    const data = await apiRequest('/agents/filters');
    state.categories = data.categories || [];
    state.languages = data.languages || [];
    updateFilterOptions();
}

async function fetchAgent(id) {
    return apiRequest(`/agents/${id}`);
}

async function createAgent(data) {
    return apiRequest('/agents', { method: 'POST', body: data });
}

async function updateAgent(id, data) {
    return apiRequest(`/agents/${id}`, { method: 'PATCH', body: data });
}

async function deleteAgent(id) {
    return apiRequest(`/agents/${id}`, { method: 'DELETE' });
}

async function duplicateAgent(id) {
    return apiRequest(`/agents/${id}/duplicate`, { method: 'POST' });
}

async function updateAgentStatus(id, isActive) {
    return apiRequest(`/agents/${id}/status`, { method: 'PATCH', body: { is_active: isActive } });
}

async function exportAgentsJson() {
    return apiRequest('/agents/export/all');
}

async function exportAgentsCsv() {
    const response = await fetch(`${API_BASE}/agents/export/csv`);
    if (!response.ok) throw new Error('Export failed');
    return response.blob();
}

async function fetchAgentStats() {
    return apiRequest('/agents/stats/summary');
}

function connectWebSocket() {
    if (state.ws && (state.ws.readyState === WebSocket.OPEN || state.ws.readyState === WebSocket.CONNECTING)) return;
    updateWsStatus('connecting');
    try {
        state.ws = new WebSocket(WS_URL);
        state.ws.onopen = () => {
            state.wsReconnectAttempts = 0;
            updateWsStatus('connected');
        };
        state.ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                handleWebSocketMessage(message);
            } catch (e) {
                console.error('Failed to parse WS message:', e);
            }
        };
        state.ws.onclose = () => {
            updateWsStatus('disconnected');
            scheduleReconnect();
        };
        state.ws.onerror = () => {
            updateWsStatus('error');
        };
    } catch (e) {
        console.error('Failed to create WebSocket:', e);
        updateWsStatus('error');
        scheduleReconnect();
    }
}

function scheduleReconnect() {
    if (state.wsReconnectAttempts >= state.maxReconnectAttempts) {
        updateWsStatus('disconnected');
        return;
    }
    const delay = state.reconnectDelay * Math.pow(2, state.wsReconnectAttempts);
    state.wsReconnectAttempts++;
    setTimeout(connectWebSocket, delay);
}

function updateWsStatus(status) {
    const indicator = elements.wsStatus;
    const text = elements.wsStatusText;
    indicator.className = 'status-indicator';
    switch (status) {
        case 'connected': indicator.classList.add('connected'); text.textContent = 'Connected'; break;
        case 'connecting': indicator.classList.add('connecting'); text.textContent = 'Connecting...'; break;
        case 'disconnected': text.textContent = 'Disconnected'; break;
        case 'error': text.textContent = 'Error'; break;
    }
}

function handleWebSocketMessage(message) {
    switch (message.type) {
        case 'agent_created':
            showToast('New agent created!', 'success');
            fetchAgents();
            break;
        case 'agent_updated':
            fetchAgents();
            break;
        case 'agent_deleted':
            fetchAgents();
            showToast('Agent deleted', 'info');
            break;
        case 'agent_duplicated':
            showToast('Agent duplicated!', 'success');
            fetchAgents();
            break;
        case 'pong':
            break;
    }
}

function updateStats() {
    const total = state.total || 0;
    const active = state.agents.filter(a => a.is_active).length;
    const inactive = state.agents.filter(a => !a.is_active).length;
    elements.statTotal.textContent = total;
    elements.statActive.textContent = active;
    elements.statInactive.textContent = inactive;
}

function renderAgentsTable() {
    const tbody = elements.agentsTbody;
    const emptyState = elements.emptyState;
    if (state.agents.length === 0) {
        tbody.innerHTML = '';
        emptyState.style.display = 'flex';
        elements.tableContainer.style.display = 'none';
        return;
    }
    emptyState.style.display = 'none';
    elements.tableContainer.style.display = 'block';

    tbody.innerHTML = state.agents.map(agent => `
        <tr data-id="${agent.id}">
            <td class="cell-name">${escapeHtml(agent.name)}</td>
            <td class="cell-type">${escapeHtml(agent.category)}</td>
            <td class="cell-body">${escapeHtml(agent.language)}</td>
            <td class="cell-body">${escapeHtml(agent.environment)}</td>
            <td class="cell-status">
                <span class="status-badge ${agent.is_active ? 'active' : 'inactive'}" data-status-toggle data-id="${agent.id}" data-current-status="${agent.is_active ? 'active' : 'inactive'}" title="Click to toggle" style="cursor: pointer;">
                    ${agent.is_active ? 'Active' : 'Inactive'}
                </span>
            </td>
            <td><code>${escapeHtml(agent.token ? agent.token.substring(0, 20) + '...' : '-')}</code></td>
            <td><code>${escapeHtml(agent.endpoint ? agent.endpoint.substring(0, 30) + '...' : '-')}</code></td>
            <td>
                <div style="font-size: 0.75rem; color: var(--color-text-secondary);">
                    <div>Finger: ${agent.finger_hole || '-'}</div>
                    <div>Card: ${agent.scrollable_agent_card || '-'}</div>
                </div>
            </td>
            <td><span style="font-size: 0.8125rem; color: var(--color-text-secondary);">${escapeHtml(agent.info ? (agent.info.length > 60 ? agent.info.substring(0, 60) + '...' : agent.info) : '-')}</span></td>
            <td class="cell-actions">
                <div class="action-buttons">
                    <button class="action-btn view" data-action="view" data-id="${agent.id}" title="View/Edit Details">👁</button>
                    <button class="action-btn toggle" data-action="status" data-id="${agent.id}" title="Toggle Active/Inactive">↻</button>
                    <button class="action-btn download" data-action="download" data-id="${agent.id}" title="Download JSON">⬇</button>
                    <button class="action-btn delete" data-action="delete" data-id="${agent.id}" title="Delete">🗑</button>
                    <button class="action-btn" data-action="duplicate" data-id="${agent.id}" title="Duplicate" style="font-size: 0.875rem;">⧉</button>
                </div>
            </td>
        </tr>
    `).join('');

    tbody.querySelectorAll('.action-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const action = btn.dataset.action;
            const id = parseInt(btn.dataset.id, 10);
            handleAction(action, id);
        });
    });

    tbody.querySelectorAll('[data-status-toggle]').forEach(badge => {
        badge.addEventListener('click', (e) => {
            e.stopPropagation();
            const id = parseInt(badge.dataset.id, 10);
            const currentStatus = badge.dataset.currentStatus === 'active';
            cycleAgentStatus(id, !currentStatus);
        });
    });

    tbody.querySelectorAll('tr').forEach(row => {
        row.addEventListener('click', () => {
            const id = parseInt(row.dataset.id, 10);
            handleAction('view', id);
        });
    });
}

function updatePagination() {
    elements.paginationInfo.textContent = `Page ${state.page} of ${state.totalPages || 1}`;
    elements.prevPage.disabled = state.page <= 1;
    elements.nextPage.disabled = state.page >= state.totalPages;
}

function updateFilterOptions() {
    updateSelectOptions(elements.categoryFilter, state.categories);
    updateSelectOptions(elements.languageFilter, state.languages);
}

function updateSelectOptions(selectEl, values) {
    // Keep the first "All" option
    const firstOption = selectEl.options[0];
    const currentValue = selectEl.value;
    selectEl.innerHTML = '';
    selectEl.appendChild(firstOption);
    values.sort().forEach(v => {
        const opt = document.createElement('option');
        opt.value = v;
        opt.textContent = v ? v.charAt(0).toUpperCase() + v.slice(1) : v;
        if (v === currentValue) {
            opt.selected = true;
        }
        selectEl.appendChild(opt);
    });
}

function renderAgentDetail(agent) {
    state.currentAgent = agent;
    elements.modalBody.innerHTML = `
        <div class="detail-grid">
            <div class="detail-label">ID</div>
            <div class="detail-value"><code>${agent.id}</code></div>

            <div class="detail-label">Name</div>
            <div class="detail-value"><input type="text" id="edit-name" value="${escapeHtml(agent.name)}" style="width:100%;padding:6px;border:1px solid var(--color-border);border-radius:var(--radius-sm);background:var(--color-bg-primary);color:var(--color-text-primary);font-size:0.875rem;" /></div>

            <div class="detail-label">Category</div>
            <div class="detail-value"><input type="text" id="edit-category" value="${escapeHtml(agent.category)}" style="width:100%;padding:6px;border:1px solid var(--color-border);border-radius:var(--radius-sm);background:var(--color-bg-primary);color:var(--color-text-primary);font-size:0.875rem;" /></div>

            <div class="detail-label">Language</div>
            <div class="detail-value"><input type="text" id="edit-language" value="${escapeHtml(agent.language)}" style="width:100%;padding:6px;border:1px solid var(--color-border);border-radius:var(--radius-sm);background:var(--color-bg-primary);color:var(--color-text-primary);font-size:0.875rem;" /></div>

            <div class="detail-label">Environment</div>
            <div class="detail-value"><input type="text" id="edit-environment" value="${escapeHtml(agent.environment)}" style="width:100%;padding:6px;border:1px solid var(--color-border);border-radius:var(--radius-sm);background:var(--color-bg-primary);color:var(--color-text-primary);font-size:0.875rem;" /></div>

            <div class="detail-label">Token</div>
            <div class="detail-value"><textarea id="edit-token" rows="2" style="width:100%;padding:6px;border:1px solid var(--color-border);border-radius:var(--radius-sm);background:var(--color-bg-primary);color:var(--color-text-primary);font-size:0.8125rem;font-family:inherit;resize:vertical;">${escapeHtml(agent.token)}</textarea></div>

            <div class="detail-label">Endpoint</div>
            <div class="detail-value"><input type="text" id="edit-endpoint" value="${escapeHtml(agent.endpoint)}" style="width:100%;padding:6px;border:1px solid var(--color-border);border-radius:var(--radius-sm);background:var(--color-bg-primary);color:var(--color-text-primary);font-size:0.875rem;" /></div>

            <div class="detail-label">JS Source</div>
            <div class="detail-value"><input type="text" id="edit-js-source" value="${escapeHtml(agent.js_source)}" style="width:100%;padding:6px;border:1px solid var(--color-border);border-radius:var(--radius-sm);background:var(--color-bg-primary);color:var(--color-text-primary);font-size:0.875rem;" /></div>

            <div class="detail-label">Script</div>
            <div class="detail-value"><input type="text" id="edit-script" value="${escapeHtml(agent.script)}" style="width:100%;padding:6px;border:1px solid var(--color-border);border-radius:var(--radius-sm);background:var(--color-bg-primary);color:var(--color-text-primary);font-size:0.875rem;" /></div>

            <div class="detail-label">Finger Hole Image</div>
            <div class="detail-value"><input type="text" id="edit-finger-hole" value="${escapeHtml(agent.finger_hole || '')}" placeholder="assets/name.png" style="width:100%;padding:6px;border:1px solid var(--color-border);border-radius:var(--radius-sm);background:var(--color-bg-primary);color:var(--color-text-primary);font-size:0.875rem;" /></div>

            <div class="detail-label">Scrollable Card Image</div>
            <div class="detail-value"><input type="text" id="edit-scrollable-card" value="${escapeHtml(agent.scrollable_agent_card || '')}" placeholder="assets/name.png" style="width:100%;padding:6px;border:1px solid var(--color-border);border-radius:var(--radius-sm);background:var(--color-bg-primary);color:var(--color-text-primary);font-size:0.875rem;" /></div>

            <div class="detail-label">Info</div>
            <div class="detail-value"><textarea id="edit-info" rows="3" style="width:100%;padding:8px;border:1px solid var(--color-border);border-radius:var(--radius-sm);background:var(--color-bg-primary);color:var(--color-text-primary);font-size:0.875rem;font-family:inherit;resize:vertical;">${escapeHtml(agent.info || '')}</textarea></div>

            <div class="detail-label">Status</div>
            <div class="detail-value">
                <select id="edit-active" style="width:100%;padding:6px;border:1px solid var(--color-border);border-radius:var(--radius-sm);background:var(--color-bg-primary);color:var(--color-text-primary);font-size:0.875rem;">
                    <option value="true" ${agent.is_active ? 'selected' : ''}>Active</option>
                    <option value="false" ${!agent.is_active ? 'selected' : ''}>Inactive</option>
                </select>
            </div>

            <div class="detail-label">Created At</div>
            <div class="detail-value">${new Date(agent.created_at).toLocaleString()}</div>

            <div class="detail-label">Updated At</div>
            <div class="detail-value">${new Date(agent.updated_at).toLocaleString()}</div>
        </div>
    `;
}

function openModal(modal) {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeModal(modal) {
    modal.classList.remove('active');
    document.body.style.overflow = '';
}

function showConfirm(title, message, onConfirm) {
    elements.confirmTitle.textContent = title;
    elements.confirmBody.textContent = message;
    confirmCallback = onConfirm;
    openModal(elements.confirmModal);
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icons = {
        success: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
        error: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
        info: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
    };
    toast.innerHTML = `
        <div class="toast-icon">${icons[type] || icons.info}</div>
        <div class="toast-message">${escapeHtml(message)}</div>
        <button class="toast-close" aria-label="Dismiss"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>
    `;
    toast.querySelector('.toast-close').addEventListener('click', () => toast.remove());
    elements.toastContainer.appendChild(toast);
    setTimeout(() => {
        if (toast.parentNode) {
            toast.style.animation = 'slideIn 0.2s ease reverse';
            setTimeout(() => toast.remove(), 200);
        }
    }, 5000);
}

let confirmCallback = null;

function handleAction(action, id) {
    const agent = state.agents.find(a => a.id === id);
    if (!agent && action !== 'view') return;
    switch (action) {
        case 'view':
            if (agent) { renderAgentDetail(agent); openModal(elements.detailModal); }
            break;
        case 'status':
            if (agent) cycleAgentStatus(id, !agent.is_active);
            break;
        case 'delete':
            showConfirm('Delete Agent', 'Are you sure you want to permanently delete this agent? This action cannot be undone.', () => performDelete(id));
            break;
        case 'download':
            if (agent) downloadAgentJson(agent);
            break;
        case 'duplicate':
            showConfirm('Duplicate Agent', 'Create a copy of this agent with "(copy)" added to the name?', () => performDuplicate(id));
            break;
    }
}

async function cycleAgentStatus(id, isActive) {
    try {
        await updateAgentStatus(id, isActive);
        showToast(`Agent ${isActive ? 'activated' : 'deactivated'}`, 'success');
        fetchAgents();
    } catch (e) {
        showToast(`Failed to update: ${e.message}`, 'error');
    }
}

async function performDelete(id) {
    try {
        await deleteAgent(id);
        showToast('Agent deleted', 'success');
        fetchAgents();
    } catch (e) {
        showToast(`Failed to delete: ${e.message}`, 'error');
    }
}

async function performDuplicate(id) {
    try {
        await duplicateAgent(id);
        showToast('Agent duplicated', 'success');
        fetchAgents();
    } catch (e) {
        showToast(`Failed to duplicate: ${e.message}`, 'error');
    }
}

function downloadAgentJson(agent) {
    const dataStr = JSON.stringify(agent, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `agent_${agent.id}_${agent.name.replace(/\s+/g, '_')}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('Agent downloaded', 'success');
}

async function handleExportJson() {
    try {
        const data = await exportAgentsJson();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `agents_export_${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
        showToast('JSON export downloaded', 'success');
    } catch (e) {
        showToast(`Export failed: ${e.message}`, 'error');
    }
}

async function handleExportCsv() {
    try {
        const blob = await exportAgentsCsv();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `agents_export_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        showToast('CSV export downloaded', 'success');
    } catch (e) {
        showToast(`Export failed: ${e.message}`, 'error');
    }
}

function setupEventListeners() {
    elements.sidebarToggle.addEventListener('click', () => {
        elements.sidebar.classList.toggle('open');
    });
    if (elements.sidebarCollapseToggle) {
        elements.sidebarCollapseToggle.addEventListener('click', () => {
            elements.sidebar.classList.toggle('collapsed');
        });
    }
    if (elements.themeToggle) {
        elements.themeToggle.addEventListener('click', toggleTheme);
    }
    elements.navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const page = item.dataset.page;
            switchPage(page);
            elements.navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');
            if (window.innerWidth < 1024) {
                elements.sidebar.classList.remove('open');
            }
        });
    });

    const debouncedSearch = debounce(() => {
        state.search = elements.searchFilter.value.trim();
        state.page = 1;
        fetchAgents();
    }, 300);
    elements.searchFilter.addEventListener('input', debouncedSearch);

    elements.statusFilter.addEventListener('change', () => {
        state.statusFilter = elements.statusFilter.value;
        state.page = 1;
        fetchAgents();
    });
    elements.categoryFilter.addEventListener('change', () => {
        state.categoryFilter = elements.categoryFilter.value;
        state.page = 1;
        fetchAgents();
    });
    elements.languageFilter.addEventListener('change', () => {
        state.languageFilter = elements.languageFilter.value;
        state.page = 1;
        fetchAgents();
    });

    elements.sortSelect.addEventListener('change', () => {
        state.sortBy = elements.sortSelect.value;
        state.page = 1;
        fetchAgents();
    });
    elements.pageSizeSelect.addEventListener('change', () => {
        state.pageSize = parseInt(elements.pageSizeSelect.value, 10);
        state.page = 1;
        fetchAgents();
    });

    elements.prevPage.addEventListener('click', () => {
        if (state.page > 1) { state.page--; fetchAgents(); }
    });
    elements.nextPage.addEventListener('click', () => {
        if (state.page < state.totalPages) { state.page++; fetchAgents(); }
    });

    elements.clearFiltersBtn.addEventListener('click', () => {
        elements.searchFilter.value = '';
        elements.statusFilter.value = '';
        elements.categoryFilter.value = '';
        elements.languageFilter.value = '';
        state.search = '';
        state.statusFilter = '';
        state.categoryFilter = '';
        state.languageFilter = '';
        state.page = 1;
        fetchAgents();
    });

    elements.refreshBtn.addEventListener('click', fetchAgents);
    elements.refreshEmpty.addEventListener('click', fetchAgents);
    elements.exportJson.addEventListener('click', handleExportJson);
    elements.exportCsv.addEventListener('click', handleExportCsv);

    elements.modalClose.addEventListener('click', () => closeModal(elements.detailModal));
    elements.modalCloseBtn.addEventListener('click', () => closeModal(elements.detailModal));

    elements.modalDownload.addEventListener('click', () => {
        if (state.currentAgent) downloadAgentJson(state.currentAgent);
    });

    elements.modalSave.addEventListener('click', async () => {
        if (!state.currentAgent) return;
        try {
            const id = state.currentAgent.id;
            const data = {
                name: document.getElementById('edit-name').value,
                category: document.getElementById('edit-category').value,
                language: document.getElementById('edit-language').value,
                environment: document.getElementById('edit-environment').value,
                token: document.getElementById('edit-token').value,
                endpoint: document.getElementById('edit-endpoint').value,
                js_source: document.getElementById('edit-js-source').value,
                script: document.getElementById('edit-script').value,
                finger_hole: document.getElementById('edit-finger-hole').value || null,
                scrollable_agent_card: document.getElementById('edit-scrollable-card').value || null,
                info: document.getElementById('edit-info').value || null,
                is_active: document.getElementById('edit-active').value === 'true',
            };
            await updateAgent(id, data);
            showToast('Agent updated', 'success');
            fetchAgents();
            closeModal(elements.detailModal);
        } catch (e) {
            showToast(`Failed to save: ${e.message}`, 'error');
        }
    });

    elements.modalDuplicate.addEventListener('click', () => {
        if (!state.currentAgent) return;
        showConfirm('Duplicate Agent', 'Create a copy of this agent?', () => performDuplicate(state.currentAgent.id));
    });

    elements.confirmCancel.addEventListener('click', () => closeModal(elements.confirmModal));
    elements.confirmOk.addEventListener('click', () => {
        if (confirmCallback) { confirmCallback(); confirmCallback = null; }
        closeModal(elements.confirmModal);
    });

    [elements.detailModal, elements.confirmModal].forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal(modal);
        });
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeModal(elements.detailModal);
            closeModal(elements.confirmModal);
        }
        if (e.key === 'f' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            elements.searchFilter.focus();
        }
    });

    document.querySelectorAll('.trainings-table th[data-sort]').forEach(th => {
        th.addEventListener('click', () => {
            const sortKey = th.dataset.sort;
            const currentSort = state.sortBy;
            let newSort;
            if (currentSort.startsWith(sortKey + ':asc')) {
                newSort = `${sortKey}:desc`;
            } else {
                newSort = `${sortKey}:asc`;
            }
            state.sortBy = newSort;
            state.page = 1;
            fetchAgents();
            document.querySelectorAll('.trainings-table th').forEach(h => {
                h.classList.remove('sorted-asc', 'sorted-desc');
            });
            th.classList.add(newSort.endsWith('asc') ? 'sorted-asc' : 'sorted-desc');
        });
    });
}

function switchPage(pageName) {
    elements.pages.forEach(page => {
        page.classList.toggle('active', page.id === `page-${pageName}`);
    });
    elements.navItems.forEach(n => n.classList.remove('active'));
    const activeNav = document.querySelector(`.nav-item[data-page="${pageName}"]`);
    if (activeNav) activeNav.classList.add('active');
    const titles = { dashboard: 'Dashboard', analytics: 'Analytics', settings: 'Settings' };
    elements.pageTitle.textContent = titles[pageName] || 'Dashboard';
    if (pageName === 'dashboard') fetchAgents();
    else if (pageName === 'analytics') renderAnalytics();
}

async function renderAnalytics() {
    try {
        const stats = await fetchAgentStats();
        document.getElementById('analytics-total').textContent = stats.total_agents || 0;
        document.getElementById('analytics-active').textContent = stats.active_agents || 0;
        document.getElementById('analytics-inactive').textContent = stats.inactive_agents || 0;
    } catch (e) {
        console.error('Failed to load analytics:', e);
        showToast('Failed to load analytics', 'error');
    }
}

async function init() {
    console.log('Initializing Agent Hotline Dashboard...');

    // Initialize DOM elements after DOM is ready
    elements = {
        sidebar: document.getElementById('sidebar'),
        sidebarToggle: document.getElementById('sidebar-toggle'),
        sidebarCollapseToggle: document.getElementById('sidebar-collapse-toggle'),
        navItems: document.querySelectorAll('.nav-item'),
        pages: document.querySelectorAll('.page'),
        themeToggle: document.getElementById('theme-toggle'),
        themeToggleSun: document.querySelector('#theme-toggle .icon-sun'),
        themeToggleMoon: document.querySelector('#theme-toggle .icon-moon'),
        searchFilter: document.getElementById('searchFilter'),
        statusFilter: document.getElementById('statusFilter'),
        categoryFilter: document.getElementById('categoryFilter'),
        languageFilter: document.getElementById('languageFilter'),
        sortSelect: document.getElementById('sortSelect'),
        pageSizeSelect: document.getElementById('pageSizeSelect'),
        clearFiltersBtn: document.getElementById('clearFiltersBtn'),
        agentsTbody: document.getElementById('agents-tbody'),
        emptyState: document.getElementById('empty-state'),
        tableContainer: document.querySelector('.table-container'),
        prevPage: document.getElementById('prev-page'),
        nextPage: document.getElementById('next-page'),
        paginationInfo: document.getElementById('pagination-info'),
        refreshBtn: document.getElementById('refresh-btn'),
        refreshEmpty: document.getElementById('refresh-empty'),
        exportJson: document.getElementById('export-json'),
        exportCsv: document.getElementById('export-csv'),
        statTotal: document.getElementById('stat-total'),
        statActive: document.getElementById('stat-active'),
        statInactive: document.getElementById('stat-inactive'),
        wsStatus: document.getElementById('ws-status'),
        wsStatusText: document.getElementById('ws-status-text'),
        detailModal: document.getElementById('detail-modal'),
        modalTitle: document.getElementById('modal-title'),
        modalBody: document.getElementById('modal-body'),
        modalClose: document.getElementById('modal-close'),
        modalCloseBtn: document.getElementById('modal-close-btn'),
        modalDownload: document.getElementById('modal-download'),
        modalSave: document.getElementById('modal-save'),
        modalDuplicate: document.getElementById('modal-duplicate'),
        confirmModal: document.getElementById('confirm-modal'),
        confirmTitle: document.getElementById('confirm-title'),
        confirmBody: document.getElementById('confirm-body'),
        confirmCancel: document.getElementById('confirm-cancel'),
        confirmOk: document.getElementById('confirm-ok'),
        toastContainer: document.getElementById('toast-container'),
        pageTitle: document.getElementById('page-title'),
        appVersion: document.getElementById('app-version'),
        appEnv: document.getElementById('app-env'),
        appDb: document.getElementById('app-db'),
    };

    initTheme();
    setupEventListeners();
    connectWebSocket();
    await fetchFilterOptions();
    await fetchAgents();
    await renderAnalytics();
    await loadSettingsInfo();
    console.log('Agent Hotline Dashboard initialized');
}

async function loadSettingsInfo() {
    try {
        // Get settings from API
        const settings = await apiRequest('/settings');
        const settingsMap = {};
        settings.forEach(s => settingsMap[s.key] = s.value);

        if (elements.appVersion) elements.appVersion.textContent = settingsMap.app_version || '2.0.0';
        if (elements.appEnv) elements.appEnv.textContent = settingsMap.app_env || 'production';
        if (elements.appDb) elements.appDb.textContent = 'MySQL';
    } catch (e) {
        console.warn('Could not load settings info:', e);
        if (elements.appVersion) elements.appVersion.textContent = '2.0.0';
        if (elements.appEnv) elements.appEnv.textContent = 'production';
        if (elements.appDb) elements.appDb.textContent = 'MySQL';
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
