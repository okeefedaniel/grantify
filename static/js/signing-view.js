/**
 * Signing View — read-only PDF viewer with highlighted placement areas.
 *
 * Shows the document to the signer with glowing markers where they need to sign.
 * Provides scroll-to-placement navigation.
 */
(function () {
  'use strict';

  let pdfDoc = null;
  let currentPage = 1;
  let totalPages = 0;
  let scale = 1.5;
  let placements = [];

  let canvas, ctx, canvasWrapper, markersLayer;

  function init() {
    const container = document.getElementById('signing-viewer');
    if (!container) return;

    const pdfUrl = container.dataset.pdfUrl;

    canvas = document.getElementById('signing-canvas');
    ctx = canvas.getContext('2d');
    canvasWrapper = document.getElementById('signing-canvas-wrapper');
    markersLayer = document.getElementById('signing-markers-layer');

    // Parse placements for this signer's step
    try {
      placements = JSON.parse(container.dataset.placements || '[]');
    } catch (e) {
      console.error('Failed to parse placements:', e);
    }

    // Navigation
    document.getElementById('signing-prev-page')?.addEventListener('click', function () {
      if (currentPage > 1) { currentPage--; renderPage(); }
    });
    document.getElementById('signing-next-page')?.addEventListener('click', function () {
      if (currentPage < totalPages) { currentPage++; renderPage(); }
    });

    // Jump to first placement
    document.getElementById('jump-to-sign')?.addEventListener('click', function () {
      if (placements.length > 0) {
        currentPage = placements[0].page_number;
        renderPage();
        // Scroll marker into view after render
        setTimeout(function () {
          const marker = markersLayer.querySelector('.sign-here-marker');
          if (marker) marker.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 300);
      }
    });

    // Load PDF
    if (pdfUrl && typeof pdfjsLib !== 'undefined') {
      pdfjsLib.GlobalWorkerOptions.workerSrc =
        'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';

      pdfjsLib.getDocument(pdfUrl).promise.then(function (pdf) {
        pdfDoc = pdf;
        totalPages = pdf.numPages;
        updatePageInfo();
        renderPage();

        // Auto-jump to first placement page
        if (placements.length > 0) {
          currentPage = placements[0].page_number;
          renderPage();
        }
      }).catch(function (err) {
        console.error('Failed to load PDF:', err);
      });
    }
  }

  function renderPage() {
    if (!pdfDoc) return;

    pdfDoc.getPage(currentPage).then(function (page) {
      const viewport = page.getViewport({ scale: scale });
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      canvas.style.width = viewport.width + 'px';
      canvas.style.height = viewport.height + 'px';

      markersLayer.style.width = viewport.width + 'px';
      markersLayer.style.height = viewport.height + 'px';
      canvasWrapper.style.width = viewport.width + 'px';
      canvasWrapper.style.height = viewport.height + 'px';

      page.render({ canvasContext: ctx, viewport: viewport }).promise.then(function () {
        renderSignHereMarkers();
      });

      updatePageInfo();
    });
  }

  function updatePageInfo() {
    const info = document.getElementById('signing-page-info');
    if (info) info.textContent = currentPage + ' / ' + totalPages;
  }

  function renderSignHereMarkers() {
    markersLayer.querySelectorAll('.sign-here-marker').forEach(function (m) { m.remove(); });

    placements.forEach(function (p) {
      if (p.page_number !== currentPage) return;

      const marker = document.createElement('div');
      marker.className = 'sign-here-marker';
      marker.style.left = p.x + '%';
      marker.style.top = p.y + '%';
      marker.style.width = p.width + '%';
      marker.style.height = p.height + '%';

      var typeLabel = p.field_type === 'signature' ? 'Sign Here'
        : p.field_type === 'initials' ? 'Initials'
        : p.field_type === 'date' ? 'Date'
        : 'Name';
      marker.setAttribute('data-label', typeLabel);
      marker.style.setProperty('--marker-label', '"' + typeLabel + '"');

      // Override the ::after content
      marker.title = typeLabel;

      markersLayer.appendChild(marker);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
