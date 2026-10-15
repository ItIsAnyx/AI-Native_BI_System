(() => {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  const icon = (n) => `<svg class="ic" aria-hidden="true"><use href="#i-${n}"/></svg>`;
  const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };

  /* ---------- Демо-данные ---------- */
  const projects = [];   // { id, name, open }
  let chats = [];        // { id, title, project, messages: [] }
  const ctxName = (c) => { const p = projects.find(p => p.id === c.project); return 'Рабочее пространство · ' + (p ? p.name : 'Личное'); };

  const state = { user: null, active: null, query: '', pending: false, files: [], counter: 100 };

  /* ---------- Хранилище (необязательное) ---------- */
  const store = {
    get() { try { return JSON.parse(localStorage.getItem('aster-user')); } catch (e) { return null; } },
    set(v) { try { v ? localStorage.setItem('aster-user', JSON.stringify(v)) : localStorage.removeItem('aster-user'); } catch (e) {} },
  };

  /* ---------- Элементы ---------- */
  const loginView = $('#login-view'), appView = $('#app-view');
  const form = $('#login-form'), email = $('#email'), pass = $('#password');
  const toastEl = $('#toast'); let toastT;
  function toast(msg) { toastEl.textContent = msg; toastEl.hidden = false; clearTimeout(toastT); toastT = setTimeout(() => toastEl.hidden = true, 2600); }

  /* ======================= ВХОД ======================= */
  let signup = false;
  const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

  function setErr(input, errId, msg) {
    $('#' + errId).textContent = msg || '';
    input.closest('.input-wrap').classList.toggle('invalid', !!msg);
    input.setAttribute('aria-invalid', msg ? 'true' : 'false');
  }
  function validate() {
    let ok = true;
    const e = email.value.trim(), p = pass.value;
    if (!e) { setErr(email, 'email-err', 'Введите email.'); ok = false; }
    else if (!EMAIL_RE.test(e)) { setErr(email, 'email-err', 'Проверьте формат адреса, например name@company.com.'); ok = false; }
    else setErr(email, 'email-err');
    if (!p) { setErr(pass, 'password-err', 'Введите пароль.'); ok = false; }
    else if (p.length < 6) { setErr(pass, 'password-err', 'Пароль должен содержать не менее 6 символов.'); ok = false; }
    else setErr(pass, 'password-err');
    return ok;
  }
  email.addEventListener('input', () => { if ($('#email-err').textContent) validate(); $('#form-error').hidden = true; });
  pass.addEventListener('input', () => { if ($('#password-err').textContent) validate(); $('#form-error').hidden = true; });

  $('#toggle-pass').addEventListener('click', (ev) => {
    const show = pass.type === 'password';
    pass.type = show ? 'text' : 'password';
    ev.currentTarget.setAttribute('aria-pressed', String(show));
    ev.currentTarget.setAttribute('aria-label', show ? 'Скрыть пароль' : 'Показать пароль');
    ev.currentTarget.querySelector('use').setAttribute('href', show ? '#i-eyeoff' : '#i-eye');
  });

  function setLoading(btn, on, label) {
    btn.classList.toggle('loading', on); btn.disabled = on;
    $('#submit-label').textContent = on ? 'Подождите…' : label;
  }
  const submitLabel = () => signup ? 'Создать аккаунт' : 'Войти';

  form.addEventListener('submit', (ev) => {
    ev.preventDefault();
    $('#form-error').hidden = true;
    if (!validate()) { (!email.value.trim() || !EMAIL_RE.test(email.value.trim()) ? email : pass).focus(); return; }
    const btn = $('#submit-btn');
    setLoading(btn, true, submitLabel());
    setTimeout(() => {
      setLoading(btn, false, submitLabel());
      if (email.value.trim().toLowerCase() === 'error@aster.app') {
        $('#form-error-text').textContent = 'Не удалось войти: неверный email или пароль. Попробуйте ещё раз.';
        $('#form-error').hidden = false; return;
      }
      login(email.value.trim());
    }, 900);
  });

  $('#demo-btn').addEventListener('click', () => login('demo@aster.app'));
  $('#forgot-link').addEventListener('click', (e) => { e.preventDefault(); toast('Демо: письмо для восстановления пароля не отправляется.'); });
  $('#switch-line').addEventListener('click', (e) => {
    if (!e.target.closest('#signup-link')) return;
    e.preventDefault(); signup = !signup;
    $('#login-title').textContent = signup ? 'Создайте аккаунт' : 'С возвращением';
    $('#login-sub').textContent = signup ? 'Начните вдумчиво планировать, писать и исследовать с Aster.' : 'Войдите, чтобы продолжить планирование, письмо и исследования.';
    $('#submit-label').textContent = submitLabel();
    $('#switch-line').innerHTML = signup ? 'Уже есть аккаунт? <a href="#" id="signup-link" class="link">Войти</a>' : 'Нет аккаунта? <a href="#" id="signup-link" class="link">Зарегистрироваться</a>';
    pass.autocomplete = signup ? 'new-password' : 'current-password';
  });

  function login(mail) {
    state.user = { mail };
    store.set(state.user);
    $('#account-mail').textContent = mail;
    const name = mail === 'demo@aster.app' ? 'Анна Крылова' : mail.split('@')[0];
    $('#account-name').textContent = name;
    $('.avatar').textContent = (name.match(/\p{L}/gu) || ['A']).slice(0, 2).join('').toUpperCase();
    show('app');
  }
  function logout() {
    state.user = null; store.set(null); closeDrawer();
    form.reset(); setErr(email, 'email-err'); setErr(pass, 'password-err'); $('#form-error').hidden = true;
    show('login'); toast('Вы вышли из аккаунта.');
  }
  $('#logout-btn').addEventListener('click', logout);

  function show(which) {
    loginView.hidden = which !== 'login';
    appView.hidden = which !== 'app';
    if (which === 'app') { renderSidebar(); openChat(state.active); }
    else email.focus({ preventScroll: true });
  }

  /* ======================= САЙДБАР ======================= */
  const search = $('#chat-search');
  search.addEventListener('input', () => { state.query = search.value.trim().toLowerCase(); renderSidebar(); });

  function chatRow(c) {
    const li = el('li', 'chat-item');
    const b = el('button', 'row' + (c.id === state.active ? ' active' : ''), `${icon('chat')}<span class="lbl"></span>`);
    b.querySelector('.lbl').textContent = c.title;
    b.type = 'button';
    if (c.id === state.active) b.setAttribute('aria-current', 'page');
    b.addEventListener('click', () => { openChat(c.id); closeDrawer(); });
    const acts = el('div', 'row-actions');
    acts.append(
      actionBtn('', 'move', 'Переместить чат «' + c.title + '» в проект', () => askMove(c.id)),
      actionBtn('del-btn', 'trash', 'Удалить чат «' + c.title + '»', () => askDelete(c.id))
    );
    li.append(b, acts); return li;
  }
  function actionBtn(cls, iconName, label, onClick) {
    const b = el('button', ('act-btn ' + cls).trim(), icon(iconName));
    b.type = 'button'; b.setAttribute('aria-label', label); b.addEventListener('click', onClick);
    return b;
  }

  /* Удаление чата */
  const dlg = $('#confirm-dialog');
  let deleteId = null;
  function askDelete(id) {
    const c = chats.find(x => x.id === id); if (!c) return;
    deleteId = id;
    $('#confirm-text').textContent = 'Чат «' + c.title + '» будет удалён без возможности восстановления.';
    dlg.showModal();
    $('#confirm-cancel').focus();
  }
  function deleteChat(id) {
    const idx = chats.findIndex(c => c.id === id); if (idx < 0) return;
    const title = chats[idx].title;
    chats.splice(idx, 1);
    if (state.active === id) {
      const next = chats[idx] || chats[idx - 1];
      openChat(next ? next.id : null);
      if (matchMedia('(max-width:860px)').matches) $('#new-chat').focus();
    } else {
      renderSidebar();
    }
    toast('Чат «' + title + '» удалён.');
  }
  $('#confirm-ok').addEventListener('click', () => { dlg.close(); if (deleteId) deleteChat(deleteId); deleteId = null; });
  $('#confirm-cancel').addEventListener('click', () => { dlg.close(); deleteId = null; });
  dlg.addEventListener('click', (e) => { if (e.target === dlg) { dlg.close(); deleteId = null; } });
  dlg.addEventListener('cancel', () => { deleteId = null; });

  function renderSidebar() {
    const q = state.query, match = (c) => !q || c.title.toLowerCase().includes(q);
    const pl = $('#projects'), rl = $('#recent');
    pl.innerHTML = ''; rl.innerHTML = '';
    let found = 0;
    projects.forEach(p => {
      const items = chats.filter(c => c.project === p.id && match(c));
      if (q && !items.length && !p.name.toLowerCase().includes(q)) return;
      const open = q ? items.length > 0 : p.open;
      const li = el('li');
      const head = el('button', 'row',`${icon('folder')}<span class="lbl"></span><span class="count">${chats.filter(c => c.project === p.id).length}</span>${icon('chevron').replace('class="ic"', 'class="ic chev"')}`);
      head.type = 'button'; head.querySelector('.lbl').textContent = p.name;
      head.setAttribute('aria-expanded', String(open));
      head.addEventListener('click', () => { p.open = !p.open; renderSidebar(); });
      const pacts = el('div', 'row-actions');
      pacts.append(
        actionBtn('', 'plus', 'Новый чат в проекте «' + p.name + '»', () => newChat(p.id)),
        actionBtn('del-btn', 'trash', 'Удалить проект «' + p.name + '»', () => askDeleteProject(p.id))
      );
      const hw = el('div', 'chat-item');   // обёртка только вокруг строки проекта, чтобы кнопки центрировались по ней, а не по списку чатов
      hw.append(head, pacts); li.append(hw);
      if (open && items.length) { const ul = el('ul', 'sub'); items.forEach(c => ul.append(chatRow(c))); li.append(ul); }
      else if (open && !q) { const ul = el('ul', 'sub'); ul.append(el('li', 'sub-empty', 'В проекте пока нет чатов')); li.append(ul); }
      pl.append(li); found += items.length || 1;
    });
    chats.filter(c => !c.project && match(c)).forEach(c => { rl.append(chatRow(c)); found++; });
    $('#no-projects').hidden = projects.length > 0 || !!q;
    $('#no-results').textContent = q ? 'Ничего не найдено по запросу.' : 'Чатов пока нет.';
    $('#no-results').hidden = found > 0;
  }

  /* Удаление проекта */
  const pdlg = $('#project-dialog');
  let deleteProjectId = null;
  function askDeleteProject(id) {
    const p = projects.find(x => x.id === id); if (!p) return;
    const n = chats.filter(c => c.project === id).length;
    deleteProjectId = id;
    $('#project-text').textContent = n
      ? 'В проекте «' + p.name + '» чатов: ' + n + '. Оставить их в «Недавних» или удалить вместе с проектом?'
      : 'Проект «' + p.name + '» пуст и будет удалён.';
    $('#project-keep').hidden = n === 0;
    $('#project-all').textContent = n ? 'Удалить вместе с чатами' : 'Удалить';
    pdlg.showModal();
    $('#project-cancel').focus();
  }
  function deleteProject(id, withChats) {
    const idx = projects.findIndex(p => p.id === id); if (idx < 0) return;
    const name = projects[idx].name;
    const hadActive = !!current();
    projects.splice(idx, 1);
    if (withChats) chats = chats.filter(c => c.project !== id);
    else chats.forEach(c => { if (c.project === id) c.project = null; });
    if (hadActive && !current()) {
      openChat(chats.length ? chats[0].id : null);
    } else {
      if (current()) $('#chat-context').textContent = ctxName(current());
      renderSidebar();
    }
    toast('Проект «' + name + '» удалён.');
  }
  const closeP = () => { pdlg.close(); deleteProjectId = null; };
  $('#project-cancel').addEventListener('click', closeP);
  $('#project-keep').addEventListener('click', () => { const id = deleteProjectId; closeP(); if (id) deleteProject(id, false); });
  $('#project-all').addEventListener('click', () => { const id = deleteProjectId; closeP(); if (id) deleteProject(id, true); });
  pdlg.addEventListener('click', (e) => { if (e.target === pdlg) closeP(); });
  pdlg.addEventListener('cancel', () => { deleteProjectId = null; });

  /* Создание проекта */
  const npdlg = $('#new-project-dialog'), npForm = $('#new-project-form');
  const npInput = $('#new-project-name'), npErr = $('#new-project-err');
  let moveAfterCreate = null;   // id чата, который нужно переместить в только что созданный проект
  function openNewProject(chatId = null) {
    moveAfterCreate = chatId;
    npInput.value = ''; npErr.textContent = ''; npInput.removeAttribute('aria-invalid');
    $('#new-project-hint').hidden = !chatId;
    npdlg.showModal(); npInput.focus();
  }
  $('#add-project').addEventListener('click', () => openNewProject());
  npForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const name = npInput.value.trim().replace(/\s+/g, ' ');
    let err = '';
    if (!name) err = 'Введите название проекта.';
    else if (projects.some(p => p.name.toLowerCase() === name.toLowerCase())) err = 'Проект с таким названием уже существует.';
    npErr.textContent = err;
    if (err) { npInput.setAttribute('aria-invalid', 'true'); npInput.focus(); return; }
    const chatId = moveAfterCreate;
    const p = { id: 'p' + (++state.counter), name, open: true };
    projects.push(p);
    state.query = ''; search.value = '';
    npdlg.close();
    if (chatId) moveChat(chatId, p.id);
    else { renderSidebar(); toast('Проект «' + name + '» создан.'); }
  });
  npInput.addEventListener('input', () => { npErr.textContent = ''; npInput.removeAttribute('aria-invalid'); });
  $('#new-project-cancel').addEventListener('click', () => npdlg.close());
  npdlg.addEventListener('click', (e) => { if (e.target === npdlg) npdlg.close(); });
  npdlg.addEventListener('close', () => { moveAfterCreate = null; });

  /* Перенос чата в проект */
  const mdlg = $('#move-dialog');
  let moveId = null;
  function askMove(id) {
    const c = chats.find(x => x.id === id); if (!c) return;
    moveId = id;
    $('#move-text').textContent = 'Куда переместить чат «' + c.title + '»?';
    const list = $('#move-list'); list.innerHTML = '';
    const option = (label, iconName, pid) => {
      const li = el('li');
      const here = c.project === pid;
      const b = el('button', 'pick-item', `${icon(iconName)}<span class="lbl"></span>${here ? icon('check') : ''}`);
      b.type = 'button'; b.querySelector('.lbl').textContent = label;
      if (here) b.setAttribute('aria-current', 'true');
      b.addEventListener('click', () => { mdlg.close(); if (!here) moveChat(id, pid); });
      li.append(b); list.append(li);
    };
    projects.forEach(p => option(p.name, 'folder', p.id));
    option('Без проекта (Недавние)', 'chat', null);
    $('#move-empty').hidden = projects.length > 0;
    mdlg.showModal();
    (list.querySelector('.pick-item:not([aria-current])') || list.querySelector('.pick-item')).focus();
  }
  function moveChat(id, projectId) {
    const c = chats.find(x => x.id === id); if (!c) return;
    const p = projects.find(x => x.id === projectId);
    c.project = p ? p.id : null;
    if (p) p.open = true;
    if (state.active === id) $('#chat-context').textContent = ctxName(c);
    renderSidebar();
    toast(p ? 'Чат перемещён в проект «' + p.name + '».' : 'Чат перемещён в «Недавние».');
  }
  $('#move-cancel').addEventListener('click', () => mdlg.close());
  $('#move-new').addEventListener('click', () => { const id = moveId; mdlg.close(); openNewProject(id); });
  mdlg.addEventListener('click', (e) => { if (e.target === mdlg) mdlg.close(); });

  /* Drawer */
  const sidebar = $('#sidebar'), scrim = $('#scrim'), openBtn = $('#open-drawer');
  function openDrawer() { sidebar.classList.add('open'); scrim.hidden = false; openBtn.setAttribute('aria-expanded', 'true'); $('#close-drawer').focus(); }
  function closeDrawer() { sidebar.classList.remove('open'); scrim.hidden = true; openBtn.setAttribute('aria-expanded', 'false'); }
  openBtn.addEventListener('click', openDrawer);
  $('#close-drawer').addEventListener('click', () => { closeDrawer(); openBtn.focus(); });
  scrim.addEventListener('click', closeDrawer);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && sidebar.classList.contains('open')) { closeDrawer(); openBtn.focus(); } });
  window.matchMedia('(min-width:861px)').addEventListener('change', closeDrawer);


  /* ======================= ЧАТ ======================= */
  const thread = $('#thread'), prompt = $('#prompt'), sendBtn = $('#send-btn');
  const current = () => chats.find(c => c.id === state.active);

  function newChat(projectId = null) {
    state.query = ''; search.value = '';
    const proj = projects.find(p => p.id === projectId);
    if (!proj && !current()) {
      openChat(null);   // чатов нет — достаточно пустого экрана, чат появится при отправке
    } else {
      const pid = proj ? proj.id : null;
      const existing = chats.find(c => c.project === pid && c.messages.length === 0 && c.title === 'Новый чат');
      if (proj) proj.open = true;
      if (existing) openChat(existing.id);
      else {
        const c = { id: 'c' + (++state.counter), title: 'Новый чат', project: pid, messages: [] };
        chats.unshift(c); openChat(c.id);
      }
    }
    closeDrawer(); prompt.focus();
  }
  $('#new-chat').addEventListener('click', () => newChat());

  function openChat(id) {
    state.active = id; state.pending = false;
    const c = current();
    $('#chat-title').textContent = c ? c.title : 'Новый чат';
    $('#chat-context').textContent = c ? ctxName(c) : 'Рабочее пространство · Личное';
    selectTab('chat', false);
    renderSidebar(); renderThread();
    updateSend();
    if (!matchMedia('(max-width:860px)').matches) prompt.focus({ preventScroll: true });
  }

  function aiMessage(msg) {
    const w = el('div', 'msg-ai');
    w.append(el('span', 'logo', icon('spark')));
    const body = el('div', 'ai-body');
    if (msg.error) {
      body.innerHTML = `<div class="err-box"><p>${icon('alert')} Не удалось получить ответ. Проверьте соединение и повторите попытку.</p></div>`;
      const rb = el('button', 'btn btn-secondary btn-sm', `${icon('retry')} Повторить`); rb.type = 'button';
      rb.addEventListener('click', () => retry());
      body.querySelector('.err-box').append(rb);
    } else {
      body.innerHTML = `
        <h3>Предлагаемый план действий</h3>
        <p>Это заглушка ответа: так Aster структурирует рекомендации по вашему запросу.</p>
        <ol class="recs">
          <li><div><strong>Уточните цель и критерии успеха</strong><span>Сформулируйте результат в одном предложении и определите 2–3 измеримых показателя.</span></div></li>
          <li><div><strong>Разбейте работу на этапы</strong><span>Выделите короткие итерации с понятными владельцами и сроками.</span></div></li>
          <li><div><strong>Соберите нужные материалы</strong><span>Подготовьте источники, примеры и ограничения, которые стоит учесть.</span></div></li>
          <li><div><strong>Назначьте точку проверки</strong><span>Запланируйте короткий обзор, чтобы вовремя скорректировать курс.</span></div></li>
        </ol>
        <p class="next-h">Что можно сделать дальше</p>
        <div class="chips"></div>`;
      ['Составить подробный чек-лист', 'Написать черновик письма команде', 'Найти риски и пути их снижения'].forEach(t => {
        const b = el('button', 'chip'); b.type = 'button'; b.textContent = t;
        b.addEventListener('click', () => send(t));
        body.querySelector('.chips').append(b);
      });
    }
    w.append(body); return w;
  }
  function userMessage(text) {
    const w = el('div', 'msg-user'); const b = el('div', 'bubble'); b.textContent = text; w.append(b); return w;
  }
  function typingEl() {
    const w = el('div', 'msg-ai'); w.id = 'typing';
    w.append(el('span', 'logo', icon('spark')));
    const b = el('div', 'ai-body'); b.setAttribute('aria-label', 'Aster печатает'); b.innerHTML = '<span class="typing"><i></i><i></i><i></i></span>';
    w.append(b); return w;
  }
  function emptyState() {
    const w = el('div', 'empty');
    w.innerHTML = `<span class="logo">${icon('spark')}</span><h2>Чем займёмся сегодня?</h2><div class="chips"></div>`;
    return w;
  }
  function renderThread() {
    thread.innerHTML = '';
    const c = current();
    if (!c || !c.messages.length) thread.append(emptyState());
    if (c) c.messages.forEach(m => thread.append(m.role === 'user' ? userMessage(m.text) : aiMessage(m)));
    if (state.pending) thread.append(typingEl());
    thread.scrollTop = thread.scrollHeight;
  }

  function send(text) {
    text = (text ?? prompt.value).trim();
    if (!text || state.pending) return;
    let c = current();
    if (!c) {   // чатов ещё нет — создаём первый при отправке сообщения
      c = { id: 'c' + (++state.counter), title: 'Новый чат', project: null, messages: [] };
      chats.unshift(c); state.active = c.id;
    }
    c.messages.push({ role: 'user', text: state.files.length ? text + '\n📎 ' + state.files.join(', ') : text });
    if (c.title === 'Новый чат') {
      c.title = text.length > 38 ? text.slice(0, 38).trim() + '…' : text;
      $('#chat-title').textContent = c.title; renderSidebar();
    }
    state.files = []; renderFiles();
    prompt.value = ''; autosize();
    state.pending = true; updateSend(); renderThread();
    const id = c.id, fail = /\/error/i.test(text);
    setTimeout(() => {
      const chat = chats.find(x => x.id === id); if (!chat) return;
      chat.messages.push(fail ? { role: 'ai', error: true } : { role: 'ai', reply: true });
      if (state.active === id) { state.pending = false; updateSend(); renderThread(); }
    }, 1400);
  }
  function retry() {
    const c = current();
    if (!c || state.pending) return;
    const last = c.messages[c.messages.length - 1];
    if (last && last.error) c.messages.pop();
    state.pending = true; updateSend(); renderThread();
    const id = c.id;
    setTimeout(() => {
      const chat = chats.find(x => x.id === id); if (!chat) return;
      chat.messages.push({ role: 'ai', reply: true });
      if (state.active === id) { state.pending = false; updateSend(); renderThread(); }
    }, 1200);
  }

  /* Композер */
  function autosize() { prompt.style.height = 'auto'; prompt.style.height = Math.min(prompt.scrollHeight, 200) + 'px'; }
  function updateSend() { sendBtn.disabled = state.pending || !prompt.value.trim(); }
  prompt.addEventListener('input', () => { autosize(); updateSend(); });
  prompt.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(); }
  });
  $('#composer').addEventListener('submit', (e) => { e.preventDefault(); send(); });

  const fileInput = $('#file-input');
  $('#attach-btn').addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', () => {
    [...fileInput.files].forEach(f => { if (state.files.length < 5) state.files.push(f.name); });
    fileInput.value = ''; renderFiles();
  });
  function renderFiles() {
    const box = $('#attachments'); box.innerHTML = '';
    state.files.forEach((n, i) => {
      const a = el('span', 'att', icon('file') + '<span></span>');
      a.querySelector('span').textContent = n;
      const x = el('button', null, icon('x').replace('class="ic"', 'class="ic" style="width:14px;height:14px"'));
      x.type = 'button'; x.setAttribute('aria-label', 'Убрать вложение ' + n);
      x.addEventListener('click', () => { state.files.splice(i, 1); renderFiles(); prompt.focus(); });
      a.append(x); box.append(a);
    });
  }

  /* ======================= ВКЛАДКИ ======================= */
  const tabs = { chat: $('#tab-chat'), dash: $('#tab-dash'), data: $('#tab-data') };
  const panels = { chat: $('#panel-chat'), dash: $('#panel-dash'), data: $('#panel-data') };
  function selectTab(k, focus = true) {
    Object.keys(tabs).forEach(n => {
      const on = n === k;
      tabs[n].setAttribute('aria-selected', String(on));
      tabs[n].tabIndex = on ? 0 : -1;
      panels[n].hidden = !on;
    });
    if (focus) tabs[k].focus();
    if (k === 'chat') { thread.scrollTop = thread.scrollHeight; }
  }
  Object.keys(tabs).forEach(k => tabs[k].addEventListener('click', () => selectTab(k, false)));
  $('.tabs').addEventListener('keydown', (e) => {
    const keys = Object.keys(tabs); const i = keys.findIndex(k => tabs[k].getAttribute('aria-selected') === 'true');
    let n = null;
    if (e.key === 'ArrowRight') n = (i + 1) % keys.length;
    if (e.key === 'ArrowLeft') n = (i - 1 + keys.length) % keys.length;
    if (e.key === 'Home') n = 0; if (e.key === 'End') n = keys.length - 1;
    if (n !== null) { e.preventDefault(); selectTab(keys[n]); }
  });

  /* ======================= СТАРТ ======================= */
  const saved = store.get();
  if (saved && saved.mail) login(saved.mail); else show('login');
})();
