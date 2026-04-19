"""Scan the DOM and return a list[DetectedField]."""
from __future__ import annotations

from typing import Any

from app.browser.playwright_base import PlaywrightBase
from app.logger import get_logger
from app.schemas import DetectedField


log = get_logger(__name__)


_SCAN_JS = r"""
() => {
  function labelFor(el) {
    if (el.labels && el.labels.length) {
      return Array.from(el.labels).map(l => (l.innerText || l.textContent || '').trim()).join(' ').trim();
    }
    if (el.id) {
      const lab = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (lab) return (lab.innerText || lab.textContent || '').trim();
    }
    const wrap = el.closest('label');
    if (wrap) return (wrap.innerText || wrap.textContent || '').trim();
    const prev = el.previousElementSibling;
    if (prev && /label|span|div|p/i.test(prev.tagName)) {
      const t = (prev.innerText || prev.textContent || '').trim();
      if (t && t.length < 120) return t;
    }
    return '';
  }

  function stableSelector(el) {
    if (el.id) return `#${CSS.escape(el.id)}`;
    if (el.name) return `${el.tagName.toLowerCase()}[name="${el.name}"]`;
    let path = [];
    let node = el;
    while (node && node.nodeType === 1 && path.length < 5) {
      let seg = node.tagName.toLowerCase();
      const parent = node.parentElement;
      if (parent) {
        const siblings = Array.from(parent.children).filter(c => c.tagName === node.tagName);
        if (siblings.length > 1) seg += `:nth-of-type(${siblings.indexOf(node) + 1})`;
      }
      path.unshift(seg);
      node = node.parentElement;
    }
    return path.join(' > ');
  }

  function kindOf(el) {
    const tag = el.tagName.toLowerCase();
    if (tag === 'textarea') return 'textarea';
    if (tag === 'select') return 'select';
    if (tag === 'input') {
      const t = (el.type || 'text').toLowerCase();
      if (['email','tel','url','number','date','file','checkbox','radio'].includes(t)) return t;
      return 'text';
    }
    if (el.getAttribute && el.getAttribute('contenteditable') === 'true') return 'textarea';
    return 'unknown';
  }

  function optionsOf(el) {
    if (el.tagName.toLowerCase() === 'select') {
      return Array.from(el.options).map(o => o.text.trim()).filter(Boolean);
    }
    if (el.type === 'radio' && el.name) {
      const group = document.querySelectorAll(`input[type="radio"][name="${CSS.escape(el.name)}"]`);
      return Array.from(group).map(r => {
        const lab = (r.labels && r.labels[0]) || document.querySelector(`label[for="${CSS.escape(r.id || '')}"]`);
        return (lab ? (lab.innerText || lab.textContent || '').trim() : (r.value || '')).trim();
      }).filter(Boolean);
    }
    return [];
  }

  const nodes = Array.from(document.querySelectorAll('input, textarea, select, [contenteditable="true"]'));
  const seenRadioGroups = new Set();
  const out = [];
  for (const el of nodes) {
    if (el.type === 'hidden' || el.type === 'submit' || el.type === 'button') continue;
    if (el.type === 'radio') {
      const key = `radio::${el.name || ''}`;
      if (seenRadioGroups.has(key)) continue;
      seenRadioGroups.add(key);
    }
    out.push({
      selector: stableSelector(el),
      kind: kindOf(el),
      name: el.name || null,
      id: el.id || null,
      label: labelFor(el),
      placeholder: el.placeholder || null,
      aria_label: el.getAttribute ? el.getAttribute('aria-label') : null,
      options: optionsOf(el),
      required: !!el.required,
      disabled: !!el.disabled,
    });
  }
  return out;
}
"""


class PageScanner:
    def scan(self, browser: PlaywrightBase) -> list[DetectedField]:
        raw: list[dict[str, Any]] = browser.evaluate(_SCAN_JS) or []
        detected: list[DetectedField] = []
        for r in raw:
            try:
                detected.append(DetectedField(**r))
            except Exception as e:
                log.warning("Dropping malformed field record: %s err=%s", r, e)
        log.info("Page scan found %d candidate fields", len(detected))
        return detected
