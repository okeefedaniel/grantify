/**
 * Signature Pad — wraps signature_pad.js for the signing interface.
 *
 * Handles three signature methods: typed, uploaded, drawn.
 * Exports drawn signatures as base64 PNG into a hidden form field.
 */
(function () {
  'use strict';

  let signaturePad = null;
  let currentMethod = 'typed';

  function init() {
    const canvas = document.getElementById('signature-canvas');
    if (!canvas) return;

    // Initialize signature_pad library
    signaturePad = new SignaturePad(canvas, {
      backgroundColor: 'rgba(255, 255, 255, 0)',
      penColor: '#1a1a2e',
      minWidth: 1,
      maxWidth: 3,
    });

    // Responsive canvas sizing
    resizeCanvas(canvas);
    window.addEventListener('resize', function () {
      resizeCanvas(canvas);
    });

    // Method tab switching
    document.querySelectorAll('[data-sig-method]').forEach(function (tab) {
      tab.addEventListener('click', function (e) {
        e.preventDefault();
        switchMethod(this.dataset.sigMethod);
      });
    });

    // Clear button
    const clearBtn = document.getElementById('sig-clear');
    if (clearBtn) {
      clearBtn.addEventListener('click', function () {
        signaturePad.clear();
        updateHiddenField();
      });
    }

    // Typed name input — update preview
    const typedInput = document.getElementById('id_typed_name');
    if (typedInput) {
      typedInput.addEventListener('input', function () {
        const preview = document.getElementById('typed-preview');
        if (preview) {
          preview.textContent = this.value || '';
        }
      });
    }

    // File upload preview
    const fileInput = document.getElementById('id_signature_image');
    if (fileInput) {
      fileInput.addEventListener('change', function () {
        const preview = document.getElementById('upload-preview');
        if (preview && this.files && this.files[0]) {
          const reader = new FileReader();
          reader.onload = function (e) {
            preview.innerHTML = '<img src="' + e.target.result + '" alt="Signature preview" class="img-fluid" style="max-height: 80px;">';
          };
          reader.readAsDataURL(this.files[0]);
        }
      });
    }

    // On canvas change, update hidden field
    if (canvas) {
      canvas.addEventListener('pointerup', function () {
        updateHiddenField();
      });
    }

    // Form submit — validate and populate
    const form = document.getElementById('signing-form');
    if (form) {
      form.addEventListener('submit', function (e) {
        // Set signature_type radio
        const radioInput = document.querySelector('input[name="signature_type"][value="' + currentMethod + '"]');
        if (radioInput) radioInput.checked = true;

        // For drawn, populate the hidden field
        if (currentMethod === 'drawn') {
          updateHiddenField();
          if (signaturePad.isEmpty()) {
            e.preventDefault();
            alert('Please draw your signature before submitting.');
            return false;
          }
        }
      });
    }

    // Pre-select method based on radio
    const checkedRadio = document.querySelector('input[name="signature_type"]:checked');
    if (checkedRadio) {
      switchMethod(checkedRadio.value);
    }

    // Saved signature quick-apply
    document.querySelectorAll('[data-apply-signature]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        const sigType = this.dataset.sigType;
        const sigValue = this.dataset.sigValue;
        switchMethod(sigType);
        if (sigType === 'typed') {
          const input = document.getElementById('id_typed_name');
          if (input) {
            input.value = sigValue;
            input.dispatchEvent(new Event('input'));
          }
        }
      });
    });
  }

  function switchMethod(method) {
    currentMethod = method;

    // Update tab active state
    document.querySelectorAll('[data-sig-method]').forEach(function (tab) {
      tab.classList.toggle('active', tab.dataset.sigMethod === method);
    });

    // Show/hide panels
    document.querySelectorAll('.sig-panel').forEach(function (panel) {
      panel.style.display = panel.dataset.sigPanel === method ? 'block' : 'none';
    });

    // Update radio
    const radio = document.querySelector('input[name="signature_type"][value="' + method + '"]');
    if (radio) radio.checked = true;
  }

  function resizeCanvas(canvas) {
    const wrapper = canvas.parentElement;
    const ratio = Math.max(window.devicePixelRatio || 1, 1);
    const width = wrapper.offsetWidth;
    const height = 200;

    canvas.width = width * ratio;
    canvas.height = height * ratio;
    canvas.style.width = width + 'px';
    canvas.style.height = height + 'px';

    const ctx = canvas.getContext('2d');
    ctx.scale(ratio, ratio);

    if (signaturePad) {
      signaturePad.clear();
    }
  }

  function updateHiddenField() {
    const hidden = document.getElementById('id_drawn_data');
    if (hidden && signaturePad && !signaturePad.isEmpty()) {
      hidden.value = signaturePad.toDataURL('image/png');
    }
  }

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
