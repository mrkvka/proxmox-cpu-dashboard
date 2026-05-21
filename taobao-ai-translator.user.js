// ==UserScript==
// @name         Taobao AI Translator (RU)
// @namespace    https://github.com/cursor-agent
// @version      1.0.0
// @description  Перевод Taobao/Tmall на русский: OpenAI или бесплатный Google fallback
// @author       cursor
// @match        https://*.taobao.com/*
// @match        https://*.tmall.com/*
// @match        https://taobao.com/*
// @match        https://tmall.com/*
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_registerMenuCommand
// @connect      api.openai.com
// @connect      translate.googleapis.com
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  const CFG = {
    apiKey: GM_getValue('apiKey', ''),
    lang: GM_getValue('lang', 'ru'),
    auto: GM_getValue('auto', true),
    engine: GM_getValue('engine', 'auto'), // auto | openai | google
  };

  const CACHE = new Map();
  const CHINESE = /[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]/;
  const SKIP = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'CODE', 'SVG', 'INPUT', 'TEXTAREA']);
  const BATCH = 12;
  const MIN_LEN = 2;

  GM_registerMenuCommand('⚙ Настройки переводчика', openSettings);

  function openSettings() {
    const key = prompt('OpenAI API key (пусто = только Google):', CFG.apiKey) ?? CFG.apiKey;
    const lang = prompt('Язык (ru, en, uk...):', CFG.lang) ?? CFG.lang;
    const auto = confirm('Авто-перевод при загрузке?\nOK = да, Отмена = нет');
    GM_setValue('apiKey', key.trim());
    GM_setValue('lang', (lang || 'ru').trim());
    GM_setValue('auto', auto);
    location.reload();
  }

  function http(opts) {
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({
        ...opts,
        onload: (r) => resolve(r),
        onerror: reject,
      });
    });
  }

  async function translateGoogle(texts, tl) {
    const out = [];
    for (const t of texts) {
      const url =
        'https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=' +
        encodeURIComponent(tl) +
        '&dt=t&q=' +
        encodeURIComponent(t);
      const r = await http({ method: 'GET', url });
      const data = JSON.parse(r.responseText);
      out.push((data[0] || []).map((x) => x[0]).join('') || t);
    }
    return out;
  }

  async function translateOpenAI(texts, tl) {
    const list = texts.map((t, i) => `${i + 1}. ${t}`).join('\n');
    const r = await http({
      method: 'POST',
      url: 'https://api.openai.com/v1/chat/completions',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer ' + CFG.apiKey,
      },
      data: JSON.stringify({
        model: 'gpt-4o-mini',
        temperature: 0.2,
        messages: [
          {
            role: 'system',
            content:
              `Translate each numbered line to ${tl}. E-commerce context. Return ONLY numbered lines, same count. No extra text.`,
          },
          { role: 'user', content: list },
        ],
      }),
    });
    if (r.status !== 200) throw new Error(r.responseText);
    const body = JSON.parse(r.responseText);
    const raw = body.choices?.[0]?.message?.content || '';
    const lines = raw.split('\n').filter(Boolean);
    return texts.map((_, i) => {
      const m = lines.find((l) => l.startsWith(i + 1 + '.'));
      return m ? m.replace(/^\d+\.\s*/, '').trim() : texts[i];
    });
  }

  async function translateBatch(texts) {
    const tl = CFG.lang;
    const useAI =
      CFG.engine === 'openai' ||
      (CFG.engine === 'auto' && CFG.apiKey.length > 10);
    try {
      return useAI ? await translateOpenAI(texts, tl) : await translateGoogle(texts, tl);
    } catch {
      return translateGoogle(texts, tl);
    }
  }

  function collectNodes(root = document.body) {
    const nodes = [];
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(n) {
        const p = n.parentElement;
        if (!p || SKIP.has(p.tagName) || p.closest('[data-tb-tr]')) return NodeFilter.FILTER_REJECT;
        if (p.isContentEditable || p.hidden) return NodeFilter.FILTER_REJECT;
        const t = n.textContent.trim();
        if (t.length < MIN_LEN || !CHINESE.test(t)) return NodeFilter.FILTER_REJECT;
        const st = getComputedStyle(p);
        if (st.display === 'none' || st.visibility === 'hidden' || +st.opacity === 0)
          return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    let x;
    while ((x = walker.nextNode())) nodes.push(x);
    return nodes;
  }

  let busy = false;

  async function runTranslate(scope) {
    if (busy) return;
    busy = true;
    try {
    const nodes = collectNodes(scope);
    const uniq = [...new Set(nodes.map((n) => n.textContent.trim()))].filter(Boolean);
    const todo = uniq.filter((t) => !CACHE.has(t));
    for (let i = 0; i < todo.length; i += BATCH) {
      const chunk = todo.slice(i, i + BATCH);
      const res = await translateBatch(chunk);
      chunk.forEach((src, j) => CACHE.set(src, res[j] || src));
    }
    nodes.forEach((n) => {
      const src = n.textContent.trim();
      const tr = CACHE.get(src);
      if (!tr || tr === src) return;
      const el = n.parentElement;
      if (!el || el.dataset.tbTr) return;
      el.dataset.tbTr = '1';
      el.title = src;
      n.textContent = n.textContent.replace(src, tr);
    });
    } finally {
      busy = false;
    }
  }

  function makeUI() {
    const btn = document.createElement('button');
    btn.textContent = '🇷🇺 Перевести';
    Object.assign(btn.style, {
      position: 'fixed',
      bottom: '20px',
      right: '20px',
      zIndex: '2147483646',
      padding: '10px 14px',
      border: 'none',
      borderRadius: '8px',
      background: '#ff5000',
      color: '#fff',
      font: 'bold 14px/1 system-ui,sans-serif',
      cursor: 'pointer',
      boxShadow: '0 2px 12px rgba(0,0,0,.25)',
    });
    btn.onclick = async () => {
      btn.disabled = true;
      btn.textContent = '…';
      try {
        await runTranslate();
        btn.textContent = '✓ Готово';
      } catch (e) {
        btn.textContent = '✗ Ошибка';
        console.error('[Taobao TR]', e);
      }
      setTimeout(() => {
        btn.disabled = false;
        btn.textContent = '🇷🇺 Перевести';
      }, 2000);
    };
    document.body.appendChild(btn);
    return btn;
  }

  let debounce;
  const obs = new MutationObserver(() => {
    clearTimeout(debounce);
    debounce = setTimeout(() => CFG.auto && runTranslate(), 1200);
  });

  makeUI();
  if (CFG.auto) runTranslate();
  obs.observe(document.body, { childList: true, subtree: true });
})();
