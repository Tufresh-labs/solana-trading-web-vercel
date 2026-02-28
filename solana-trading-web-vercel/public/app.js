/**
 * 1SOL Trader - Vercel Edition
 * Phanes-inspired UI with Smart Money integration
 */

// Configuration for Vercel
const CONFIG = {
    API_URL: window.location.origin + '/api',
    REFRESH_INTERVAL: 30000,
};

// State
const state = {
    currentPage: 'dashboard',
    signals: [],
    portfolio: { sol: 50.00, usd: 7500, dailyTarget: 1.00, currentPnl: 0.35 }
};

// DOM Elements
const elements = {
    pages: document.querySelectorAll('.page'),
    navItems: document.querySelectorAll('.nav-item'),
    signalCount: document.getElementById('signal-count'),
    topSignalsContainer: document.getElementById('top-signals-container'),
    signalsGrid: document.getElementById('signals-grid'),
    modal: document.getElementById('token-modal'),
    modalBody: document.getElementById('modal-body'),
    toastContainer: document.getElementById('toast-container'),
    portfolioSol: document.getElementById('portfolio-sol'),
    portfolioUsd: document.getElementById('portfolio-usd'),
    targetRatio: document.getElementById('target-ratio'),
    targetProgress: document.getElementById('target-progress'),
    todayPnl: document.getElementById('today-pnl')
};

// API Functions
const API = {
    async getSignals(minScore = 60) {
        const response = await fetch(`${CONFIG.API_URL}/signals?min_score=${minScore}&limit=10`);
        const data = await response.json();
        if (!data.success) throw new Error(data.error);
        return data.signals;
    },
    
    async analyzeToken(address) {
        const response = await fetch(`${CONFIG.API_URL}/analyze/${address}`);
        const data = await response.json();
        if (!data.success) throw new Error(data.error);
        return data.signal;
    },
    
    async getPortfolio() {
        const response = await fetch(`${CONFIG.API_URL}/portfolio`);
        const data = await response.json();
        if (!data.success) throw new Error(data.error);
        return data.portfolio;
    },
    
    async getHoldings() {
        const response = await fetch(`${CONFIG.API_URL}/holdings`);
        const data = await response.json();
        if (!data.success) throw new Error(data.error);
        return data.holdings;
    },
    
    async executeTrade(tokenAddress, amount) {
        const response = await fetch(`${CONFIG.API_URL}/trade`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token_address: tokenAddress, amount, side: 'buy' })
        });
        const data = await response.json();
        if (!data.success) throw new Error(data.error);
        return data.trade;
    }
};

// Initialize
function init() {
    setupNavigation();
    setupEventListeners();
    loadData();
    startAutoRefresh();
}

function setupNavigation() {
    elements.navItems.forEach(item => {
        item.addEventListener('click', () => {
            const page = item.dataset.page;
            navigateTo(page);
            elements.navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');
        });
    });
}

function navigateTo(page) {
    state.currentPage = page;
    elements.pages.forEach(p => p.classList.remove('active'));
    const targetPage = document.getElementById(`page-${page}`);
    if (targetPage) targetPage.classList.add('active');
    
    if (page === 'signals') renderSignalsPage();
}

function setupEventListeners() {
    document.getElementById('global-search')?.addEventListener('input', debounce((e) => {
        const query = e.target.value;
        if (query.length > 30) analyzeToken(query);
    }, 500));
    
    document.addEventListener('keydown', (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
            e.preventDefault();
            document.getElementById('global-search')?.focus();
        }
    });
    
    document.getElementById('refresh-btn')?.addEventListener('click', () => {
        showToast('Refreshing data...', 'info');
        loadData();
    });
    
    document.querySelector('.modal-close')?.addEventListener('click', closeModal);
    elements.modal?.addEventListener('click', (e) => {
        if (e.target === elements.modal) closeModal();
    });
}

async function loadData() {
    try {
        const signals = await API.getSignals();
        state.signals = signals;
        
        if (elements.signalCount) elements.signalCount.textContent = signals.length;
        renderTopSignals(signals.slice(0, 3));
        
        const portfolio = await API.getPortfolio();
        updatePortfolioDisplay(portfolio);
        
    } catch (error) {
        console.error('Error loading data:', error);
        showToast('Failed to load data', 'error');
    }
}

function updatePortfolioDisplay(portfolio) {
    if (elements.portfolioSol) elements.portfolioSol.textContent = portfolio.sol.toFixed(2);
    if (elements.portfolioUsd) elements.portfolioUsd.textContent = `$${Math.round(portfolio.usd).toLocaleString()}`;
    if (elements.targetRatio) elements.targetRatio.textContent = `${portfolio.current_pnl.toFixed(2)}/${portfolio.daily_target.toFixed(2)} SOL`;
    if (elements.targetProgress) elements.targetProgress.style.width = `${Math.min((portfolio.current_pnl / portfolio.daily_target) * 100, 100)}%`;
    if (elements.todayPnl) {
        elements.todayPnl.textContent = `${portfolio.current_pnl >= 0 ? '+' : ''}${portfolio.current_pnl.toFixed(2)} SOL`;
        elements.todayPnl.className = `stat-value ${portfolio.current_pnl >= 0 ? 'positive' : 'negative'}`;
    }
}

function renderTopSignals(signals) {
    if (!elements.topSignalsContainer) return;
    
    if (signals.length === 0) {
        elements.topSignalsContainer.innerHTML = '<div class="loading">No signals found</div>';
        return;
    }
    
    elements.topSignalsContainer.innerHTML = signals.map(signal => createSignalCard(signal)).join('');
    
    elements.topSignalsContainer.querySelectorAll('.signal-card').forEach((card, i) => {
        card.addEventListener('click', () => openSignalModal(signals[i]));
    });
}

function renderSignalsPage() {
    if (!elements.signalsGrid) return;
    elements.signalsGrid.innerHTML = state.signals.map(signal => createSignalCard(signal, true)).join('');
    elements.signalsGrid.querySelectorAll('.signal-card').forEach((card, i) => {
        card.addEventListener('click', () => openSignalModal(state.signals[i]));
    });
}

function createSignalCard(signal, detailed = false) {
    const signalClass = signal.signal_type.replace('_', '-');
    const badgeText = signal.signal_type.replace('_', ' ').toUpperCase();
    
    return `
        <div class="signal-card ${signalClass}">
            <div class="signal-header">
                <div class="signal-token">
                    <div class="token-icon-img">${signal.symbol[0]}</div>
                    <div class="token-info">
                        <h4>${signal.symbol}</h4>
                        <code class="token-address">${shortenAddress(signal.token_address)}</code>
                    </div>
                </div>
                <div class="signal-badge ${signalClass}">${badgeText}</div>
            </div>
            
            <div class="score-grid">
                <div class="score-item">
                    <div class="score-label">SM Score</div>
                    <div class="score-value" style="color: ${getScoreColor(signal.smart_money_score)}">${signal.smart_money_score}</div>
                    <div class="score-bar-container">
                        <div class="score-bar ${getScoreClass(signal.smart_money_score)}" style="width: ${signal.smart_money_score}%"></div>
                    </div>
                </div>
                <div class="score-item">
                    <div class="score-label">Momentum</div>
                    <div class="score-value" style="color: ${getScoreColor(signal.momentum_score)}">${signal.momentum_score}</div>
                    <div class="score-bar-container">
                        <div class="score-bar ${getScoreClass(signal.momentum_score)}" style="width: ${signal.momentum_score}%"></div>
                    </div>
                </div>
                <div class="score-item">
                    <div class="score-label">Pattern</div>
                    <div class="score-value" style="color: ${getScoreColor(signal.pattern_score)}">${signal.pattern_score}</div>
                    <div class="score-bar-container">
                        <div class="score-bar ${getScoreClass(signal.pattern_score)}" style="width: ${signal.pattern_score}%"></div>
                    </div>
                </div>
            </div>
            
            <div class="signal-details">
                <div class="detail-tree">
                    <div class="tree-line">
                        <span class="tree-branch">├</span>
                        <span class="tree-icon">🧠</span>
                        <span class="tree-label">Smart Money</span>
                        <span class="tree-value">${signal.smart_money_count} wallets</span>
                    </div>
                    <div class="tree-line">
                        <span class="tree-branch">├</span>
                        <span class="tree-icon">📊</span>
                        <span class="tree-label">Volume</span>
                        <span class="tree-value ${signal.volume_trend === 'spiking' ? 'positive' : ''}">${signal.volume_trend} (${signal.volume_ratio}x)</span>
                    </div>
                    <div class="tree-line">
                        <span class="tree-branch">└</span>
                        <span class="tree-icon">📈</span>
                        <span class="tree-label">24h Change</span>
                        <span class="tree-value ${signal.price_momentum_24h >= 0 ? 'positive' : 'negative'}">${signal.price_momentum_24h >= 0 ? '+' : ''}${signal.price_momentum_24h}%</span>
                    </div>
                </div>
            </div>
            
            ${signal.suggested_entry ? `
                <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border-color);">
                    <div style="display: flex; justify-content: space-between; font-size: 12px;">
                        <span style="color: var(--text-tertiary);">Entry: $${formatPrice(signal.suggested_entry)}</span>
                        <span style="color: var(--success);">Target: $${formatPrice(signal.suggested_target)}</span>
                    </div>
                </div>
            ` : ''}
        </div>
    `;
}

function openSignalModal(signal) {
    document.getElementById('modal-token-name').textContent = `${signal.name} ($${signal.symbol})`;
    document.getElementById('modal-token-address').textContent = signal.token_address;
    document.getElementById('modal-token-icon').textContent = signal.symbol[0];
    
    elements.modalBody.innerHTML = `
        <div class="modal-signal-details">
            ${createSignalCard(signal, true)}
            
            <div style="margin-top: 20px;">
                <h4 style="margin-bottom: 12px; color: var(--text-secondary);">Key Insights</h4>
                <div style="background: var(--bg-tertiary); border-radius: var(--radius-md); padding: 16px;">
                    ${signal.key_insights.map(insight => `
                        <div style="padding: 8px 0; border-bottom: 1px solid var(--border-color);">${insight}</div>
                    `).join('')}
                </div>
            </div>
            
            ${signal.green_flags.length > 0 ? `
                <div style="margin-top: 20px;">
                    <h4 style="margin-bottom: 12px; color: var(--success);">✅ Green Flags</h4>
                    <ul style="list-style: none; padding: 0;">
                        ${signal.green_flags.map(flag => `<li style="padding: 4px 0; color: var(--text-secondary);">• ${flag}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
            
            <div style="margin-top: 20px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;">
                <div style="background: var(--bg-tertiary); padding: 16px; border-radius: var(--radius-md); text-align: center;">
                    <div style="font-size: 12px; color: var(--text-tertiary);">Entry</div>
                    <div style="font-size: 18px; font-weight: 700; font-family: var(--font-mono);">$${formatPrice(signal.suggested_entry)}</div>
                </div>
                <div style="background: rgba(239, 68, 68, 0.1); padding: 16px; border-radius: var(--radius-md); text-align: center;">
                    <div style="font-size: 12px; color: var(--danger);">Stop Loss</div>
                    <div style="font-size: 18px; font-weight: 700; font-family: var(--font-mono); color: var(--danger);">$${formatPrice(signal.suggested_stop)}</div>
                </div>
                <div style="background: rgba(16, 185, 129, 0.1); padding: 16px; border-radius: var(--radius-md); text-align: center;">
                    <div style="font-size: 12px; color: var(--success);">Target</div>
                    <div style="font-size: 18px; font-weight: 700; font-family: var(--font-mono); color: var(--success);">$${formatPrice(signal.suggested_target)}</div>
                </div>
            </div>
        </div>
    `;
    
    document.getElementById('modal-buy-btn').onclick = () => executeTrade(signal);
    elements.modal.classList.add('active');
}

function closeModal() {
    elements.modal.classList.remove('active');
}

async function executeTrade(signal) {
    try {
        showToast(`Executing ${signal.symbol} trade...`, 'info');
        const trade = await API.executeTrade(signal.token_address, 0.5);
        showToast(`Trade executed! TX: ${shortenAddress(trade.tx_id)}`, 'success');
        closeModal();
    } catch (error) {
        showToast('Trade failed: ' + error.message, 'error');
    }
}

async function analyzeToken(address) {
    try {
        showToast('Analyzing token...', 'info');
        const signal = await API.analyzeToken(address);
        openSignalModal(signal);
    } catch (error) {
        showToast('Analysis failed', 'error');
    }
}

// Utilities
function shortenAddress(addr) {
    if (!addr || addr.length < 10) return addr;
    return addr.slice(0, 4) + '...' + addr.slice(-4);
}

function formatPrice(price) {
    if (!price) return '0.00';
    if (price < 0.0001) return price.toExponential(2);
    if (price < 1) return price.toFixed(8);
    return price.toFixed(2);
}

function getScoreColor(score) {
    if (score >= 75) return '#10b981';
    if (score >= 50) return '#f59e0b';
    return '#ef4444';
}

function getScoreClass(score) {
    if (score >= 75) return 'high';
    if (score >= 50) return 'medium';
    return 'low';
}

function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = 'toast';
    const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
    toast.innerHTML = `<span style="font-size: 18px;">${icons[type]}</span><span>${message}</span>`;
    elements.toastContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function startAutoRefresh() {
    setInterval(() => {
        if (state.currentPage === 'dashboard') loadData();
    }, CONFIG.REFRESH_INTERVAL);
}

// Start
document.addEventListener('DOMContentLoaded', init);
