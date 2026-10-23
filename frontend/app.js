/* ==========================================================
   OmniSight — Application Logic
   Visual QA & Safe UI Repair Workspace
   ========================================================== */
'use strict';

// ===== Live Server Reload Guard =====
// Prevent Live Server from auto-reloading when backend writes screenshots
if (window.WebSocket) {
  const OriginalWebSocket = window.WebSocket;
  window.WebSocket = function (...args) {
    const ws = new OriginalWebSocket(...args);
    let originalOnMessage = null;
    Object.defineProperty(ws, 'onmessage', {
      get() { return originalOnMessage; },
      set(fn) {
        originalOnMessage = function (event) {
          if (event && event.data === 'reload' && document.body.dataset.inspecting === 'true') {
            console.warn('OmniSight: Live Server auto-reload ignored during active inspection.');
            return;
          }
          if (typeof fn === 'function') fn.call(this, event);
        };
      }
    });
    return ws;
  };
  window.WebSocket.prototype = OriginalWebSocket.prototype;
}

// ===== Configuration =====
const API_BASE = 'http://127.0.0.1:8000';

// ===== State =====
const state = {
  inspections: 0,
  repairs: 0,
  checks: 0,
  issues: [],
  lastInspectionUrl: '',
  lastInspectionViewport: '',
  lastScreenshotUrl: '',
  isInspecting: false,
  isEvaluating: false,
  isRepairing: false,
};

// ===== DOM References =====
const $ = id => document.getElementById(id);

const dom = {
  // Metrics
  inspectionCount: $('inspectionCount'),
  issueCount: $('issueCount'),
  repairCount: $('repairCount'),
  checkCount: $('checkCount'),

  // Health
  healthBadge: $('healthBadge'),
  healthDot: document.querySelector('.health-dot'),
  healthText: null, // set after init

  // Navigation
  nav: $('mainNav'),
  menuToggle: $('menuToggle'),
  navLinks: document.querySelectorAll('.nav-link'),

  // Inspection
  inspectionForm: $('inspectionForm'),
  websiteUrl: $('websiteUrl'),
  viewport: $('viewport'),
  demoSite: $('demoSite'),
  inspectBtn: $('inspectBtn'),
  notice: $('notice'),
  progressBar: $('progressBar'),

  // Issues
  issuesSection: $('issues'),
  issuesSummary: $('issuesSummary'),
  issueGrid: $('issueGrid'),

  // Sandbox
  cssEditor: $('cssEditor'),
  sandboxViewport: $('sandboxViewport'),
  evaluateBtn: $('evaluateBtn'),
  resetCssBtn: $('resetCssBtn'),
  sandboxNotice: $('sandboxNotice'),
  measurementsPanel: $('measurementsPanel'),
  measurementGrid: $('measurementGrid'),
  comparisonPanel: $('comparisonPanel'),
  comparisonContainer: $('comparisonContainer'),
  sandboxBeforeImg: $('sandboxBeforeImg'),
  sandboxAfterImg: $('sandboxAfterImg'),

  // Approval
  repairBtn: $('repairBtn'),
  repairStatus: $('repairStatus'),

  // Evidence
  timeline: $('timeline'),
  timelineEmpty: $('timelineEmpty'),
  screenshotCaption: $('screenshotCaption'),
  screenshotPlaceholder: $('screenshotPlaceholder'),
  inspectionScreenshot: $('inspectionScreenshot'),
  emptyHistory: $('emptyHistory'),
  historyList: $('historyList'),
  exportReportBtn: $('exportReportBtn'),
};


// ===== Utilities =====

function formatApiError(errorObj, fallback = 'Operation failed.') {
  if (!errorObj) return fallback;
  if (typeof errorObj === 'string') return errorObj;

  if (errorObj.detail) {
    if (typeof errorObj.detail === 'string') return errorObj.detail;
    if (Array.isArray(errorObj.detail)) {
      return errorObj.detail
        .map(item => {
          if (typeof item === 'string') return item;
          if (item && item.msg) {
            const loc = Array.isArray(item.loc)
              ? item.loc.filter(x => x !== 'body').join('.')
              : '';
            return loc ? `${loc}: ${item.msg}` : item.msg;
          }
          return JSON.stringify(item);
        })
        .join('; ');
    }
    if (typeof errorObj.detail === 'object') return JSON.stringify(errorObj.detail);
  }

  if (typeof errorObj.message === 'string' && errorObj.message) return errorObj.message;

  try { return JSON.stringify(errorObj); }
  catch { return fallback; }
}

function showNotice(el, message, type = 'info') {
  if (!el) { console.error(message); return; }
  el.className = `notice show ${type}`;
  el.textContent = message;
}

function hideNotice(el) {
  if (!el) return;
  el.className = 'notice';
  el.textContent = '';
}

function buildScreenshotUrl(data) {
  const screenshotPath = data.screenshot_url || data.screenshotUrl || data.screenshot;

  if (typeof screenshotPath !== 'string' || !screenshotPath.trim()) return null;

  let imageUrl;
  if (/^https?:\/\//i.test(screenshotPath)) {
    imageUrl = screenshotPath;
  } else {
    const normalizedPath = screenshotPath.replace(/\\/g, '/');
    const marker = '/screenshots/';
    const index = normalizedPath.toLowerCase().lastIndexOf(marker);

    if (index !== -1) {
      const filename = normalizedPath.slice(index + marker.length);
      imageUrl = API_BASE + '/screenshots/' +
        filename.split('/').map(encodeURIComponent).join('/');
    } else {
      imageUrl = API_BASE + screenshotPath;
    }
  }

  return imageUrl + (imageUrl.includes('?') ? '&' : '?') + 't=' + Date.now();
}

function timeNow() {
  return new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
}


// ===== Navigation =====

function initNavigation() {
  // Mobile menu toggle
  if (dom.menuToggle) {
    dom.menuToggle.addEventListener('click', () => {
      dom.menuToggle.classList.toggle('open');
      dom.nav.classList.toggle('open');
    });
  }

  // Close mobile nav on link click
  dom.navLinks.forEach(link => {
    link.addEventListener('click', () => {
      dom.menuToggle?.classList.remove('open');
      dom.nav?.classList.remove('open');

      // Update active link
      dom.navLinks.forEach(l => l.classList.remove('active'));
      link.classList.add('active');
    });
  });

  // Scroll spy
  const sections = document.querySelectorAll('.section[id]');
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const id = entry.target.id;
        dom.navLinks.forEach(l => {
          l.classList.toggle('active', l.getAttribute('href') === '#' + id);
        });
      }
    });
  }, { rootMargin: '-100px 0px -60% 0px' });

  sections.forEach(s => observer.observe(s));
}


// ===== Health Check =====

async function checkBackendHealth() {
  try {
    const res = await fetch(API_BASE + '/health', { cache: 'no-store' });
    if (res.ok) {
      if (dom.healthDot) dom.healthDot.className = 'health-dot connected';
      if (dom.healthBadge) {
        const textNode = dom.healthBadge.querySelector('.health-label');
        if (textNode) textNode.textContent = 'Connected';
      }
    } else {
      throw new Error('Status ' + res.status);
    }
  } catch {
    if (dom.healthDot) dom.healthDot.className = 'health-dot offline';
    if (dom.healthBadge) {
      const textNode = dom.healthBadge.querySelector('.health-label');
      if (textNode) textNode.textContent = 'Offline';
    }
  }
}


// ===== Timeline =====

function addTimelineEvent(text, type = 'info') {
  if (!dom.timeline) return;
  if (dom.timelineEmpty) dom.timelineEmpty.style.display = 'none';

  const event = document.createElement('div');
  event.className = 'timeline-event animate-in';

  event.innerHTML = `
    <span class="timeline-dot ${type}"></span>
    <div class="timeline-content">
      <div class="timeline-text">${text}</div>
      <div class="timeline-time">${timeNow()}</div>
    </div>
  `;

  dom.timeline.prepend(event);
}


// ===== History =====

function addHistoryItem(titleText, url, viewportText) {
  if (!dom.historyList || !dom.emptyHistory) return;

  const item = document.createElement('div');
  item.className = 'history-item animate-in';
  item.innerHTML = `
    <div class="history-title">${titleText || 'Website inspected'}</div>
    <div class="history-meta">${url || ''} · ${viewportText}</div>
    <span class="status-pill success">Success</span>
  `;

  dom.historyList.prepend(item);
  dom.emptyHistory.style.display = 'none';
  dom.historyList.hidden = false;
}


// ===== Screenshot Display =====

function updateScreenshot(data, fallbackUrl) {
  if (!dom.inspectionScreenshot || !dom.screenshotPlaceholder || !dom.screenshotCaption) return;

  const imageUrl = buildScreenshotUrl(data);
  if (!imageUrl) return;

  dom.inspectionScreenshot.hidden = true;
  dom.screenshotPlaceholder.style.display = 'block';
  dom.screenshotPlaceholder.textContent = 'Loading screenshot…';

  dom.inspectionScreenshot.onload = function () {
    dom.inspectionScreenshot.hidden = false;
    dom.screenshotPlaceholder.style.display = 'none';
  };

  dom.inspectionScreenshot.onerror = function () {
    dom.inspectionScreenshot.hidden = true;
    dom.screenshotPlaceholder.style.display = 'block';
    dom.screenshotPlaceholder.textContent = 'Screenshot could not load. Check the backend screenshot endpoint.';
  };

  dom.screenshotCaption.textContent = 'Screenshot: ' + (data.title || data.url || fallbackUrl);
  dom.inspectionScreenshot.src = imageUrl;

  // Store for sandbox before image
  state.lastScreenshotUrl = imageUrl;
}


// ===== Issue Detection =====

async function detectIssues(url, viewport) {
  if (dom.issueCount) dom.issueCount.textContent = '…';

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 35000);

  try {
    const response = await fetch(API_BASE + '/detect-issues', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, viewport }),
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    let result;
    try { result = await response.json(); }
    catch { throw new Error('Issue detection returned an invalid response.'); }

    if (!response.ok) {
      const detail = result.detail || result.message;
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail || 'Issue detection failed.'));
    }

    const issues = Array.isArray(result.issues) ? result.issues : [];
    const count = Number(result.issue_count ?? issues.length);

    if (!Number.isFinite(count)) throw new Error('Issue detection did not return a valid count.');

    if (dom.issueCount) dom.issueCount.textContent = String(count);
    state.issues = issues;

    // Render issue cards
    renderIssueCards(issues, result.detection_method || 'DOM heuristics');

    addTimelineEvent(`Detected ${count} issue${count === 1 ? '' : 's'} via ${result.detection_method || 'DOM heuristics'}`,
      count > 0 ? 'warning' : 'success');

    console.log('OmniSight issue detection result:', result);
    return result;

  } catch (error) {
    clearTimeout(timeoutId);
    console.warn('OmniSight issue detection unavailable:', error);
    if (dom.issueCount) dom.issueCount.textContent = '—';
    addTimelineEvent('Issue detection unavailable', 'error');
    return null;
  }
}


function renderIssueCards(issues, method) {
  if (!dom.issueGrid || !dom.issuesSection) return;

  if (!issues || issues.length === 0) {
    dom.issuesSection.hidden = true;
    return;
  }

  dom.issuesSection.hidden = false;
  if (dom.issuesSummary) {
    dom.issuesSummary.textContent = `${issues.length} issue${issues.length === 1 ? '' : 's'} detected · Method: ${method}`;
  }

  dom.issueGrid.innerHTML = '';

  issues.forEach(issue => {
    const card = document.createElement('div');
    card.className = 'issue-card animate-in';

    // Determine badge type
    let badgeClass = 'overflow';
    if (issue.type === 'positioning') badgeClass = 'position';
    else if (issue.type === 'oversized-button') badgeClass = 'oversized';
    else if (issue.type === 'page-horizontal-overflow') badgeClass = 'page';

    let typeLabel = issue.type || 'unknown';
    typeLabel = typeLabel.replace(/-/g, ' ');

    let dimsHtml = '';
    if (issue.width != null || issue.parent_width != null) {
      dimsHtml = '<div class="issue-dims">';
      if (issue.width != null) dimsHtml += `<span><span class="dim-label">Width:</span> ${issue.width}px</span>`;
      if (issue.parent_width != null) dimsHtml += `<span><span class="dim-label">Parent:</span> ${issue.parent_width}px</span>`;
      dimsHtml += '</div>';
    }

    let textHtml = '';
    if (issue.text) {
      textHtml = `<div class="issue-text">"${issue.text}"</div>`;
    }

    card.innerHTML = `
      <div class="issue-card-header">
        <span class="issue-type-badge ${badgeClass}">${typeLabel}</span>
        <span class="issue-element">&lt;${issue.element || 'unknown'}&gt;</span>
      </div>
      <div class="issue-desc">${issue.description || 'No description available.'}</div>
      ${textHtml}
      ${dimsHtml}
    `;

    dom.issueGrid.appendChild(card);
  });
}


// ===== Inspection Flow =====

async function handleInspection(event) {
  event.preventDefault();

  if (state.isInspecting) return;

  const url = dom.websiteUrl.value.trim();
  const selectedViewport = dom.viewport.value;
  const selectedOption = dom.viewport.options[dom.viewport.selectedIndex];
  const viewportText = selectedOption ? selectedOption.text : selectedViewport;

  // Validate URL
  if (!url) {
    showNotice(dom.notice, 'Please enter a website URL.', 'error');
    return;
  }

  let parsedUrl;
  try {
    parsedUrl = new URL(url);
    if (!['http:', 'https:'].includes(parsedUrl.protocol)) {
      throw new Error('Unsupported protocol.');
    }
  } catch {
    showNotice(dom.notice, 'Please enter a valid URL, such as https://example.com', 'error');
    return;
  }

  // Begin inspection
  state.isInspecting = true;
  state.checks++;
  if (dom.checkCount) dom.checkCount.textContent = state.checks;

  document.body.dataset.inspecting = 'true';
  dom.inspectBtn.disabled = true;
  dom.inspectBtn.innerHTML = '<span class="pulse">⏳</span> Inspecting…';
  if (dom.progressBar) dom.progressBar.hidden = false;
  showNotice(dom.notice, 'Connecting to backend — capturing screenshot…', 'info');
  addTimelineEvent(`Inspecting ${parsedUrl.hostname}${parsedUrl.pathname} at ${viewportText}`, 'info');

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 35000);

  try {
    const response = await fetch(API_BASE + '/inspect-browser', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: parsedUrl.href, viewport: selectedViewport }),
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    let data;
    try { data = await response.json(); }
    catch { throw new Error('Backend returned an invalid response. Check FastAPI logs.'); }

    if (!response.ok || data.status !== 'success') {
      const detail = data.detail || data.message;
      throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail || 'Inspection failed.'));
    }

    // Success
    state.inspections++;
    state.lastInspectionUrl = parsedUrl.href;
    state.lastInspectionViewport = selectedViewport;
    if (dom.inspectionCount) dom.inspectionCount.textContent = state.inspections;

    addHistoryItem(data.title || parsedUrl.href, data.url || parsedUrl.href, viewportText);
    updateScreenshot(data, parsedUrl.href);

    showNotice(dom.notice,
      `Inspection complete — ${data.title || parsedUrl.href} · ${viewportText}`,
      'success');

    addTimelineEvent(`Inspection successful: ${data.title || parsedUrl.hostname}`, 'success');

    console.log('OmniSight inspection result:', data);

    // Re-enable button before running detection
    dom.inspectBtn.disabled = false;
    dom.inspectBtn.innerHTML = '<span class="btn-icon">▶</span> Inspect Website';
    if (dom.progressBar) dom.progressBar.hidden = true;

    // Issue detection runs async — its failure doesn't fail the inspection
    await detectIssues(parsedUrl.href, selectedViewport);

  } catch (error) {
    clearTimeout(timeoutId);
    console.error('OmniSight inspection error:', error);

    let message = error.message || 'An unexpected error occurred.';
    if (error.name === 'AbortError') {
      message = 'Request timed out. The backend or target website took too long to respond.';
    } else if (error instanceof TypeError) {
      message = 'Cannot connect to backend. Ensure FastAPI is running at ' + API_BASE;
    }

    showNotice(dom.notice, message, 'error');
    addTimelineEvent('Inspection failed: ' + message, 'error');

  } finally {
    state.isInspecting = false;
    document.body.dataset.inspecting = 'false';
    dom.inspectBtn.disabled = false;
    dom.inspectBtn.innerHTML = '<span class="btn-icon">▶</span> Inspect Website';
    if (dom.progressBar) dom.progressBar.hidden = true;
  }
}


// ===== Sandbox Evaluation =====

async function handleSandboxEvaluate() {
  if (state.isEvaluating) return;

  const css = dom.cssEditor?.value.trim();
  if (!css) {
    showNotice(dom.sandboxNotice, 'Enter CSS to evaluate.', 'warning');
    return;
  }

  // Determine URL: use last inspected URL or current URL input
  const url = state.lastInspectionUrl || dom.websiteUrl?.value.trim();
  if (!url) {
    showNotice(dom.sandboxNotice, 'Run an inspection first, or enter a URL above.', 'warning');
    return;
  }

  const viewport = dom.sandboxViewport?.value || '375x812';

  state.isEvaluating = true;
  dom.evaluateBtn.disabled = true;
  dom.evaluateBtn.innerHTML = '<span class="pulse">⏳</span> Evaluating…';
  showNotice(dom.sandboxNotice, 'Launching isolated browser and applying candidate CSS…', 'info');
  addTimelineEvent('Evaluating CSS candidate in sandbox', 'info');

  try {
    const response = await fetch(API_BASE + '/sandbox-evaluate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, viewport, css })
    });

    let result;
    try { result = await response.json(); }
    catch { throw new Error('Sandbox returned an invalid response.'); }

    if (!response.ok) {
      throw new Error(formatApiError(result, 'Sandbox evaluation failed with HTTP ' + response.status));
    }

    if (result.status === 'error') {
      throw new Error(result.message || 'Candidate evaluation failed.');
    }

    // Render measurements
    if (result.measurements) {
      renderMeasurements(result.measurements);
    }

    // Render comparison
    const afterUrl = buildScreenshotUrl(result);
    if (afterUrl && dom.comparisonPanel) {
      dom.comparisonPanel.hidden = false;

      // Before image: use the last inspection screenshot
      if (state.lastScreenshotUrl && dom.sandboxBeforeImg) {
        dom.sandboxBeforeImg.src = state.lastScreenshotUrl;
      }

      // After image: sandbox result
      if (dom.sandboxAfterImg) {
        dom.sandboxAfterImg.src = afterUrl;
      }
    }

    showNotice(dom.sandboxNotice, 'Candidate evaluated. Review measurements and screenshots below.', 'success');
    addTimelineEvent('Sandbox evaluation complete — review comparison', 'success');

    console.log('OmniSight sandbox result:', result);

  } catch (error) {
    console.error('OmniSight sandbox error:', error);
    let message = error.message || 'Sandbox evaluation failed.';
    if (error instanceof TypeError) {
      message = 'Cannot connect to backend. Ensure FastAPI is running at ' + API_BASE;
    }
    showNotice(dom.sandboxNotice, message, 'error');
    addTimelineEvent('Sandbox evaluation failed: ' + message, 'error');

  } finally {
    state.isEvaluating = false;
    dom.evaluateBtn.disabled = false;
    dom.evaluateBtn.innerHTML = '<span class="btn-icon">⧫</span> Evaluate Candidate';
  }
}


function renderMeasurements(measurements) {
  if (!dom.measurementsPanel || !dom.measurementGrid) return;
  dom.measurementsPanel.hidden = false;
  dom.measurementGrid.innerHTML = '';

  const items = [
    {
      label: 'Horizontal Overflow',
      value: measurements.horizontal_overflow,
      display: measurements.horizontal_overflow ? 'Detected' : 'None',
      className: measurements.horizontal_overflow ? 'fail' : 'pass'
    },
    {
      label: 'Vertical Overflow',
      value: measurements.vertical_overflow,
      display: measurements.vertical_overflow ? 'Detected' : 'None',
      className: measurements.vertical_overflow ? 'fail' : 'pass'
    },
  ];

  if (measurements.bounding_box) {
    const bb = measurements.bounding_box;
    items.push({
      label: 'Offending Element',
      display: `${Math.round(bb.width)}×${Math.round(bb.height)} @ (${Math.round(bb.x)}, ${Math.round(bb.y)})`,
      className: 'info'
    });
  }

  items.forEach(item => {
    const el = document.createElement('div');
    el.className = 'measurement-item';
    el.innerHTML = `
      <span class="measurement-label">${item.label}</span>
      <span class="measurement-value ${item.className}">${item.display}</span>
    `;
    dom.measurementGrid.appendChild(el);
  });
}


// ===== Approved Repair =====

async function handleApprovedRepair() {
  if (state.isRepairing) return;

  let websiteUrl = dom.websiteUrl?.value.trim() || '';
  if (!websiteUrl) {
    if (dom.repairStatus) {
      dom.repairStatus.textContent = 'Enter a website URL first.';
      dom.repairStatus.className = 'repair-status error';
    }
    return;
  }

  // Ensure valid protocol
  if (!/^https?:\/\//i.test(websiteUrl)) {
    if (websiteUrl.startsWith('127.0.0.1') || websiteUrl.startsWith('localhost')) {
      websiteUrl = 'http://' + websiteUrl;
      if (dom.websiteUrl) dom.websiteUrl.value = websiteUrl;
    } else {
      if (dom.repairStatus) {
        dom.repairStatus.textContent = 'Please enter a valid HTTP or HTTPS URL.';
        dom.repairStatus.className = 'repair-status error';
      }
      return;
    }
  }

  state.isRepairing = true;
  dom.repairBtn.disabled = true;
  document.body.dataset.inspecting = 'true';

  try {
    // Step 1: Capture baseline if needed
    const needsBaseline = !state.lastScreenshotUrl;
    if (needsBaseline) {
      if (dom.repairStatus) {
        dom.repairStatus.textContent = 'Capturing baseline screenshot…';
        dom.repairStatus.className = 'repair-status pending';
      }
      addTimelineEvent('Capturing baseline screenshot before repair', 'info');

      const inspectRes = await fetch(API_BASE + '/inspect-browser', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: websiteUrl, viewport: '1366x768' })
      });

      let inspectData = {};
      try { inspectData = await inspectRes.json(); } catch { inspectData = {}; }

      if (!inspectRes.ok || inspectData.status !== 'success') {
        throw new Error(formatApiError(inspectData, 'Could not capture baseline screenshot.'));
      }

      const baselineUrl = buildScreenshotUrl(inspectData);
      if (baselineUrl) state.lastScreenshotUrl = baselineUrl;
    }

    // Step 2: Apply approved repair
    if (dom.repairStatus) {
      dom.repairStatus.textContent = 'Applying approved CSS repair in Playwright…';
      dom.repairStatus.className = 'repair-status pending';
    }
    addTimelineEvent('Sending approved repair request', 'info');

    const repairRes = await fetch(API_BASE + '/repair-ui', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: websiteUrl, approved: true })
    });

    let repairData = {};
    try { repairData = await repairRes.json(); } catch { repairData = {}; }

    if (!repairRes.ok) {
      throw new Error(formatApiError(repairData, 'Repair request failed with HTTP ' + repairRes.status));
    }

    // Step 3: Update comparison
    const repairScreenshotUrl = buildScreenshotUrl(repairData);
    if (repairScreenshotUrl && dom.comparisonPanel) {
      dom.comparisonPanel.hidden = false;
      if (state.lastScreenshotUrl && dom.sandboxBeforeImg) {
        dom.sandboxBeforeImg.src = state.lastScreenshotUrl;
      }
      if (dom.sandboxAfterImg) {
        dom.sandboxAfterImg.src = repairScreenshotUrl;
      }
    }

    if (repairData.status === 'success') {
      state.repairs++;
      if (dom.repairCount) dom.repairCount.textContent = state.repairs;

      const msg = (repairData.message || 'Repair applied.') +
        ' (Session-only — original files unchanged.)';
      if (dom.repairStatus) {
        dom.repairStatus.textContent = '✓ ' + msg;
        dom.repairStatus.className = 'repair-status success';
      }
      showNotice(dom.notice, 'Repair applied! ' + (repairData.message || ''), 'success');
      addTimelineEvent('Repair applied successfully (session-scoped)', 'success');

    } else {
      const msg = repairData.message || 'No repairable element found on target page.';
      if (dom.repairStatus) {
        dom.repairStatus.textContent = 'ℹ ' + msg;
        dom.repairStatus.className = 'repair-status';
      }
      showNotice(dom.notice, msg, 'warning');
      addTimelineEvent('Repair not applied: ' + msg, 'warning');
    }

  } catch (error) {
    console.error('OmniSight repair error:', error);

    let errorMessage = 'An unexpected error occurred.';
    if (error instanceof TypeError) {
      errorMessage = 'Cannot connect to backend. Ensure FastAPI is running at ' + API_BASE;
    } else if (error instanceof Error) {
      errorMessage = error.message;
    } else {
      errorMessage = formatApiError(error);
    }

    if (dom.repairStatus) {
      dom.repairStatus.textContent = 'Repair failed: ' + errorMessage;
      dom.repairStatus.className = 'repair-status error';
    }
    showNotice(dom.notice, 'Repair failed: ' + errorMessage, 'error');
    addTimelineEvent('Repair failed: ' + errorMessage, 'error');

  } finally {
    state.isRepairing = false;
    document.body.dataset.inspecting = 'false';
    dom.repairBtn.disabled = false;
  }
}


// ===== Report Export =====

function exportReport() {
  const now = new Date().toISOString();
  const issues = state.issues || [];

  let issueRows = '';
  if (issues.length === 0) {
    issueRows = '<tr><td colspan="4" style="text-align:center;color:#888;">No issues detected in this session.</td></tr>';
  } else {
    issues.forEach((issue, i) => {
      issueRows += `<tr>
        <td>${i + 1}</td>
        <td><code>${issue.type || 'unknown'}</code></td>
        <td><code>&lt;${issue.element || '?'}&gt;</code></td>
        <td>${issue.description || '—'}</td>
      </tr>`;
    });
  }

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>OmniSight Inspection Report — ${now}</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #1a1a2e; }
    h1 { font-size: 24px; border-bottom: 2px solid #6366f1; padding-bottom: 8px; }
    h2 { font-size: 18px; margin-top: 32px; color: #6366f1; }
    table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    th, td { padding: 10px 12px; border: 1px solid #e0e0e0; text-align: left; font-size: 14px; }
    th { background: #f8f9fa; font-weight: 600; }
    code { background: #f0f0f5; padding: 2px 6px; border-radius: 3px; font-size: 13px; }
    .meta { color: #666; font-size: 13px; margin-top: 4px; }
    .footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #e0e0e0; color: #888; font-size: 12px; }
    .stat { display: inline-block; margin-right: 24px; }
    .stat strong { color: #1a1a2e; }
    img { max-width: 100%; border: 1px solid #e0e0e0; border-radius: 4px; margin-top: 8px; }
  </style>
</head>
<body>
  <h1>OmniSight Inspection Report</h1>
  <p class="meta">Generated: ${now}</p>

  <h2>Session Summary</h2>
  <p>
    <span class="stat"><strong>${state.inspections}</strong> Inspections</span>
    <span class="stat"><strong>${issues.length}</strong> Issues Detected</span>
    <span class="stat"><strong>${state.repairs}</strong> Repairs Applied</span>
    <span class="stat"><strong>${state.checks}</strong> Total Checks</span>
  </p>
  ${state.lastInspectionUrl ? `<p class="meta">Last inspected: <code>${state.lastInspectionUrl}</code> · Viewport: <code>${state.lastInspectionViewport}</code></p>` : ''}

  <h2>Detected Issues</h2>
  <table>
    <thead><tr><th>#</th><th>Type</th><th>Element</th><th>Description</th></tr></thead>
    <tbody>${issueRows}</tbody>
  </table>

  ${state.lastScreenshotUrl ? `
  <h2>Latest Screenshot</h2>
  <img src="${state.lastScreenshotUrl}" alt="Inspection screenshot">
  ` : ''}

  <div class="footer">
    <p>OmniSight — Visual QA & Safe UI Repair · Report generated from live session data.</p>
  </div>
</body>
</html>`;

  const blob = new Blob([html], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `omnisight-report-${Date.now()}.html`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  addTimelineEvent('Report exported', 'success');
}


// ===== Demo Site Selector =====

function handleDemoSiteChange() {
  if (!dom.demoSite || !dom.websiteUrl) return;

  if (dom.demoSite.value === 'shophub') {
    if (window.location.protocol === 'file:') {
      dom.websiteUrl.value = 'http://127.0.0.1:8000/frontend/store.html';
    } else {
      dom.websiteUrl.value = new URL('store.html', window.location.href).href;
    }
  }
}


// ===== Initialization =====

function init() {
  console.log('OmniSight dashboard loaded.');

  initNavigation();

  // Health check
  checkBackendHealth();
  setInterval(checkBackendHealth, 10000);

  // Inspection form
  if (dom.inspectionForm) {
    dom.inspectionForm.addEventListener('submit', handleInspection);
  }

  // Demo site selector
  if (dom.demoSite) {
    dom.demoSite.addEventListener('change', handleDemoSiteChange);
  }

  // Sandbox
  if (dom.evaluateBtn) {
    dom.evaluateBtn.addEventListener('click', handleSandboxEvaluate);
  }

  if (dom.resetCssBtn) {
    dom.resetCssBtn.addEventListener('click', () => {
      if (dom.cssEditor) dom.cssEditor.value = '';
      hideNotice(dom.sandboxNotice);
      if (dom.measurementsPanel) dom.measurementsPanel.hidden = true;
      if (dom.comparisonPanel) dom.comparisonPanel.hidden = true;
      addTimelineEvent('Sandbox CSS reset', 'info');
    });
  }

  // Approved repair
  if (dom.repairBtn) {
    dom.repairBtn.addEventListener('click', handleApprovedRepair);
  }

  // Report export
  if (dom.exportReportBtn) {
    dom.exportReportBtn.addEventListener('click', exportReport);
  }

  // Default URL
  if (dom.websiteUrl && !dom.websiteUrl.value.trim()) {
    dom.websiteUrl.value = 'https://example.com';
  }
}

// Start
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
