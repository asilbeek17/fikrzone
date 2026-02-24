/* ════════════════════════════════════════════════════════════════════════════
   Block Editor — Django Admin Custom JS
   Builds a visual block editor over the standard Django inlines
   ════════════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  // Wait for DOM + CKEditor to be ready
  document.addEventListener('DOMContentLoaded', function () {
    // Only run on post change/add pages
    const inlineGroup = document.getElementById('contentblock_set-group');
    if (!inlineGroup) return;

    initBlockEditor(inlineGroup);
  });

  function initBlockEditor(inlineGroup) {
    // ── Build the custom editor UI above the hidden inline forms ────────────
    const editorWrapper = document.createElement('div');
    editorWrapper.id = 'block-editor-wrapper';
    editorWrapper.innerHTML = `
      <div class="block-editor-header">
        <h3>Content Blocks</h3>
        <div class="block-add-buttons">
          <button type="button" class="block-add-btn btn-text"  data-type="text">
            ✎ Text
          </button>
          <button type="button" class="block-add-btn btn-image" data-type="image">
            🖼 Image
          </button>
          <button type="button" class="block-add-btn btn-video" data-type="video">
            ▶ Video
          </button>
          <button type="button" class="block-add-btn btn-audio" data-type="audio">
            ♪ Audio
          </button>
        </div>
      </div>
      <div id="blocks-container">
        <div class="block-empty-prompt" id="emptyPrompt">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#818cf8" stroke-width="1.5">
            <rect x="3" y="3" width="18" height="18" rx="2"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/>
          </svg>
          <p>No blocks yet</p>
          <p class="hint">Use the buttons above to add text, images, video or audio</p>
        </div>
      </div>
    `;

    inlineGroup.parentNode.insertBefore(editorWrapper, inlineGroup);
    inlineGroup.style.display = 'none'; // hide raw inline forms but keep them in DOM

    const container     = document.getElementById('blocks-container');
    const emptyPrompt   = document.getElementById('emptyPrompt');
    const addButtons    = editorWrapper.querySelectorAll('.block-add-btn');

    // ── Detect existing inline forms (for edit pages) ────────────────────────
    const existingForms = inlineGroup.querySelectorAll('.inline-related:not(.empty-form)');
    let blockCount = 0;

    existingForms.forEach((form, idx) => {
      const prefix  = getFormPrefix(form);
      if (!prefix) return;

      const typeEl  = form.querySelector(`[name$="-block_type"]`);
      if (!typeEl)  return;
      const type    = typeEl.value || 'text';

      renderBlock(prefix, type, form, idx);
      blockCount++;
    });

    updateEmptyState();

    // ── Add block buttons ────────────────────────────────────────────────────
    addButtons.forEach(btn => {
      btn.addEventListener('click', () => addBlock(btn.dataset.type));
    });

    // ── Sortable drag-and-drop ───────────────────────────────────────────────
    if (typeof Sortable !== 'undefined') {
      Sortable.create(container, {
        handle: '.block-drag-handle',
        animation: 180,
        ghostClass: 'sortable-ghost',
        chosenClass: 'sortable-chosen',
        onEnd: reindexPositions,
      });
    }

    // ────────────────────────────────────────────────────────────────────────
    // Core functions
    // ────────────────────────────────────────────────────────────────────────

    function addBlock(type) {
      // Clone the empty form template
      const emptyForm = inlineGroup.querySelector('.empty-form');
      if (!emptyForm) { console.warn('No empty form template found'); return; }

      const totalInput = inlineGroup.querySelector('[name$="-TOTAL_FORMS"]');
      const total      = parseInt(totalInput.value, 10);

      // Clone and update prefix
      const newForm    = emptyForm.cloneNode(true);
      newForm.classList.remove('empty-form');
      newForm.id = newForm.id.replace('__prefix__', total);

      // Update all input names/ids
      newForm.querySelectorAll('input, select, textarea, label').forEach(el => {
        ['name', 'id', 'for', 'data-ckeditor-basepath'].forEach(attr => {
          if (el.getAttribute(attr)) {
            el.setAttribute(attr, el.getAttribute(attr).replace(/__prefix__/g, total));
          }
        });
      });

      // Set the block_type
      const typeSelect = newForm.querySelector('[name$="-block_type"]');
      if (typeSelect) typeSelect.value = type;

      inlineGroup.querySelector('.inline-group, fieldset, .tabular, tbody, .stacked').appendChild(newForm);

      totalInput.value = total + 1;

      const prefix = `contentblock_set-${total}`;
      renderBlock(prefix, type, newForm, total);
      blockCount++;
      updateEmptyState();
      reindexPositions();
    }

    function renderBlock(prefix, type, sourceForm, index) {
      const blockEl = document.createElement('div');
      blockEl.className = 'block-item';
      blockEl.dataset.prefix = prefix;
      blockEl.dataset.type   = type;

      const typeLabels = { text: 'Text', image: 'Image', video: 'Video', audio: 'Audio' };
      const typeLabel  = typeLabels[type] || type;
      const typeIcons  = { text: '✎', image: '🖼', video: '▶', audio: '♪' };
      const icon       = typeIcons[type] || '•';

      blockEl.innerHTML = `
        <div class="block-header">
          <span class="block-drag-handle" title="Drag to reorder">⠿</span>
          <span class="block-type-badge badge-${type}">${icon} ${typeLabel}</span>
          <span class="block-preview-text" id="preview-${prefix}">—</span>
          <div class="block-header-actions">
            <button type="button" class="block-move-btn move-up"   title="Move up">↑</button>
            <button type="button" class="block-move-btn move-down" title="Move down">↓</button>
            <button type="button" class="block-toggle-btn"         title="Collapse/expand">−</button>
            <button type="button" class="block-delete-btn"         title="Delete block">✕</button>
          </div>
          <span class="block-position-num" id="posnum-${prefix}"></span>
        </div>
        <div class="block-body" id="body-${prefix}">
          ${buildBlockFields(prefix, type, sourceForm)}
        </div>
      `;

      // Remove from container first to avoid duplicates
      const existing = container.querySelector(`[data-prefix="${prefix}"]`);
      if (existing) existing.remove();

      container.appendChild(blockEl);

      // Wire events
      wireBlockEvents(blockEl, prefix, type, sourceForm);
      updatePreview(prefix, type);
    }

    function buildBlockFields(prefix, type, sourceForm) {
      if (type === 'text') {
        // Get the actual textarea from the hidden form (CKEditor target)
        const textarea = sourceForm.querySelector(`[name="${prefix}-text_content"]`);
        const taId     = textarea ? textarea.id : `id_${prefix}-text_content`;
        return `
          <label class="block-field-label">Content (rich text)</label>
          <div class="block-ck-placeholder" data-textarea-id="${taId}">
            <em style="color:#3f3f46;font-size:.85rem;">Loading editor…</em>
          </div>
        `;
      }

      if (type === 'image') {
        const imgInput = sourceForm ? sourceForm.querySelector(`[name="${prefix}-image"]`) : null;
        const hasImage = imgInput && imgInput.closest('.field-image')
          ? !!imgInput.closest('.field-image').querySelector('a') : false;
        const currentSrc = hasImage
          ? imgInput.closest('.field-image').querySelector('a')?.href : '';

        return `
          <label class="block-field-label">Image file</label>
          <input type="file" accept="image/*"
            id="id_${prefix}-image" name="${prefix}-image"
            style="color:#e4e4e7;font-size:.85rem;"
            onchange="blockEditorImagePreview(this, '${prefix}')" />
          <div class="block-image-preview" id="imgprev-${prefix}" style="${currentSrc ? '' : 'display:none'}">
            ${currentSrc ? `<img src="${currentSrc}" /><div class="block-image-preview-label">Current image</div>` : ''}
          </div>
          <label class="block-field-label" style="margin-top:.75rem;">Layout</label>
          <select class="block-layout-select" name="${prefix}-image_layout" id="id_${prefix}-image_layout">
            <option value="full">Full width</option>
            <option value="wide">Wide (80%)</option>
            <option value="center">Centered (60%)</option>
            <option value="left">Float left</option>
            <option value="right">Float right</option>
          </select>
          <label class="block-field-label" style="margin-top:.75rem;">Caption</label>
          <input type="text" class="block-caption-input"
            name="${prefix}-caption" id="id_${prefix}-caption"
            placeholder="Optional caption…"
            oninput="updateBlockPreview('${prefix}', 'image', this.value)" />
        `;
      }

      if (type === 'video') {
        return `
          <label class="block-field-label">Video file</label>
          <input type="file" accept="video/*"
            id="id_${prefix}-video" name="${prefix}-video"
            style="color:#e4e4e7;font-size:.85rem;"
            onchange="blockEditorVideoPreview(this, '${prefix}')" />
          <div class="block-media-preview" id="vidprev-${prefix}" style="display:none"></div>
          <label class="block-field-label" style="margin-top:.75rem;">Caption</label>
          <input type="text" class="block-caption-input"
            name="${prefix}-caption" id="id_${prefix}-caption"
            placeholder="Optional caption…"
            oninput="updateBlockPreview('${prefix}', 'video', this.value)" />
        `;
      }

      if (type === 'audio') {
        return `
          <label class="block-field-label">Audio file</label>
          <input type="file" accept="audio/*"
            id="id_${prefix}-audio" name="${prefix}-audio"
            style="color:#e4e4e7;font-size:.85rem;"
            onchange="blockEditorAudioPreview(this, '${prefix}')" />
          <div class="block-media-preview" id="audprev-${prefix}" style="display:none"></div>
          <label class="block-field-label" style="margin-top:.75rem;">Caption</label>
          <input type="text" class="block-caption-input"
            name="${prefix}-caption" id="id_${prefix}-caption"
            placeholder="Optional caption…"
            oninput="updateBlockPreview('${prefix}', 'audio', this.value)" />
        `;
      }

      return '';
    }

    function wireBlockEvents(blockEl, prefix, type, sourceForm) {
      // Toggle collapse
      const toggleBtn = blockEl.querySelector('.block-toggle-btn');
      const body      = blockEl.querySelector('.block-body');
      toggleBtn.addEventListener('click', () => {
        const collapsed = body.classList.toggle('collapsed');
        toggleBtn.textContent = collapsed ? '+' : '−';
      });

      // Move up/down
      blockEl.querySelector('.move-up').addEventListener('click', () => {
        const prev = blockEl.previousElementSibling;
        if (prev && prev.classList.contains('block-item')) {
          container.insertBefore(blockEl, prev);
          reindexPositions();
        }
      });
      blockEl.querySelector('.move-down').addEventListener('click', () => {
        const next = blockEl.nextElementSibling;
        if (next && next.classList.contains('block-item')) {
          container.insertBefore(next, blockEl);
          reindexPositions();
        }
      });

      // Delete
      blockEl.querySelector('.block-delete-btn').addEventListener('click', () => {
        if (!confirm('Delete this block?')) return;
        // Mark hidden form for deletion
        const deleteInput = document.querySelector(`#id_${prefix}-DELETE`);
        if (deleteInput) deleteInput.checked = true;
        blockEl.style.transition = 'opacity .25s, transform .25s';
        blockEl.style.opacity = '0';
        blockEl.style.transform = 'scale(.96)';
        setTimeout(() => { blockEl.remove(); blockCount--; updateEmptyState(); reindexPositions(); }, 260);
      });

      // For text blocks, init CKEditor on the placeholder
      if (type === 'text') {
        setTimeout(() => initCKInBlock(prefix, sourceForm), 100);
      }
    }

    function initCKInBlock(prefix, sourceForm) {
      const placeholder = document.querySelector(`.block-ck-placeholder[data-textarea-id="id_${prefix}-text_content"]`);
      if (!placeholder) return;

      // Get the real textarea from the hidden inline form
      const textarea = sourceForm.querySelector(`[name="${prefix}-text_content"]`)
                    || document.querySelector(`[name="${prefix}-text_content"]`);
      if (!textarea) { placeholder.innerHTML = '<em style="color:#f87171">Editor unavailable</em>'; return; }

      // Move the textarea into our block (CKEditor needs it in the visible DOM)
      textarea.style.display = 'block';
      textarea.style.width   = '100%';
      placeholder.replaceWith(textarea);

      // Trigger Django CKEditor 5 initialization if not already done
      if (window.ClassicEditor) {
        ClassicEditor.create(textarea, {
          toolbar: {
            items: [
              'heading', '|',
              'bold', 'italic', 'underline', 'strikethrough', '|',
              'link', 'blockQuote', 'code', '|',
              'bulletedList', 'numberedList', '|',
              'imageUpload', 'mediaEmbed', '|',
              'undo', 'redo',
            ],
            shouldNotGroupWhenFull: false,
          },
          language: 'en',
        }).then(editor => {
          editor.model.document.on('change:data', () => {
            const text = editor.getData().replace(/<[^>]+>/g, '').trim();
            const preview = document.getElementById(`preview-${prefix}`);
            if (preview) preview.textContent = text.slice(0, 80) || '(empty)';
          });
          // Trigger initial preview
          const text = editor.getData().replace(/<[^>]+>/g, '').trim();
          const preview = document.getElementById(`preview-${prefix}`);
          if (preview) preview.textContent = text.slice(0, 80) || '(empty)';
        }).catch(err => console.warn('CKEditor init:', err));
      }
    }

    function updatePreview(prefix, type) {
      const preview = document.getElementById(`preview-${prefix}`);
      if (!preview) return;
      if (type === 'text')  preview.textContent = 'Text block';
      if (type === 'image') preview.textContent = 'Image block — choose a file below';
      if (type === 'video') preview.textContent = 'Video block — choose a file below';
      if (type === 'audio') preview.textContent = 'Audio block — choose a file below';
    }

    function reindexPositions() {
      const items = container.querySelectorAll('.block-item');
      items.forEach((item, i) => {
        const prefix = item.dataset.prefix;
        // Update position field in hidden form
        const posInput = document.querySelector(`[name="${prefix}-position"]`);
        if (posInput) posInput.value = i;
        // Update visual number
        const num = document.getElementById(`posnum-${prefix}`);
        if (num) num.textContent = `#${i + 1}`;
      });
    }

    function updateEmptyState() {
      const hasBlocks = container.querySelectorAll('.block-item').length > 0;
      emptyPrompt.style.display = hasBlocks ? 'none' : 'flex';
    }

    function getFormPrefix(formEl) {
      // Extract prefix from the form's id, e.g. "contentblock_set-0"
      const match = formEl.id && formEl.id.match(/contentblock_set-(\d+)/);
      if (match) return `contentblock_set-${match[1]}`;
      return null;
    }
  }

  // ── Global helpers (called from inline HTML event handlers) ───────────────

  window.blockEditorImagePreview = function (input, prefix) {
    const preview = document.getElementById(`imgprev-${prefix}`);
    if (!preview) return;
    if (!input.files || !input.files[0]) { preview.style.display = 'none'; return; }
    const url = URL.createObjectURL(input.files[0]);
    preview.innerHTML = `<img src="${url}" style="max-height:200px;width:100%;object-fit:cover;" /><div class="block-image-preview-label">${input.files[0].name}</div>`;
    preview.style.display = 'block';
    const previewText = document.getElementById(`preview-${prefix}`);
    if (previewText) previewText.textContent = input.files[0].name;
  };

  window.blockEditorVideoPreview = function (input, prefix) {
    const preview = document.getElementById(`vidprev-${prefix}`);
    if (!preview) return;
    if (!input.files || !input.files[0]) { preview.style.display = 'none'; return; }
    const url = URL.createObjectURL(input.files[0]);
    preview.innerHTML = `<video src="${url}" controls style="width:100%;border-radius:4px;"></video>`;
    preview.style.display = 'block';
    const previewText = document.getElementById(`preview-${prefix}`);
    if (previewText) previewText.textContent = input.files[0].name;
  };

  window.blockEditorAudioPreview = function (input, prefix) {
    const preview = document.getElementById(`audprev-${prefix}`);
    if (!preview) return;
    if (!input.files || !input.files[0]) { preview.style.display = 'none'; return; }
    const url = URL.createObjectURL(input.files[0]);
    preview.innerHTML = `<audio src="${url}" controls style="width:100%;"></audio>`;
    preview.style.display = 'block';
    const previewText = document.getElementById(`preview-${prefix}`);
    if (previewText) previewText.textContent = input.files[0].name;
  };

  window.updateBlockPreview = function (prefix, type, value) {
    const preview = document.getElementById(`preview-${prefix}`);
    if (preview && value) preview.textContent = value;
  };

})();
