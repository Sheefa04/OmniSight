
/* ==========================================================
   OmniSight — Application Logic
   Visual QA & Safe UI Repair Workspace
   Phase 3: Viewport-aware inspection and repair
   ========================================================== */
'use strict';

// ===== Live Server Reload Guard =====
if (window.WebSocket) {
  const OriginalWebSocket = window.WebSocket;

  window.WebSocket = function (...args) {
    const ws = new OriginalWebSocket(...args);
    let originalOnMessage = null;

    Object.defineProperty(ws, 'onmessage', {
      get() {
        return originalOnMessage;
      },
      set(fn) {
        originalOnMessage = function (event) {
          if (
            event &&
            event.data === 'reload' &&
            document.body.dataset.inspecting === 'true'
          ) {
            console.warn(
              'OmniSight: Live Server reload ignored during inspection.'
            );
            return;
          }

          if (typeof fn === 'function') {
            fn.call(this, event);
          }
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
  lastScreenshotViewport: '',
  isInspecting: false,
  isEvaluating: false,
  isRepairing: false
};

// ===== DOM References =====
const $ = id => document.getElementById(id);

const dom = {
  inspectionCount: $('inspectionCount') || $('websitesCount'),
  issueCount: $('issueCount') || $('issuesCount'),
  repairCount: $('repairCount') || $('repairsCount'),
  checkCount: $('checkCount') || $('checksCount'),

  healthBadge: $('healthBadge'),
  healthDot: document.querySelector('.health-dot'),
  healthText: null,

  nav: $('mainNav'),
  menuToggle: $('menuToggle'),
  navLinks: document.querySelectorAll('.nav-link'),

  inspectionForm: $('inspectionForm'),
  websiteUrl: $('websiteUrl'),
  viewport: $('viewport'),
  demoSite: $('demoSite'),
  inspectBtn: $('inspectBtn'),
  notice: $('notice'),
  progressBar: $('progressBar'),

  issuesSection: $('issues'),
  issuesSummary: $('issuesSummary'),
  issueGrid: $('issueGrid'),

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
  beforeRepairImage: $('beforeRepairImage'),
  afterRepairImage: $('afterRepairImage'),
  diffRepairImage: $('diffRepairImage'),
  diffPercentage: $('diffPercentage'),

  repairBtn: $('repairBtn') || $('repairButton'),
  repairStatus: $('repairStatus'),

  timeline: $('timeline'),
  timelineEmpty: $('timelineEmpty'),
  screenshotCaption: $('screenshotCaption'),
  screenshotPlaceholder: $('screenshotPlaceholder'),
  inspectionScreenshot: $('inspectionScreenshot'),
  emptyHistory: $('emptyHistory'),
  historyList: $('historyList'),
  exportReportBtn: $('exportReportBtn')
};

// ===== Utilities =====

function formatApiError(errorObj, fallback = 'Operation failed.') {
  if (!errorObj) return fallback;
  if (typeof errorObj === 'string') return errorObj;

  if (errorObj.detail) {
    if (typeof errorObj.detail === 'string') {
      return errorObj.detail;
    }

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

    if (typeof errorObj.detail === 'object') {
      return JSON.stringify(errorObj.detail);
    }
  }

  if (typeof errorObj.message === 'string' && errorObj.message) {
    return errorObj.message;
  }

  try {
    return JSON.stringify(errorObj);
  } catch {
    return fallback;
  }
}

function extractFilename(urlOrPath) {
  if (!urlOrPath || typeof urlOrPath !== 'string') return '';

  const clean = urlOrPath.split('?')[0].split('#')[0];
  const parts = clean.replace(/\\/g, '/').split('/');

  return parts.pop() || '';
}

function showNotice(el, message, type = 'info') {
  if (!el) {
    console.error(message);
    return;
  }

  el.className = `notice show ${type}`;
  el.textContent = message;
}

function hideNotice(el) {
  if (!el) return;

  el.className = 'notice';
  el.textContent = '';
}

function timeNow() {
  return new Date().toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  });
}

function normalizeHttpUrl(value) {
  let input = (value || '').trim();

  if (!input) {
    throw new Error('Please enter a website URL first.');
  }

  if (
    !/^https?:\/\//i.test(input) &&
    /^(localhost|127\.0\.0\.1)(:\d+)?(\/|$)/i.test(input)
  ) {
    input = 'http://' + input;
  }

  let parsed;

  try {
    parsed = new URL(input);
  } catch {
    throw new Error(
      'Please enter a valid HTTP or HTTPS URL, such as https://example.com.'
    );
  }

  if (!['http:', 'https:'].includes(parsed.protocol)) {
    throw new Error('Only HTTP and HTTPS URLs are supported.');
  }

  return parsed.href;
}

function buildScreenshotUrl(data) {
  const screenshotPath =
    data?.screenshot_url ||
    data?.screenshotUrl ||
    data?.screenshot;

  if (
    typeof screenshotPath !== 'string' ||
    !screenshotPath.trim()
  ) {
    return null;
  }

  let imageUrl;

  if (/^https?:\/\//i.test(screenshotPath)) {
    imageUrl = screenshotPath;
  } else {
    const normalizedPath = screenshotPath.replace(/\\/g, '/');
    const marker = '/screenshots/';
    const index = normalizedPath.toLowerCase().lastIndexOf(marker);

    if (index !== -1) {
      const filename = normalizedPath.slice(index + marker.length);

      imageUrl =
        API_BASE +
        '/screenshots/' +
        filename.split('/').map(encodeURIComponent).join('/');
    } else {
      const path = normalizedPath.startsWith('/')
        ? normalizedPath
        : '/' + normalizedPath;

      imageUrl = API_BASE + path;
    }
  }

  return imageUrl + (imageUrl.includes('?') ? '&' : '?') + 't=' + Date.now();
}

function setRepairStatus(message, type = '') {
  if (!dom.repairStatus) return;

  dom.repairStatus.textContent = message;
  dom.repairStatus.className = 'repair-status' + (type ? ' ' + type : '');
}

async function readJsonResponse(response, fallbackMessage) {
  let data;

  try {
    data = await response.json();
  } catch {
    throw new Error(fallbackMessage + ' Backend returned invalid JSON.');
  }

  if (!response.ok) {
    throw new Error(
      formatApiError(
        data,
        `${fallbackMessage} HTTP ${response.status}`
      )
    );
  }

  return data;
}

// ===== Navigation =====

function initNavigation() {
  if (dom.menuToggle) {
    dom.menuToggle.addEventListener('click', () => {
      dom.menuToggle.classList.toggle('open');
      dom.nav?.classList.toggle('open');
    });
  }

  dom.navLinks.forEach(link => {
    link.addEventListener('click', () => {
      dom.menuToggle?.classList.remove('open');
      dom.nav?.classList.remove('open');

      dom.navLinks.forEach(item => item.classList.remove('active'));
      link.classList.add('active');
    });
  });

  const sections = document.querySelectorAll('.section[id]');

  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;

        const id = entry.target.id;

        dom.navLinks.forEach(link => {
          link.classList.toggle(
            'active',
            link.getAttribute('href') === '#' + id
          );
        });
      });
    }, { rootMargin: '-100px 0px -60% 0px' });

    sections.forEach(section => observer.observe(section));
  }
}

// ===== Health Check =====

async function checkBackendHealth() {
  try {
    const response = await fetch(API_BASE + '/health', {
      cache: 'no-store'
    });

    if (!response.ok) {
      throw new Error('Backend returned status ' + response.status);
    }

    if (dom.healthDot) {
      dom.healthDot.className = 'health-dot connected';
    }

    if (dom.healthBadge) {
      const label = dom.healthBadge.querySelector('.health-label');
      if (label) label.textContent = 'Connected';
    }
  } catch {
    if (dom.healthDot) {
      dom.healthDot.className = 'health-dot offline';
    }

    if (dom.healthBadge) {
      const label = dom.healthBadge.querySelector('.health-label');
      if (label) label.textContent = 'Offline';
    }
  }
}

// ===== Timeline =====

function addTimelineEvent(message, type = 'info') {
  if (!dom.timeline) return;

  if (dom.timelineEmpty) {
    dom.timelineEmpty.style.display = 'none';
  }

  const event = document.createElement('div');
  event.className = 'timeline-event animate-in';

  const dot = document.createElement('span');
  dot.className = `timeline-dot ${type}`;

  const content = document.createElement('div');
  content.className = 'timeline-content';

  const text = document.createElement('div');
  text.className = 'timeline-text';
  text.textContent = message;

  const time = document.createElement('div');
  time.className = 'timeline-time';
  time.textContent = timeNow();

  content.append(text, time);
  event.append(dot, content);
  dom.timeline.prepend(event);
}

// ===== History =====

function addHistoryItem(titleText, url, viewportText) {
  if (!dom.historyList || !dom.emptyHistory) return;

  const item = document.createElement('div');
  item.className = 'history-item animate-in';

  const title = document.createElement('div');
  title.className = 'history-title';
  title.textContent = titleText || 'Website inspected';

  const meta = document.createElement('div');
  meta.className = 'history-meta';
  meta.textContent = `${url || ''} · ${viewportText || ''}`;

  const badge = document.createElement('span');
  badge.className = 'status-pill success';
  badge.textContent = 'Success';

  item.append(title, meta, badge);
  dom.historyList.prepend(item);

  dom.emptyHistory.style.display = 'none';
  dom.historyList.hidden = false;
}

// ===== Screenshot Display =====

function updateScreenshot(data, fallbackUrl) {
  const imageUrl = buildScreenshotUrl(data);

  if (!imageUrl) return;

  // Keep the screenshot URL and viewport together.
  state.lastScreenshotUrl = imageUrl;
  state.lastScreenshotViewport =
    data?.viewport_key ||
    state.lastInspectionViewport ||
    '';

  if (
    !dom.inspectionScreenshot ||
    !dom.screenshotPlaceholder ||
    !dom.screenshotCaption
  ) {
    return;
  }

  dom.inspectionScreenshot.hidden = true;
  dom.screenshotPlaceholder.style.display = 'block';
  dom.screenshotPlaceholder.textContent = 'Loading screenshot…';

  dom.inspectionScreenshot.onload = () => {
    dom.inspectionScreenshot.hidden = false;
    dom.screenshotPlaceholder.style.display = 'none';
  };

  dom.inspectionScreenshot.onerror = () => {
    dom.inspectionScreenshot.hidden = true;
    dom.screenshotPlaceholder.style.display = 'block';
    dom.screenshotPlaceholder.textContent =
      'Screenshot could not load. Check the backend screenshot endpoint.';
  };

  dom.screenshotCaption.textContent =
    'Screenshot: ' + (data.title || data.url || fallbackUrl || '');

  dom.inspectionScreenshot.src = imageUrl;
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

    const result = await readJsonResponse(
      response,
      'Issue detection failed.'
    );

    const issues = Array.isArray(result.issues) ? result.issues : [];
    const count = Number(result.issue_count ?? issues.length);

    if (!Number.isFinite(count)) {
      throw new Error('Issue detection returned an invalid issue count.');
    }

    state.issues = issues;

    if (dom.issueCount) {
      dom.issueCount.textContent = String(count);
    }

    renderIssueCards(
      issues,
      result.detection_method || 'DOM heuristics'
    );

    addTimelineEvent(
      `Detected ${count} issue${count === 1 ? '' : 's'} via ${result.detection_method || 'DOM heuristics'}`,
      count > 0 ? 'warning' : 'success'
    );

    console.log('OmniSight issue detection result:', result);
    return result;

  } catch (error) {
    console.warn('OmniSight issue detection unavailable:', error);

    if (dom.issueCount) dom.issueCount.textContent = '—';

    addTimelineEvent(
      'Issue detection unavailable: ' + error.message,
      'error'
    );

    return null;

  } finally {
    clearTimeout(timeoutId);
  }
}

function renderIssueCards(issues, method) {
  if (!dom.issueGrid || !dom.issuesSection) return;

  if (!issues || issues.length === 0) {
    dom.issuesSection.hidden = true;
    if (dom.issueGrid) dom.issueGrid.replaceChildren();
    return;
  }

  dom.issuesSection.hidden = false;

  if (dom.issuesSummary) {
    dom.issuesSummary.textContent =
      `${issues.length} issue${issues.length === 1 ? '' : 's'} detected · Method: ${method}`;
  }

  dom.issueGrid.replaceChildren();

  issues.forEach(issue => {
    const card = document.createElement('div');
    card.className = 'issue-card animate-in';

    let badgeClass = 'overflow';

    if (issue.type === 'positioning') badgeClass = 'position';
    else if (issue.type === 'oversized-button') badgeClass = 'oversized';
    else if (issue.type === 'page-horizontal-overflow') badgeClass = 'page';

    const header = document.createElement('div');
    header.className = 'issue-card-header';

    const badge = document.createElement('span');
    badge.className = `issue-type-badge ${badgeClass}`;
    badge.textContent = String(issue.type || 'unknown').replace(/-/g, ' ');

    const element = document.createElement('span');
    element.className = 'issue-element';
    element.textContent = `<${issue.element || 'unknown'}>`;

    header.append(badge, element);

    const description = document.createElement('div');
    description.className = 'issue-desc';
    description.textContent = issue.description || 'No description available.';

    card.append(header, description);

    if (issue.text) {
      const text = document.createElement('div');
      text.className = 'issue-text';
      text.textContent = `"${issue.text}"`;
      card.appendChild(text);
    }

    if (issue.width != null || issue.parent_width != null) {
      const dims = document.createElement('div');
      dims.className = 'issue-dims';

      if (issue.width != null) {
        const width = document.createElement('span');
        width.textContent = `Width: ${issue.width}px`;
        dims.appendChild(width);
      }

      if (issue.parent_width != null) {
        const parent = document.createElement('span');
        parent.textContent = `Parent: ${issue.parent_width}px`;
        dims.appendChild(parent);
      }

      card.appendChild(dims);
    }

    dom.issueGrid.appendChild(card);
  });
}

// ===== Inspection Flow =====

async function handleInspection(event) {
  event.preventDefault();

  if (state.isInspecting) return;

  let parsedUrl;

  try {
    parsedUrl = new URL(normalizeHttpUrl(dom.websiteUrl?.value));
  } catch (error) {
    showNotice(dom.notice, error.message, 'error');
    return;
  }

  if (dom.websiteUrl) dom.websiteUrl.value = parsedUrl.href;

  const selectedViewport = dom.viewport?.value || '375x812';
  const selectedOption = dom.viewport?.options[dom.viewport.selectedIndex];
  const viewportText = selectedOption
    ? selectedOption.text
    : selectedViewport;

  state.isInspecting = true;
  state.checks++;

  if (dom.checkCount) {
    dom.checkCount.textContent = state.checks;
  }

  document.body.dataset.inspecting = 'true';

  if (dom.inspectBtn) {
    dom.inspectBtn.disabled = true;
    dom.inspectBtn.textContent = 'Inspecting…';
  }

  if (dom.progressBar) dom.progressBar.hidden = false;

  showNotice(
    dom.notice,
    'Connecting to backend — capturing screenshot…',
    'info'
  );

  addTimelineEvent(
    `Inspecting ${parsedUrl.hostname}${parsedUrl.pathname} at ${viewportText}`,
    'info'
  );

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 35000);

  try {
    const response = await fetch(API_BASE + '/inspect-browser', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: parsedUrl.href,
        viewport: selectedViewport
      }),
      signal: controller.signal
    });

    const data = await readJsonResponse(
      response,
      'Inspection failed.'
    );

    if (data.status !== 'success') {
      throw new Error(
        formatApiError(data, 'Inspection did not complete successfully.')
      );
    }

    state.inspections++;
    state.lastInspectionUrl = parsedUrl.href;
    state.lastInspectionViewport =
      data.viewport_key || selectedViewport;

    if (dom.inspectionCount) {
      dom.inspectionCount.textContent = state.inspections;
    }

    addHistoryItem(
      data.title || parsedUrl.href,
      data.url || parsedUrl.href,
      viewportText
    );

    updateScreenshot(data, parsedUrl.href);

    showNotice(
      dom.notice,
      `Inspection complete — ${data.title || parsedUrl.href} · ${viewportText}`,
      'success'
    );

    addTimelineEvent(
      `Inspection successful: ${data.title || parsedUrl.hostname}`,
      'success'
    );

    console.log('OmniSight inspection result:', data);

    // Detection is separate: its failure should not erase the inspection.
    await detectIssues(parsedUrl.href, selectedViewport);

  } catch (error) {
    console.error('OmniSight inspection error:', error);

    let message = error.message || 'An unexpected error occurred.';

    if (error.name === 'AbortError') {
      message = 'Inspection timed out. Check the backend and target website.';
    } else if (error instanceof TypeError) {
      message = 'Cannot connect to backend. Ensure FastAPI is running at ' + API_BASE;
    }

    showNotice(dom.notice, message, 'error');
    addTimelineEvent('Inspection failed: ' + message, 'error');

  } finally {
    clearTimeout(timeoutId);

    state.isInspecting = false;
    document.body.dataset.inspecting = 'false';

    if (dom.inspectBtn) {
      dom.inspectBtn.disabled = false;
      dom.inspectBtn.innerHTML =
        '<span class="btn-icon">▶</span> Inspect Website';
    }

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

  const url = state.lastInspectionUrl || dom.websiteUrl?.value.trim();

  if (!url) {
    showNotice(
      dom.sandboxNotice,
      'Run an inspection first, or enter a URL above.',
      'warning'
    );
    return;
  }

  const viewport = dom.sandboxViewport?.value || '375x812';

  state.isEvaluating = true;

  if (dom.evaluateBtn) {
    dom.evaluateBtn.disabled = true;
    dom.evaluateBtn.textContent = 'Evaluating…';
  }

  showNotice(
    dom.sandboxNotice,
    'Launching isolated browser and applying candidate CSS…',
    'info'
  );

  addTimelineEvent('Evaluating CSS candidate in sandbox', 'info');

  try {
    const response = await fetch(API_BASE + '/sandbox-evaluate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, viewport, css })
    });

    const result = await readJsonResponse(
      response,
      'Sandbox evaluation failed.'
    );

    if (result.status === 'error') {
      throw new Error(result.message || 'Candidate evaluation failed.');
    }

    if (result.measurements) {
      renderMeasurements(result.measurements);
    }

    const afterUrl = buildScreenshotUrl(result);

    if (afterUrl && dom.comparisonPanel) {
      dom.comparisonPanel.hidden = false;

      if (state.lastScreenshotUrl && dom.beforeRepairImage) {
        dom.beforeRepairImage.src = state.lastScreenshotUrl;
        dom.beforeRepairImage.style.display = 'block';
      }

      if (dom.afterRepairImage) {
        dom.afterRepairImage.src = afterUrl;
        dom.afterRepairImage.style.display = 'block';
      }
    }

    showNotice(
      dom.sandboxNotice,
      'Candidate evaluated. Review measurements and screenshots below.',
      'success'
    );

    addTimelineEvent('Sandbox evaluation complete', 'success');
    console.log('OmniSight sandbox result:', result);

  } catch (error) {
    console.error('OmniSight sandbox error:', error);

    const message = error instanceof TypeError
      ? 'Cannot connect to backend. Ensure FastAPI is running at ' + API_BASE
      : error.message || 'Sandbox evaluation failed.';

    showNotice(dom.sandboxNotice, message, 'error');
    addTimelineEvent('Sandbox evaluation failed: ' + message, 'error');

  } finally {
    state.isEvaluating = false;

    if (dom.evaluateBtn) {
      dom.evaluateBtn.disabled = false;
      dom.evaluateBtn.innerHTML =
        '<span class="btn-icon">⧫</span> Evaluate Candidate';
    }
  }
}

function renderMeasurements(measurements) {
  if (!dom.measurementsPanel || !dom.measurementGrid) return;

  dom.measurementsPanel.hidden = false;
  dom.measurementGrid.replaceChildren();

  const items = [
    {
      label: 'Horizontal Overflow',
      display: measurements.horizontal_overflow ? 'Detected' : 'None',
      className: measurements.horizontal_overflow ? 'fail' : 'pass'
    },
    {
      label: 'Vertical Overflow',
      display: measurements.vertical_overflow ? 'Detected' : 'None',
      className: measurements.vertical_overflow ? 'fail' : 'pass'
    }
  ];

  if (measurements.bounding_box) {
    const bb = measurements.bounding_box;

    items.push({
      label: 'Offending Element',
      display:
        `${Math.round(bb.width)}×${Math.round(bb.height)} @ (${Math.round(bb.x)}, ${Math.round(bb.y)})`,
      className: 'info'
    });
  }

  items.forEach(item => {
    const el = document.createElement('div');
    el.className = 'measurement-item';

    const label = document.createElement('span');
    label.className = 'measurement-label';
    label.textContent = item.label;

    const value = document.createElement('span');
    value.className = `measurement-value ${item.className}`;
    value.textContent = item.display;

    el.append(label, value);
    dom.measurementGrid.appendChild(el);
  });
}

// ===== Approved Repair: Viewport-aware workflow =====

async function handleApprovedRepair() {
  if (state.isRepairing) return;

  let websiteUrl;

  try {
    websiteUrl = normalizeHttpUrl(dom.websiteUrl?.value);
  } catch (error) {
    setRepairStatus(error.message, 'error');
    showNotice(dom.notice, error.message, 'error');
    return;
  }

  if (dom.websiteUrl) {
    dom.websiteUrl.value = websiteUrl;
  }

  // Use the currently selected viewport, not a hardcoded desktop viewport.
  const repairViewport =
    dom.viewport?.value ||
    state.lastInspectionViewport ||
    '1366x768';

  state.isRepairing = true;

  if (dom.repairBtn) dom.repairBtn.disabled = true;

  document.body.dataset.inspecting = 'true';

  let repairWasSuccessful = false;

  try {
    // Step 1: Reuse a baseline only when URL and viewport both match.
    let baselineMatches =
      Boolean(state.lastScreenshotUrl) &&
      state.lastInspectionUrl === websiteUrl &&
      state.lastScreenshotViewport === repairViewport;

    if (!baselineMatches) {
      setRepairStatus(
        `Capturing baseline at ${repairViewport}…`,
        'pending'
      );

      addTimelineEvent(
        `Capturing matching baseline screenshot at ${repairViewport}`,
        'info'
      );

      const baselineResponse = await fetch(
        API_BASE + '/capture-baseline',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            url: websiteUrl,
            viewport: repairViewport
          })
        }
      );

      const baselineData = await readJsonResponse(
        baselineResponse,
        'Could not capture baseline screenshot.'
      );

      const baselineUrl = buildScreenshotUrl(baselineData);

      if (!baselineUrl) {
        throw new Error(
          'Baseline endpoint did not return a usable screenshot URL.'
        );
      }

      const actualBaselineViewport =
        baselineData.viewport_key || repairViewport;

      if (actualBaselineViewport !== repairViewport) {
        throw new Error(
          `Baseline viewport mismatch: requested ${repairViewport}, received ${actualBaselineViewport}.`
        );
      }

      state.lastScreenshotUrl = baselineUrl;
      state.lastScreenshotViewport = actualBaselineViewport;
      state.lastInspectionUrl = websiteUrl;
      state.lastInspectionViewport = actualBaselineViewport;

      baselineMatches = true;
    }

    const originalScreenshotUrl = state.lastScreenshotUrl;
    const originalViewportKey = state.lastScreenshotViewport;

    if (!originalScreenshotUrl || !originalViewportKey) {
      throw new Error(
        'A valid baseline screenshot and viewport are required before repair.'
      );
    }

    // Step 2: Submit explicitly approved repair at the same viewport.
    setRepairStatus(
      `Applying approved repair at ${repairViewport}…`,
      'pending'
    );

    addTimelineEvent(
      `Submitting approved repair at ${repairViewport}`,
      'info'
    );

    const repairResponse = await fetch(API_BASE + '/repair-ui', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: websiteUrl,
        approved: true,
        viewport: repairViewport
      })
    });

    const repairData = await readJsonResponse(
      repairResponse,
      'Repair request failed.'
    );

    if (repairData.status !== 'success') {
      const message =
        repairData.message ||
        'No repair was applied by the backend.';

      setRepairStatus(message, 'error');
      showNotice(dom.notice, message, 'warning');
      addTimelineEvent('Repair not applied: ' + message, 'warning');
      return;
    }

    // The backend reports that the repair succeeded.
    repairWasSuccessful = true;

    const repairedScreenshotUrl = buildScreenshotUrl(repairData);
    const repairedViewportKey =
      repairData.viewport_key || repairViewport;

    // Record the repair outcome independently of comparison.
    state.repairs++;

    if (dom.repairCount) {
      dom.repairCount.textContent = String(state.repairs);
    }

    const repairMessage =
      (repairData.message || 'Repair applied successfully.') +
      ' Session-only repair: original website source files were not modified.';

    setRepairStatus('✓ ' + repairMessage, 'success');

    showNotice(
      dom.notice,
      'Repair applied successfully. Preparing screenshot comparison…',
      'success'
    );

    addTimelineEvent(
      `Repair applied at ${repairedViewportKey}`,
      'success'
    );

    // Step 3: Display before/after screenshots.
    if (dom.comparisonPanel) {
      dom.comparisonPanel.hidden = false;
    }

    if (dom.beforeRepairImage) {
      dom.beforeRepairImage.src = originalScreenshotUrl;
      dom.beforeRepairImage.style.display = 'block';
    }

    if (repairedScreenshotUrl && dom.afterRepairImage) {
      dom.afterRepairImage.src = repairedScreenshotUrl;
      dom.afterRepairImage.style.display = 'block';
    }

    // Step 4: Compare only screenshots captured at identical viewports.
    if (!repairedScreenshotUrl) {
      showNotice(
        dom.notice,
        'Repair succeeded, but the backend did not return an after screenshot.',
        'warning'
      );

      addTimelineEvent(
        'Repair succeeded; comparison unavailable because no after screenshot was returned.',
        'warning'
      );

      return;
    }

    if (originalViewportKey !== repairedViewportKey) {
      const mismatchMessage =
        `Repair succeeded, but comparison was skipped: baseline viewport ` +
        `${originalViewportKey} differs from repaired viewport ${repairedViewportKey}.`;

      showNotice(dom.notice, mismatchMessage, 'warning');

      addTimelineEvent(mismatchMessage, 'warning');

      return;
    }

    const originalFilename = extractFilename(originalScreenshotUrl);
    const repairedFilename = extractFilename(repairedScreenshotUrl);

    if (!originalFilename || !repairedFilename) {
      showNotice(
        dom.notice,
        'Repair succeeded, but screenshot filenames could not be determined for comparison.',
        'warning'
      );

      return;
    }

    try {
      const compareResponse = await fetch(
        API_BASE + '/compare-screenshots',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            original: originalFilename,
            repaired: repairedFilename,
            original_viewport: originalViewportKey,
            repaired_viewport: repairedViewportKey
          })
        }
      );

      const compareData = await readJsonResponse(
        compareResponse,
        'Screenshot comparison failed.'
      );

      if (compareData.diff_url && dom.diffRepairImage) {
        const diffUrl = new URL(
          compareData.diff_url,
          API_BASE
        );

        diffUrl.searchParams.set('t', Date.now());

        dom.diffRepairImage.src = diffUrl.href;
        dom.diffRepairImage.style.display = 'block';
      }

      if (
        dom.diffPercentage &&
        compareData.difference_percent !== undefined
      ) {
        dom.diffPercentage.textContent =
          `${compareData.difference_percent}% difference`;

        dom.diffPercentage.style.display = 'block';
      }

      showNotice(
        dom.notice,
        `Repair successful. Before/after comparison completed at ${repairViewport}.`,
        'success'
      );

      addTimelineEvent(
        `Screenshot comparison completed at ${repairViewport}`,
        'success'
      );

    } catch (comparisonError) {
      // A comparison error must not turn a successful repair into a failed repair.
      console.error(
        'OmniSight screenshot comparison error:',
        comparisonError
      );

      showNotice(
        dom.notice,
        `Repair succeeded, but screenshot comparison failed: ${comparisonError.message}`,
        'warning'
      );

      addTimelineEvent(
        'Repair succeeded, but comparison failed: ' + comparisonError.message,
        'warning'
      );
    }

  } catch (error) {
    console.error('OmniSight repair error:', error);

    const message = error instanceof TypeError
      ? 'Cannot connect to backend. Ensure FastAPI is running at ' + API_BASE
      : error.message || 'An unexpected error occurred.';

    // Only this outer handler reports an error when the repair workflow
    // itself fails before a successful repair response has been received.
    if (!repairWasSuccessful) {
      setRepairStatus('Repair failed: ' + message, 'error');

      showNotice(
        dom.notice,
        'Repair workflow failed: ' + message,
        'error'
      );

      addTimelineEvent('Repair workflow failed: ' + message, 'error');
    } else {
      // Preserve the successful repair state if a later UI operation fails.
      showNotice(
        dom.notice,
        'Repair succeeded, but a follow-up operation failed: ' + message,
        'warning'
      );

      addTimelineEvent(
        'Repair succeeded; follow-up operation failed: ' + message,
        'warning'
      );
    }

  } finally {
    state.isRepairing = false;
    document.body.dataset.inspecting = 'false';

    if (dom.repairBtn) {
      dom.repairBtn.disabled = false;
    }
  }
}

// ===== Report Export =====

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  })[char]);
}

function exportReport() {
  const now = new Date().toISOString();
  const issues = state.issues || [];

  let issueRows = '';

  if (issues.length === 0) {
    issueRows =
      '<tr><td colspan="4" style="text-align:center;color:#888;">No issues detected in this session.</td></tr>';
  } else {
    issues.forEach((issue, index) => {
      issueRows += `
        <tr>
          <td>${index + 1}</td>
          <td><code>${escapeHtml(issue.type || 'unknown')}</code></td>
          <td><code>&lt;${escapeHtml(issue.element || '?')}&gt;</code></td>
          <td>${escapeHtml(issue.description || '—')}</td>
        </tr>`;
    });
  }

  const lastInspection = state.lastInspectionUrl
    ? `<p class="meta">Last inspected: <code>${escapeHtml(state.lastInspectionUrl)}</code> · Viewport: <code>${escapeHtml(state.lastInspectionViewport)}</code></p>`
    : '';

  const screenshotSection = state.lastScreenshotUrl
    ? `<h2>Latest Screenshot</h2>
       <p class="meta">Viewport: ${escapeHtml(state.lastScreenshotViewport || 'Unknown')}</p>
       <img src="${escapeHtml(state.lastScreenshotUrl)}" alt="Inspection screenshot">`
    : '';

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>OmniSight Inspection Report — ${escapeHtml(now)}</title>
  <style>
    body {
      font-family: system-ui, sans-serif;
      max-width: 900px;
      margin: 40px auto;
      padding: 0 20px;
      color: #1a1a2e;
    }
    h1 {
      font-size: 24px;
      border-bottom: 2px solid #6366f1;
      padding-bottom: 8px;
    }
    h2 {
      font-size: 18px;
      margin-top: 32px;
      color: #6366f1;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
    }
    th, td {
      padding: 10px 12px;
      border: 1px solid #e0e0e0;
      text-align: left;
      font-size: 14px;
    }
    th {
      background: #f8f9fa;
      font-weight: 600;
    }
    code {
      background: #f0f0f5;
      padding: 2px 6px;
      border-radius: 3px;
      font-size: 13px;
      overflow-wrap: anywhere;
    }
    .meta {
      color: #666;
      font-size: 13px;
      margin-top: 4px;
    }
    .footer {
      margin-top: 40px;
      padding-top: 16px;
      border-top: 1px solid #e0e0e0;
      color: #888;
      font-size: 12px;
    }
    .stat {
      display: inline-block;
      margin: 0 24px 12px 0;
    }
    img {
      max-width: 100%;
      border: 1px solid #e0e0e0;
      border-radius: 4px;
      margin-top: 8px;
    }
  </style>
</head>
<body>
  <h1>OmniSight Inspection Report</h1>
  <p class="meta">Generated: ${escapeHtml(now)}</p>

  <h2>Session Summary</h2>
  <p>
    <span class="stat"><strong>${state.inspections}</strong> Inspections</span>
    <span class="stat"><strong>${issues.length}</strong> Issues Detected</span>
    <span class="stat"><strong>${state.repairs}</strong> Repairs Applied</span>
    <span class="stat"><strong>${state.checks}</strong> Total Checks</span>
  </p>

  ${lastInspection}

  <h2>Detected Issues</h2>
  <table>
    <thead>
      <tr><th>#</th><th>Type</th><th>Element</th><th>Description</th></tr>
    </thead>
    <tbody>${issueRows}</tbody>
  </table>

  ${screenshotSection}

  <div class="footer">
    <p>OmniSight — Visual QA &amp; Safe UI Repair.</p>
    <p>Report generated from the current browser session.</p>
  </div>
</body>
</html>`;

  const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
  const blobUrl = URL.createObjectURL(blob);
  const anchor = document.createElement('a');

  anchor.href = blobUrl;
  anchor.download = `omnisight-report-${Date.now()}.html`;

  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();

  setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);

  addTimelineEvent('Report exported', 'success');
}

// ===== Demo Site Selector =====

function handleDemoSiteChange() {
  if (!dom.demoSite || !dom.websiteUrl) return;

  if (dom.demoSite.value === 'shophub') {
    if (window.location.protocol === 'file:') {
      dom.websiteUrl.value =
        'http://127.0.0.1:8000/frontend/store.html';
    } else {
      dom.websiteUrl.value =
        new URL('store.html', window.location.href).href;
    }
  }
}

// ===== Initialization =====

function init() {
  console.log('OmniSight dashboard loaded.');

  initNavigation();

  checkBackendHealth();
  setInterval(checkBackendHealth, 10000);

  if (dom.inspectionForm) {
    dom.inspectionForm.addEventListener('submit', handleInspection);
  }

  if (dom.demoSite) {
    dom.demoSite.addEventListener('change', handleDemoSiteChange);
  }

  if (dom.evaluateBtn) {
    dom.evaluateBtn.addEventListener('click', handleSandboxEvaluate);
  }

  if (dom.resetCssBtn) {
    dom.resetCssBtn.addEventListener('click', () => {
      if (dom.cssEditor) dom.cssEditor.value = '';

      hideNotice(dom.sandboxNotice);

      if (dom.measurementsPanel) {
        dom.measurementsPanel.hidden = true;
      }

      // Resetting the sandbox should not erase a repair comparison.
      addTimelineEvent('Sandbox CSS reset', 'info');
    });
  }

  if (dom.repairBtn) {
    dom.repairBtn.addEventListener('click', handleApprovedRepair);
  }

  if (dom.exportReportBtn) {
    dom.exportReportBtn.addEventListener('click', exportReport);
  }

  if (dom.websiteUrl && !dom.websiteUrl.value.trim()) {
    dom.websiteUrl.value = 'https://example.com';
  }
}

// Start application
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
