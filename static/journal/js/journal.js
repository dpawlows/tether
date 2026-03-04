(function () {
  "use strict";

  /* ============================================================
     CONFIG — read from data attributes on our own <script> tag,
     avoiding any inline <script> that would be blocked by CSP.
     ============================================================ */
  var scriptEl   = document.currentScript ||
                   document.querySelector('script[data-journal-id]');
  var JOURNAL_ID = scriptEl ? scriptEl.getAttribute('data-journal-id') : null;
    var OPEN_DELETE = scriptEl && scriptEl.getAttribute('data-open-delete-modal') === '1';
  

  /* ============================================================
     MAP CANVAS
     ============================================================ */
  function setupCanvas(canvasId, savedImgId) {
    var canvas = document.getElementById(canvasId);
    if (!canvas) return null;
    var ctx = canvas.getContext('2d');
    var drawing = false, erasing = false, lastX = 0, lastY = 0;

    function init() {
      /* Use offsetWidth/Height which are available even before first paint,
         and fall back to the CSS-computed size — avoids the post-save shrink. */
	  var r = canvas.getBoundingClientRect();
      canvas.width  = Math.round(r.width) || 600;
      canvas.height = Math.round(r.height) || 500;
      var img = document.getElementById(savedImgId);
      if (!img) return;
      function draw() { ctx.drawImage(img, 0, 0, canvas.width, canvas.height); }
      if (img.complete) { draw(); } else { img.addEventListener('load', draw); }
    }

    function pos(e) {
      var r = canvas.getBoundingClientRect();
      return {
        x: (e.clientX - r.left) * (canvas.width  / r.width),
        y: (e.clientY - r.top)  * (canvas.height / r.height)
      };
    }

    canvas.addEventListener('contextmenu', function (e) { e.preventDefault(); });

    canvas.addEventListener('pointerdown', function (e) {
      erasing = (e.button === 2);
      drawing = true;
      var p = pos(e); lastX = p.x; lastY = p.y;
      canvas.setPointerCapture(e.pointerId);
	canvas.classList.toggle('cursor-cell', erasing);
	canvas.classList.toggle('cursor-crosshair', !erasing);
      e.preventDefault();
    });

    canvas.addEventListener('pointermove', function (e) {
      if (!drawing) return;
      var p = pos(e);
      ctx.beginPath();
      ctx.moveTo(lastX, lastY);
      ctx.lineTo(p.x, p.y);
      if (erasing) {
        ctx.globalCompositeOperation = 'destination-out';
        ctx.strokeStyle = 'rgba(0,0,0,1)';
        ctx.lineWidth   = 16;
      } else {
        ctx.globalCompositeOperation = 'source-over';
        var pressure = (e.pointerType === 'pen') ? Math.max(0.15, e.pressure) : 1;
        ctx.strokeStyle = 'rgba(43,29,14,0.82)';
        ctx.lineWidth   = pressure * 2.5;
      }
      ctx.lineCap = ctx.lineJoin = 'round';
      ctx.stroke();
      lastX = p.x; lastY = p.y;
      e.preventDefault();
    });

      canvas.addEventListener('pointerup',     function () { drawing = false; erasing = false; ctx.globalCompositeOperation = 'source-over'; canvas.classList.remove('cursor-cell'); canvas.classList.add('cursor-crosshair');});
      canvas.addEventListener('pointercancel', function () { drawing = false; erasing = false; ctx.globalCompositeOperation = 'source-over'; canvas.style.cursor = 'crosshair'; });

    var ro = new ResizeObserver(function(entries) {
	var r = entries[0].contentRect;
	if (r.width > 0 && r.height > 0) {
	    ro.disconnect();
	    init();
	}
    });
 ro.observe(canvas);
    return canvas;
  }

  var cLeft  = setupCanvas('map-canvas-left',  'map-saved-image-left');
  var cRight = setupCanvas('map-canvas-right', 'map-saved-image-right');

  var mapForm = document.getElementById('map-form');
  if (mapForm) {
    mapForm.addEventListener('submit', function () {
      var inpL = document.getElementById('map-image-left-input');
      var inpR = document.getElementById('map-image-right-input');
      if (cLeft  && inpL) inpL.value = cLeft.toDataURL('image/png');
      if (cRight && inpR) inpR.value = cRight.toDataURL('image/png');
    });
  }

  /* ============================================================
     ENTRY INLINE EDITING
     ============================================================ */
  document.querySelectorAll('.entry-edit-trigger').forEach(function (btn) {
    btn.addEventListener('click', function () {
	var body = btn.closest('.entry-body');
	body.querySelector('.entry-view').classList.add('is-hidden');
	body.querySelector('.entry-edit-form').classList.add('is-flex');
	btn.classList.add('is-hidden');	
      var ta = body.querySelector('.entry-edit-textarea');
      ta.focus();
      ta.setSelectionRange(ta.value.length, ta.value.length);
    });
  });

  document.querySelectorAll('.btn-cancel').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var body = btn.closest('.entry-body');
	body.querySelector('.entry-view').classList.remove('is-hidden');
	body.querySelector('.entry-edit-form').classList.remove('is-flex');
	body.querySelector('.entry-edit-trigger').classList.remove('is-hidden');
    });
  });

  /* ============================================================
     COMPOSE DRAFT — persist textarea text across navigation
     ============================================================ */
  if (JOURNAL_ID) {
    var draftKey    = 'tether-draft-' + JOURNAL_ID;
    var composeArea = document.querySelector('.compose-form textarea');

    if (composeArea) {
      var saved = localStorage.getItem(draftKey);
      if (saved) composeArea.value = saved;

      composeArea.addEventListener('input', function () {
        localStorage.setItem(draftKey, composeArea.value);
      });

      composeArea.closest('form').addEventListener('submit', function () {
        localStorage.removeItem(draftKey);
      });

      var doneLink = document.querySelector('.footer-link');
      if (doneLink) {
        doneLink.addEventListener('click', function () {
          localStorage.removeItem(draftKey);
        });
      }
    }
  }

  /* ============================================================
     ARROW KEY NAVIGATION
     ============================================================ */
  document.addEventListener('keydown', function (e) {
    if (e.target.tagName === 'TEXTAREA' || e.target.tagName === 'INPUT') return;
    if (e.key === 'ArrowLeft') {
      var prev = document.getElementById('btn-prev');
      if (prev && prev.href) window.location = prev.href;
    } else if (e.key === 'ArrowRight') {
      var next = document.getElementById('btn-next');
      if (next && next.href) window.location = next.href;
    }
  });

  /* ============================================================
     DELETE JOURNAL MODAL
     ============================================================ */
  var deleteModal = document.getElementById('delete-modal');

  function openDeleteModal() {
    deleteModal.classList.add('delete-modal--open');
    deleteModal.removeAttribute('aria-hidden');
    var input = document.getElementById('delete-codeword');
    if (input) input.focus();
  }

  function closeDeleteModal() {
    deleteModal.classList.remove('delete-modal--open');
    deleteModal.setAttribute('aria-hidden', 'true');
  }

  document.querySelectorAll('.delete-trigger').forEach(function (btn) {
    btn.addEventListener('click', openDeleteModal);
  });

  deleteModal.addEventListener('click', function (e) {
    if (e.target === deleteModal) closeDeleteModal();
  });

  deleteModal.querySelector('.delete-cancel').addEventListener('click', function (e) {
    e.preventDefault();
    closeDeleteModal();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && deleteModal.classList.contains('delete-modal--open')) closeDeleteModal();
  });

  /* Auto-open delete modal on page load if a bad codeword was submitted */
    if (OPEN_DELETE) { openDeleteModal(); }

   window.addEventListener('pageshow', function(e) {
  if (e.persisted) {
    document.querySelectorAll('.entry-edit-form').forEach(function(form) {
      form.classList.remove('is-flex');
    });
    document.querySelectorAll('.entry-view').forEach(function(el) {
      el.classList.remove('is-hidden');
    });
    document.querySelectorAll('.entry-edit-trigger').forEach(function(btn) {
      btn.classList.remove('is-hidden');
    });
  }
});

}());
