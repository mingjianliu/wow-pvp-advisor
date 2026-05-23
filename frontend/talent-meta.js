// talent-meta.js — fetches WoW spell icons + tooltip HTML from Wowhead.
//
// Uses Wowhead's tooltip JSON endpoint:
//   https://nether.wowhead.com/tooltip/spell/<id>?dataEnv=1&locale=0
// which returns { name, icon, tooltip } where `tooltip` is the same HTML
// fragment the power.js widget would inject on hover.
//
// CORS is open on this endpoint, so we just fetch directly.  Results are
// cached in `window.__talentMetaCache` and survive React re-renders.

window.TalentMeta = (function () {
  const cache = window.__talentMetaCache = window.__talentMetaCache || {};
  const subscribers = new Set();
  const inFlight = new Set();
  const fire = () => subscribers.forEach((fn) => fn(cache));

  const ENDPOINT = (id) =>
    `https://nether.wowhead.com/tooltip/spell/${id}?dataEnv=1&locale=0`;
  const ICON_URL = (name) =>
    `https://wow.zamimg.com/images/wow/icons/medium/${name}.jpg`;

  function fetchOne(spellId) {
    const sid = String(spellId);
    if (cache[sid] || inFlight.has(sid)) return;
    inFlight.add(sid);
    fetch(ENDPOINT(sid))
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((json) => {
        const tooltipHtml = sanitize(json.tooltip || '');
        cache[sid] = {
          name: json.name || '',
          icon: json.icon ? ICON_URL(json.icon) : null,
          descHtml: tooltipHtml,
        };
        inFlight.delete(sid);
        fire();
      })
      .catch(() => {
        inFlight.delete(sid);
      });
  }

  // Strip the parts of Wowhead's tooltip HTML we don't want to show in our
  // own popup (the name — we already render it; the leading icon block;
  // sell-price / drop-from / sold-by chunks the widget appends for items).
  function sanitize(html) {
    const wrap = document.createElement('div');
    wrap.innerHTML = html;
    wrap.querySelectorAll('.whtt-name, .whtt-tooltip-icon').forEach((n) => n.remove());
    wrap.querySelectorAll('a[href^="/"]').forEach((a) => {
      a.setAttribute('href', 'https://www.wowhead.com' + a.getAttribute('href'));
      a.setAttribute('target', '_blank');
      a.setAttribute('rel', 'noopener');
    });
    return wrap.innerHTML;
  }

  function preload(spellIds) {
    spellIds.forEach((id) => { if (id) fetchOne(id); });
  }

  function get(spellId) {
    return spellId ? cache[String(spellId)] : null;
  }

  function subscribe(fn) {
    subscribers.add(fn);
    return () => subscribers.delete(fn);
  }

  return { preload, get, subscribe, fetchDesc: fetchOne };
})();

// React hook — re-renders the calling component when the cache updates.
window.useTalentMeta = function () {
  const [, setTick] = React.useState(0);
  React.useEffect(() => {
    return window.TalentMeta.subscribe(() => {
      setTick((t) => t + 1);
    });
  }, []);
  return window.TalentMeta;
};
