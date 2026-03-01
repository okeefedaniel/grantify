/**
 * Placement Editor — PDF.js-based editor for positioning signature fields.
 *
 * Renders PDF pages, allows drag-and-drop placement of signature markers,
 * and saves placements via AJAX.
 */
(function () {
  'use strict';

  // State
  let pdfDoc = null;
  let currentPage = 1;
  let totalPages = 0;
  let scale = 1.5;
  let placements = [];
  let steps = [];
  let selectedStepId = null;
  let selectedFieldType = 'signature';
  let dragging = null;
  let resizing = null;
  let dragOffset = { x: 0, y: 0 };

  // DOM references
  let canvas, ctx, canvasWrapper, markersLayer;

  // Config (set from data attributes)
  let documentId = '';
  let apiUrl = '';
  let pdfUrl = '';
  let csrfToken = '';

  function init() {
    const container = document.getElementById('placement-editor');
    if (!container) return;

    documentId = container.dataset.documentId;
    apiUrl = container.dataset.apiUrl;
    pdfUrl = container.dataset.pdfUrl;
    csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

    canvas = document.getElementById('pdf-canvas');
    ctx = canvas.getContext('2d');
    canvasWrapper = document.getElementById('canvas-wrapper');
    markersLayer = document.getElementById('markers-layer');

    // Parse initial data
    try {
      placements = JSON.parse(container.dataset.placements || '[]');
      steps = JSON.parse(container.dataset.steps || '[]');
    } catch (e) {
      console.error('Failed to parse placement data:', e);
    }

    // Populate step selector
    populateStepSelector();

    // Load PDF
    loadPDF();

    // Navigation
    document.getElementById('prev-page')?.addEventListener('click', function () {
      if (currentPage > 1) { currentPage--; renderPage(); }
    });
    document.getElementById('next-page')?.addEventListener('click', function () {
      if (currentPage < totalPages) { currentPage++; renderPage(); }
    });

    // Field type selector
    document.querySelectorAll('[data-field-type]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        selectedFieldType = this.dataset.fieldType;
        document.querySelectorAll('[data-field-type]').forEach(function (b) {
          b.classList.toggle('active', b.dataset.fieldType === selectedFieldType);
        });
      });
    });

    // Click on canvas to add placement
    markersLayer.addEventListener('click', function (e) {
      if (e.target !== markersLayer) return; // Only direct clicks
      if (!selectedStepId) {
        alert('Please select a signing step first.');
        return;
      }

      const rect = markersLayer.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;

      addPlacement({
        step_id: selectedStepId,
        field_type: selectedFieldType,
        page_number: currentPage,
        x: x,
        y: y,
        width: 20,
        height: 5,
      });
    });

    // Save button
    document.getElementById('save-placements')?.addEventListener('click', savePlacements);

    // Mouse/touch events for drag and resize
    markersLayer.addEventListener('mousedown', onPointerDown);
    markersLayer.addEventListener('touchstart', onPointerDown, { passive: false });
    document.addEventListener('mousemove', onPointerMove);
    document.addEventListener('touchmove', onPointerMove, { passive: false });
    document.addEventListener('mouseup', onPointerUp);
    document.addEventListener('touchend', onPointerUp);
  }

  function populateStepSelector() {
    const select = document.getElementById('step-selector');
    if (!select) return;
    select.innerHTML = '<option value="">-- Select Step --</option>';
    steps.forEach(function (step) {
      const opt = document.createElement('option');
      opt.value = step.id;
      opt.textContent = 'Step ' + step.order + ': ' + step.label;
      select.appendChild(opt);
    });
    select.addEventListener('change', function () {
      selectedStepId = this.value || null;
    });
  }

  function loadPDF() {
    if (!pdfUrl || typeof pdfjsLib === 'undefined') {
      console.error('PDF.js or PDF URL not available');
      return;
    }

    pdfjsLib.GlobalWorkerOptions.workerSrc =
      'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

    pdfjsLib.getDocument(pdfUrl).promise.then(function (pdf) {
      pdfDoc = pdf;
      totalPages = pdf.numPages;
      updatePageInfo();
      renderPage();
    }).catch(function (err) {
      console.error('Failed to load PDF:', err);
    });
  }

  function renderPage() {
    if (!pdfDoc) return;

    pdfDoc.getPage(currentPage).then(function (page) {
      const viewport = page.getViewport({ scale: scale });
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      canvas.style.width = viewport.width + 'px';
      canvas.style.height = viewport.height + 'px';

      // Size the markers layer to match
      markersLayer.style.width = viewport.width + 'px';
      markersLayer.style.height = viewport.height + 'px';
      canvasWrapper.style.width = viewport.width + 'px';
      canvasWrapper.style.height = viewport.height + 'px';

      page.render({ canvasContext: ctx, viewport: viewport }).promise.then(function () {
        renderMarkers();
      });

      updatePageInfo();
    });
  }

  function updatePageInfo() {
    const info = document.getElementById('page-info');
    if (info) info.textContent = currentPage + ' / ' + totalPages;
  }

  function renderMarkers() {
    // Clear existing markers
    markersLayer.querySelectorAll('.placement-marker').forEach(function (m) { m.remove(); });

    // Render placements for current page
    placements.forEach(function (p, idx) {
      if (p.page_number !== currentPage) return;

      const step = steps.find(function (s) { return s.id === p.step_id; });
      const marker = document.createElement('div');
      marker.className = 'placement-marker';
      marker.dataset.index = idx;
      marker.dataset.stepOrder = step ? step.order : 0;
      marker.style.left = p.x + '%';
      marker.style.top = p.y + '%';
      marker.style.width = p.width + '%';
      marker.style.height = p.height + '%';

      // Label
      const label = (step ? 'S' + step.order : '?') + ': ' + (p.field_type || 'sig');
      marker.textContent = label;
      marker.title = (step ? step.label : 'Unknown') + ' — ' + p.field_type;

      // Delete button
      const delBtn = document.createElement('button');
      delBtn.className = 'delete-btn';
      delBtn.innerHTML = '&times;';
      delBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        placements.splice(idx, 1);
        renderMarkers();
      });
      marker.appendChild(delBtn);

      // Resize handle
      const handle = document.createElement('div');
      handle.className = 'resize-handle';
      handle.dataset.index = idx;
      marker.appendChild(handle);

      markersLayer.appendChild(marker);
    });
  }

  function addPlacement(data) {
    placements.push(data);
    renderMarkers();
  }

  // Drag and resize handlers
  function onPointerDown(e) {
    const touch = e.touches ? e.touches[0] : e;
    const target = touch.target || e.target;

    if (target.classList.contains('resize-handle')) {
      e.preventDefault();
      resizing = parseInt(target.dataset.index);
      return;
    }

    const marker = target.closest('.placement-marker');
    if (marker) {
      e.preventDefault();
      const idx = parseInt(marker.dataset.index);
      dragging = idx;

      const rect = markersLayer.getBoundingClientRect();
      const px = ((touch.clientX - rect.left) / rect.width) * 100;
      const py = ((touch.clientY - rect.top) / rect.height) * 100;
      dragOffset.x = px - placements[idx].x;
      dragOffset.y = py - placements[idx].y;

      marker.classList.add('dragging');
    }
  }

  function onPointerMove(e) {
    if (dragging === null && resizing === null) return;
    e.preventDefault();

    const touch = e.touches ? e.touches[0] : e;
    const rect = markersLayer.getBoundingClientRect();
    const px = ((touch.clientX - rect.left) / rect.width) * 100;
    const py = ((touch.clientY - rect.top) / rect.height) * 100;

    if (dragging !== null) {
      const p = placements[dragging];
      p.x = Math.max(0, Math.min(100 - p.width, px - dragOffset.x));
      p.y = Math.max(0, Math.min(100 - p.height, py - dragOffset.y));
      renderMarkers();
    }

    if (resizing !== null) {
      const p = placements[resizing];
      p.width = Math.max(5, Math.min(100 - p.x, px - p.x));
      p.height = Math.max(2, Math.min(100 - p.y, py - p.y));
      renderMarkers();
    }
  }

  function onPointerUp() {
    if (dragging !== null) {
      const marker = markersLayer.querySelector('[data-index="' + dragging + '"]');
      if (marker) marker.classList.remove('dragging');
    }
    dragging = null;
    resizing = null;
  }

  function savePlacements() {
    const btn = document.getElementById('save-placements');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Saving...';
    }

    fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify({ placements: placements }),
    })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = '<i class="bi bi-check-circle me-1"></i>Saved';
          setTimeout(function () {
            btn.innerHTML = '<i class="bi bi-save me-1"></i>Save Placements';
          }, 2000);
        }
      })
      .catch(function (err) {
        console.error('Save failed:', err);
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = '<i class="bi bi-exclamation-triangle me-1"></i>Save Failed';
        }
      });
  }

  // Initialize
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
