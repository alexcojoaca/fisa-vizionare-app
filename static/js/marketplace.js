/**
 * Premium Marketplace 2026 — Vanilla JS
 * Handles filter drawer, zone selector modal, ESC key, body scroll lock
 */
(function() {
  'use strict';

  // ===== FILTER DRAWER =====
  var filtersPanel = document.getElementById('filters-panel');
  var filtersOverlay = document.getElementById('filters-panel-overlay');
  var filtersOpenBtn = document.getElementById('filters-open-btn');
  var filtersCloseBtn = document.querySelector('.js-filters-panel-close');
  var filtersResetBtn = document.getElementById('filters-reset-btn');

  function openFilters() {
    if (filtersOverlay) {
      filtersOverlay.classList.add('open');
      filtersOverlay.setAttribute('aria-hidden', 'false');
    }
    if (filtersPanel) {
      filtersPanel.classList.add('open');
      document.body.style.overflow = 'hidden';
    }
  }

  function closeFilters() {
    if (filtersOverlay) {
      filtersOverlay.classList.remove('open');
      filtersOverlay.setAttribute('aria-hidden', 'true');
    }
    if (filtersPanel) {
      filtersPanel.classList.remove('open');
      document.body.style.overflow = '';
    }
  }

  if (filtersOpenBtn) {
    filtersOpenBtn.addEventListener('click', openFilters);
  }
  if (filtersOverlay) {
    filtersOverlay.addEventListener('click', closeFilters);
  }
  if (filtersCloseBtn) {
    filtersCloseBtn.addEventListener('click', closeFilters);
  }
  if (filtersResetBtn) {
    filtersResetBtn.addEventListener('click', function(e) {
      e.preventDefault();
      closeFilters();
      window.location.href = filtersResetBtn.href;
    });
  }

  // ===== ZONE SELECTOR MODAL =====
  var zoneSelectorModal = document.getElementById('zone-selector-modal');
  var zoneSelectorOverlay = document.getElementById('zone-selector-overlay');
  var zoneSelectorSearch = document.getElementById('zone-selector-search');
  var zoneSelectorChips = document.getElementById('zone-selector-chips');
  var zoneSelectorGroups = document.getElementById('zone-selector-groups');
  var zoneSelectorDone = document.querySelector('.js-zone-selector-done');
  var zoneSelectorReset = document.querySelector('.js-zone-selector-reset');
  var zoneSelectorClose = document.querySelector('.js-zone-selector-close');

  var zoneSelectorContext = {
    formId: null,
    containerId: null,
    inputName: null,
    countElId: null,
    chipsWrapId: null
  };

  function openZoneSelector() {
    var btn = this;
    zoneSelectorContext.formId = btn.getAttribute('data-form-id');
    zoneSelectorContext.containerId = btn.getAttribute('data-container-id');
    zoneSelectorContext.inputName = btn.getAttribute('data-input-name');
    zoneSelectorContext.countElId = btn.getAttribute('data-count-el');
    zoneSelectorContext.chipsWrapId = btn.getAttribute('data-chips-wrap-id') || null;

    var container = zoneSelectorContext.containerId ? document.getElementById(zoneSelectorContext.containerId) : null;
    var selected = [];
    if (container) {
      var inputs = container.querySelectorAll('input[name="' + zoneSelectorContext.inputName + '"]');
      for (var i = 0; i < inputs.length; i++) {
        selected.push(inputs[i].value);
      }
    }

    var checkboxes = zoneSelectorModal ? zoneSelectorModal.querySelectorAll('.zone-selector-cb') : [];
    for (var j = 0; j < checkboxes.length; j++) {
      checkboxes[j].checked = selected.indexOf(checkboxes[j].value) >= 0;
    }

    if (zoneSelectorSearch) zoneSelectorSearch.value = '';
    zoneSelectorFilterGroups('');
    zoneSelectorExpandAll(true);
    renderZoneSelectorChips();

    if (zoneSelectorOverlay) {
      zoneSelectorOverlay.classList.add('open');
      zoneSelectorOverlay.setAttribute('aria-hidden', 'false');
    }
    if (zoneSelectorModal) {
      zoneSelectorModal.classList.add('open');
      document.body.style.overflow = 'hidden';
    }
  }

  function closeZoneSelector() {
    if (zoneSelectorOverlay) {
      zoneSelectorOverlay.classList.remove('open');
      zoneSelectorOverlay.setAttribute('aria-hidden', 'true');
    }
    if (zoneSelectorModal) {
      zoneSelectorModal.classList.remove('open');
      document.body.style.overflow = (filtersPanel && filtersPanel.classList.contains('open')) ? 'hidden' : '';
    }
  }

  function zoneSelectorExpandAll(open) {
    if (!zoneSelectorGroups) return;
    var titles = zoneSelectorGroups.querySelectorAll('.zone-selector-group-title');
    for (var i = 0; i < titles.length; i++) {
      var body = titles[i].nextElementSibling;
      titles[i].setAttribute('aria-expanded', open ? 'true' : 'false');
      if (body) body.classList.toggle('open', open);
    }
  }

  function zoneSelectorFilterGroups(q) {
    q = (q || '').toLowerCase().trim();
    if (!zoneSelectorGroups) return;
    var groups = zoneSelectorGroups.querySelectorAll('.zone-selector-group');
    for (var i = 0; i < groups.length; i++) {
      var opts = groups[i].querySelectorAll('.zone-selector-option');
      var hasVisible = false;
      for (var j = 0; j < opts.length; j++) {
        var name = (opts[j].querySelector('span') || {}).textContent || '';
        var match = !q || name.toLowerCase().indexOf(q) >= 0;
        opts[j].style.display = match ? '' : 'none';
        if (match) hasVisible = true;
      }
      groups[i].style.display = hasVisible ? '' : 'none';
    }
  }

  function renderZoneSelectorChips() {
    if (!zoneSelectorChips) return;
    var checkboxes = zoneSelectorModal ? zoneSelectorModal.querySelectorAll('.zone-selector-cb:checked') : [];
    var html = '';
    for (var i = 0; i < checkboxes.length; i++) {
      var name = checkboxes[i].getAttribute('data-zone-name') || ('Zone ' + checkboxes[i].value);
      html += '<span class="zone-chip-tag" data-zone-id="' + escapeHtml(checkboxes[i].value) + '">' + escapeHtml(name) + ' <span class="remove" data-zone-id="' + escapeHtml(checkboxes[i].value) + '" aria-label="Elimină">×</span></span>';
    }
    zoneSelectorChips.innerHTML = html;
    var removes = zoneSelectorChips.querySelectorAll('.remove');
    for (var r = 0; r < removes.length; r++) {
      removes[r].addEventListener('click', function() {
        var id = this.getAttribute('data-zone-id');
        var cb = zoneSelectorModal.querySelector('.zone-selector-cb[value="' + escapeHtml(id) + '"]');
        if (cb) cb.checked = false;
        renderZoneSelectorChips();
      });
    }
  }

  function escapeHtml(s) {
    var div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }

  function applyZoneSelection() {
    var container = zoneSelectorContext.containerId ? document.getElementById(zoneSelectorContext.containerId) : null;
    var countEl = zoneSelectorContext.countElId ? document.getElementById(zoneSelectorContext.countElId) : null;
    var chipsWrap = zoneSelectorContext.chipsWrapId ? document.getElementById(zoneSelectorContext.chipsWrapId) : null;

    var checkboxes = zoneSelectorModal ? zoneSelectorModal.querySelectorAll('.zone-selector-cb:checked') : [];
    var selected = [];
    for (var i = 0; i < checkboxes.length; i++) {
      selected.push({
        id: checkboxes[i].value,
        name: checkboxes[i].getAttribute('data-zone-name') || ''
      });
    }

    if (container) {
      container.innerHTML = '';
      for (var j = 0; j < selected.length; j++) {
        var input = document.createElement('input');
        input.type = 'hidden';
        input.name = zoneSelectorContext.inputName;
        input.value = selected[j].id;
        container.appendChild(input);
      }
    }

    if (countEl) {
      countEl.textContent = selected.length;
    }

    if (chipsWrap) {
      chipsWrap.innerHTML = '';
      for (var k = 0; k < selected.length; k++) {
        var tag = document.createElement('span');
        tag.className = 'zone-chip-tag';
        tag.textContent = selected[k].name;
        chipsWrap.appendChild(tag);
      }
    }

    closeZoneSelector();
  }

  function resetZoneSelection() {
    var checkboxes = zoneSelectorModal ? zoneSelectorModal.querySelectorAll('.zone-selector-cb') : [];
    for (var i = 0; i < checkboxes.length; i++) checkboxes[i].checked = false;
    renderZoneSelectorChips();
  }

  var zoneTriggerButtons = document.querySelectorAll('.js-open-zone-selector');
  if (zoneTriggerButtons.length) {
    for (var b = 0; b < zoneTriggerButtons.length; b++) {
      zoneTriggerButtons[b].addEventListener('click', openZoneSelector);
    }
  }

  if (zoneSelectorSearch) {
    zoneSelectorSearch.addEventListener('input', function() {
      zoneSelectorFilterGroups(this.value);
    });
  }

  if (zoneSelectorGroups) {
    zoneSelectorGroups.addEventListener('click', function(e) {
      var t = e.target;
      if (t.classList && t.classList.contains('zone-selector-group-title')) {
        var body = t.nextElementSibling;
        var expanded = t.getAttribute('aria-expanded') === 'true';
        t.setAttribute('aria-expanded', !expanded);
        if (body) body.classList.toggle('open', !expanded);
      }
      if (t.classList && t.classList.contains('zone-selector-cb')) {
        setTimeout(renderZoneSelectorChips, 0);
      }
    });
  }

  if (zoneSelectorDone) {
    zoneSelectorDone.addEventListener('click', applyZoneSelection);
  }
  if (zoneSelectorReset) {
    zoneSelectorReset.addEventListener('click', resetZoneSelection);
  }
  if (zoneSelectorClose) {
    zoneSelectorClose.addEventListener('click', closeZoneSelector);
  }
  if (zoneSelectorOverlay) {
    zoneSelectorOverlay.addEventListener('click', closeZoneSelector);
  }

  // ===== ETAJ SELECTOR MODAL =====
  var etajSelectorModal = document.getElementById('etaj-selector-modal');
  var etajSelectorOverlay = document.getElementById('etaj-selector-overlay');
  var etajSelectorChips = document.getElementById('etaj-selector-chips');
  var etajSelectorList = document.getElementById('etaj-selector-list');
  var etajSelectorDone = document.querySelector('.js-etaj-selector-done');
  var etajSelectorReset = document.querySelector('.js-etaj-selector-reset');
  var etajSelectorClose = document.querySelector('.js-etaj-selector-close');

  var etajSelectorContext = { containerId: null, inputName: 'etaj', countElId: null, chipsWrapId: null };

  function openEtajSelector() {
    var btn = this;
    etajSelectorContext.containerId = btn.getAttribute('data-container-id');
    etajSelectorContext.countElId = btn.getAttribute('data-count-el');
    etajSelectorContext.chipsWrapId = btn.getAttribute('data-chips-wrap-id') || null;

    var container = etajSelectorContext.containerId ? document.getElementById(etajSelectorContext.containerId) : null;
    var selected = [];
    if (container) {
      var inputs = container.querySelectorAll('input[name="' + etajSelectorContext.inputName + '"]');
      for (var i = 0; i < inputs.length; i++) {
        var v = inputs[i].value;
        selected.push(v === 'P' ? 'Parter' : v);
      }
    }

    var cbs = etajSelectorModal ? etajSelectorModal.querySelectorAll('.etaj-selector-cb') : [];
    for (var j = 0; j < cbs.length; j++) {
      cbs[j].checked = selected.indexOf(cbs[j].value) >= 0;
    }

    renderEtajSelectorChips();

    if (etajSelectorOverlay) {
      etajSelectorOverlay.classList.add('open');
      etajSelectorOverlay.setAttribute('aria-hidden', 'false');
    }
    if (etajSelectorModal) {
      etajSelectorModal.classList.add('open');
      document.body.style.overflow = 'hidden';
    }
  }

  function closeEtajSelector() {
    if (etajSelectorOverlay) {
      etajSelectorOverlay.classList.remove('open');
      etajSelectorOverlay.setAttribute('aria-hidden', 'true');
    }
    if (etajSelectorModal) {
      etajSelectorModal.classList.remove('open');
      document.body.style.overflow = (filtersPanel && filtersPanel.classList.contains('open')) ? 'hidden' : (zoneSelectorModal && zoneSelectorModal.classList.contains('open')) ? 'hidden' : '';
    }
  }

  function renderEtajSelectorChips() {
    if (!etajSelectorChips) return;
    var cbs = etajSelectorModal ? etajSelectorModal.querySelectorAll('.etaj-selector-cb:checked') : [];
    var html = '';
    for (var i = 0; i < cbs.length; i++) {
      var label = cbs[i].getAttribute('data-etaj-label') || cbs[i].value;
      html += '<span class="zone-chip-tag" data-etaj-val="' + escapeHtml(cbs[i].value) + '">' + escapeHtml(label) + ' <span class="remove" data-etaj-val="' + escapeHtml(cbs[i].value) + '" aria-label="Elimină">×</span></span>';
    }
    etajSelectorChips.innerHTML = html;
    var removes = etajSelectorChips.querySelectorAll('.remove');
    for (var r = 0; r < removes.length; r++) {
      removes[r].addEventListener('click', function() {
        var val = this.getAttribute('data-etaj-val');
        var cb = etajSelectorModal.querySelector('.etaj-selector-cb[value="' + val.replace(/"/g, '\\"') + '"]');
        if (cb) cb.checked = false;
        renderEtajSelectorChips();
      });
    }
  }

  function applyEtajSelection() {
    var container = etajSelectorContext.containerId ? document.getElementById(etajSelectorContext.containerId) : null;
    var countEl = etajSelectorContext.countElId ? document.getElementById(etajSelectorContext.countElId) : null;
    var chipsWrap = etajSelectorContext.chipsWrapId ? document.getElementById(etajSelectorContext.chipsWrapId) : null;

    var cbs = etajSelectorModal ? etajSelectorModal.querySelectorAll('.etaj-selector-cb:checked') : [];
    var selected = [];
    for (var i = 0; i < cbs.length; i++) {
      selected.push({
        value: cbs[i].value,
        label: cbs[i].getAttribute('data-etaj-label') || cbs[i].value
      });
    }

    if (container) {
      container.innerHTML = '';
      for (var j = 0; j < selected.length; j++) {
        var input = document.createElement('input');
        input.type = 'hidden';
        input.name = etajSelectorContext.inputName;
        input.value = selected[j].value;
        container.appendChild(input);
      }
    }

    if (countEl) countEl.textContent = selected.length;
    if (chipsWrap) {
      chipsWrap.innerHTML = '';
      for (var k = 0; k < selected.length; k++) {
        var tag = document.createElement('span');
        tag.className = 'zone-chip-tag';
        tag.textContent = selected[k].label;
        chipsWrap.appendChild(tag);
      }
    }

    closeEtajSelector();
  }

  function resetEtajSelection() {
    var cbs = etajSelectorModal ? etajSelectorModal.querySelectorAll('.etaj-selector-cb') : [];
    for (var i = 0; i < cbs.length; i++) cbs[i].checked = false;
    renderEtajSelectorChips();
  }

  var etajTriggerButtons = document.querySelectorAll('.js-open-etaj-selector');
  for (var b = 0; b < etajTriggerButtons.length; b++) {
    etajTriggerButtons[b].addEventListener('click', openEtajSelector);
  }
  if (etajSelectorList) {
    etajSelectorList.addEventListener('change', function() { setTimeout(renderEtajSelectorChips, 0); });
  }
  if (etajSelectorDone) etajSelectorDone.addEventListener('click', applyEtajSelection);
  if (etajSelectorReset) etajSelectorReset.addEventListener('click', resetEtajSelection);
  if (etajSelectorClose) etajSelectorClose.addEventListener('click', closeEtajSelector);
  if (etajSelectorOverlay) etajSelectorOverlay.addEventListener('click', closeEtajSelector);

  // ===== ESC KEY =====
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' || e.keyCode === 27) {
      if (etajSelectorModal && etajSelectorModal.classList.contains('open')) {
        closeEtajSelector();
      } else if (zoneSelectorModal && zoneSelectorModal.classList.contains('open')) {
        closeZoneSelector();
      } else if (filtersPanel && filtersPanel.classList.contains('open')) {
        closeFilters();
      }
    }
  });

  // ===== FILTER FORM SUBMIT =====
  var filtersForm = document.getElementById('filters-form');
  if (filtersForm) {
    filtersForm.addEventListener('submit', function() {
      closeFilters();
    });
  }
})();
