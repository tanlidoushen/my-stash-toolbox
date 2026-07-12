// Stash Subtitle Assistant UI. This file only renders UI and calls Stash's same-origin GraphQL API.
// Subtitle search, download, saving, and scanning run in subtitle_assistant_backend.py.
(() => {
  'use strict';
  const PLUGIN_ID = 'StashSubtitleAssistant';
  let initializing = false;
  let panelVisible = false;

  const sceneId = () => (location.pathname.match(/^\/scenes\/(\d+)/) || [])[1] || null;
  const byId = (id) => document.getElementById(id);
  const setStatus = (text) => { const output = byId('stash-test-output'); if (output) output.textContent = text; };

  async function backend(mode, args = {}) {
    const query = `mutation RunPluginOperation($plugin_id: ID!, $args: Map!) {
      runPluginOperation(plugin_id: $plugin_id, args: $args)
    }`;
    const response = await fetch('/graphql', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, variables: { plugin_id: PLUGIN_ID, args: { mode, ...args } } }),
    });
    const payload = await response.json();
    if (!response.ok || payload.errors) throw new Error(payload.errors?.[0]?.message || `请求失败 (${response.status})`);
    const value = payload.data?.runPluginOperation;
    const output = value?.output || value;
    if (!output?.success) throw new Error(output?.message || '后端操作失败');
    return output.result;
  }

  function textCell(row, value) { const cell = document.createElement('td'); cell.textContent = value; row.appendChild(cell); }
  function button(label, className, handler) { const b = document.createElement('button'); b.className = `btn btn-sm ${className}`; b.type = 'button'; b.textContent = label; b.onclick = handler; return b; }

  function showResults(items) {
    const body = byId('stash-subtitle-tbody'); const container = byId('stash-subtitle-results');
    body.replaceChildren();
    items.forEach((item) => {
      const row = document.createElement('tr');
      textCell(row, item.name); textCell(row, item.ext); textCell(row, item.source);
      const actions = document.createElement('td'); actions.className = 'stash-subtitle-actions';
      actions.append(button('预览', 'btn-primary', () => preview(item)));
      actions.append(button('保存到媒体目录', 'btn-success', () => save(item)));
      row.appendChild(actions); body.appendChild(row);
    });
    container.style.display = items.length ? 'block' : 'none';
  }

  async function search() {
    const keyword = byId('stash-subtitle-input').value.trim();
    if (!keyword) return setStatus('请输入番号或关键词');
    setStatus(`正在由后端搜索：${keyword}`);
    try { const { items } = await backend('search', { keyword }); showResults(items); setStatus(`找到 ${items.length} 个字幕`); }
    catch (error) { setStatus(`搜索失败：${error.message}`); }
  }

  async function preview(item) {
    setStatus('正在由后端读取字幕…');
    try {
      const { content, truncated } = await backend('preview', { url: item.url });
      const modal = document.createElement('div'); modal.className = 'stash-test-modal';
      const box = document.createElement('div'); box.className = 'stash-test-modal-box';
      const title = document.createElement('strong'); title.textContent = item.name;
      const close = button('关闭', 'btn-secondary', () => modal.remove());
      const pre = document.createElement('pre'); pre.textContent = content + (truncated ? '\n\n[内容过长，已截断]' : '');
      const footer = document.createElement('div'); footer.append(button('保存到媒体目录', 'btn-success', () => { modal.remove(); save(item); }), close);
      box.append(title, pre, footer); modal.appendChild(box); modal.onclick = (e) => { if (e.target === modal) modal.remove(); }; document.body.appendChild(modal); setStatus('预览已打开');
    } catch (error) { setStatus(`预览失败：${error.message}`); }
  }

  async function save(item) {
    const id = sceneId(); if (!id) return setStatus('未能识别当前场景');
    setStatus('正在由后端下载并上传字幕…');
    try {
      const { filename, scanned, scan_error } = await backend('save', { scene_id: id, url: item.url, ext: item.ext });
      setStatus(scanned ? `已保存 ${filename}，并已触发 Stash 扫描。` : `已保存 ${filename}；自动扫描失败，请在 Stash 中手动扫描该目录。${scan_error ? `（${scan_error}）` : ''}`);
    }
    catch (error) { setStatus(`保存失败：${error.message}`); }
  }

  function addStyles() {
    if (byId('stash-test-css')) return;
    const style = document.createElement('style'); style.id = 'stash-test-css'; style.textContent = `
      .tab-content.stash-test-active > .tab-pane { display:none!important; } .tab-content.stash-test-active > #stash-test-panel { display:block!important; } #stash-test-toolbar-btn.test-active { color:#007bff!important; }
      #stash-subtitle-results{display:none;margin-top:12px;overflow-x:auto} #stash-subtitle-results table{width:100%;min-width:560px;table-layout:fixed;color:#fff;font-size:13px} #stash-subtitle-results th,#stash-subtitle-results td{padding:6px 8px;border-bottom:1px solid #333;vertical-align:top}
      #stash-subtitle-results th:first-child,#stash-subtitle-results td:first-child{width:24%;overflow-wrap:anywhere;word-break:break-word} #stash-subtitle-results th:nth-child(2),#stash-subtitle-results td:nth-child(2){width:8%} #stash-subtitle-results th:nth-child(3),#stash-subtitle-results td:nth-child(3){width:12%;overflow-wrap:anywhere}
      #stash-subtitle-results .btn{margin:2px}.stash-subtitle-actions{width:56%;white-space:normal}.stash-subtitle-actions .btn{white-space:nowrap}.stash-search-row{display:flex;gap:8px;flex-wrap:wrap}.stash-search-row input{flex:1;min-width:180px;background:#2d2d2d;border:1px solid #444;color:#fff;padding:6px 10px;border-radius:4px}
      #stash-test-output{background:#1a1a1a;color:#b8f5c1;padding:8px 12px;border-radius:4px;margin-top:8px;white-space:pre-wrap}.stash-test-modal{position:fixed;inset:0;z-index:99999;background:#000b;display:flex;align-items:center;justify-content:center}.stash-test-modal-box{background:#242424;color:#fff;width:min(900px,90vw);max-height:90vh;padding:16px;border-radius:8px;display:flex;flex-direction:column;gap:12px}.stash-test-modal pre{margin:0;overflow:auto;white-space:pre-wrap;background:#171717;padding:12px}.stash-test-modal-box footer{display:flex;gap:8px;justify-content:flex-end}`;
    document.head.appendChild(style);
  }

  async function init() {
    if (initializing || byId('stash-test-toolbar-btn') || !sceneId()) return;
    initializing = true;
    try {
      const toolbarGroups = document.querySelectorAll('.scene-toolbar-group');
      if (!toolbarGroups.length) return;
      const toolbar = toolbarGroups[toolbarGroups.length - 1];
      const navTabs = document.querySelector('.nav-tabs');
      const firstPane = document.querySelector('.tab-content .tab-pane');
      const tabContent = firstPane ? firstPane.parentElement : (navTabs ? navTabs.nextElementSibling : null);
      if (!toolbar || !tabContent) return; addStyles();
      const panel = document.createElement('div'); panel.id = 'stash-test-panel'; panel.className = 'tab-pane';
      panel.innerHTML = `<div style="padding:16px 20px"><h4>字幕工具</h4><div class="stash-search-row"><input id="stash-subtitle-input" placeholder="输入番号或关键词"><button class="btn btn-primary" id="stash-search-btn">搜索字幕</button></div><div id="stash-test-output">就绪</div><div id="stash-subtitle-results"><table><thead><tr><th>文件名</th><th>格式</th><th>来源</th><th>操作</th></tr></thead><tbody id="stash-subtitle-tbody"></tbody></table></div></div>`;
      tabContent.appendChild(panel); byId('stash-search-btn').onclick = search; byId('stash-subtitle-input').onkeydown = (e) => { if (e.key === 'Enter') search(); };
      const toolbarButton = document.createElement('button'); toolbarButton.id = 'stash-test-toolbar-btn'; toolbarButton.className = 'minimal btn btn-secondary'; toolbarButton.type = 'button'; toolbarButton.title = '字幕工具';
      toolbarButton.innerHTML = `<svg aria-hidden="true" focusable="false" data-prefix="fas" data-icon="bars" class="svg-inline--fa fa-bars fa-icon" role="img" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512" width="16" height="16"><path fill="currentColor" d="M0 96C0 78.3 14.3 64 32 64h384c17.7 0 32 14.3 32 32s-14.3 32-32 32H32C14.3 128 0 113.7 0 96zm0 160c0-17.7 14.3-32 32-32h384c17.7 0 32 14.3 32 32s-14.3 32-32 32H32c-17.7 0-32-14.3-32-32zm448 160c0 17.7-14.3 32-32 32H32c-17.7 0-32-14.3-32-32s14.3-32 32-32h384c17.7 0 32 14.3 32 32z"></path></svg>`;
      toolbarButton.onclick = async () => {
        panelVisible = !panelVisible;
        if (panelVisible) {
          navTabs?.querySelectorAll('.nav-link').forEach((link) => link.classList.remove('active'));
          tabContent.classList.add('stash-test-active');
          toolbarButton.classList.add('test-active');
          try { byId('stash-subtitle-input').value = (await backend('scene_info', { scene_id: sceneId() })).keyword; }
          catch (e) { setStatus(`读取场景失败：${e.message}`); }
        } else {
          tabContent.classList.remove('stash-test-active');
          toolbarButton.classList.remove('test-active');
          navTabs?.querySelector('.nav-link')?.click();
        }
      };
      // Insert before the operations dropdown, matching SpriteTab's layout.
      const operationsDropdown = toolbar.querySelector('.dropdown');
      if (operationsDropdown && operationsDropdown.parentElement === toolbar) {
        toolbar.insertBefore(toolbarButton, operationsDropdown);
      } else if (operationsDropdown && operationsDropdown.parentElement?.parentElement === toolbar) {
        toolbar.insertBefore(toolbarButton, operationsDropdown.parentElement);
      } else {
        toolbar.appendChild(toolbarButton);
      }
      // Return to Stash's normal tab view whenever a native tab is selected.
      navTabs?.addEventListener('click', (event) => {
        if (event.target.closest('.nav-link')) {
          panelVisible = false;
          tabContent.classList.remove('stash-test-active');
          toolbarButton.classList.remove('test-active');
        }
      }, { capture: true });
    } finally { initializing = false; }
  }

  new MutationObserver(() => { if (sceneId()) init(); else { byId('stash-test-panel')?.remove(); byId('stash-test-toolbar-btn')?.remove(); panelVisible = false; } }).observe(document.body, { childList: true, subtree: true });
  setTimeout(init, 500);
})();
