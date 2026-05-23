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

  const ENDPOINT = (type, id) =>
    `https://nether.wowhead.com/tooltip/${type}/${id}?dataEnv=1&locale=0`;
  const ICON_URL = (name) =>
    `https://wow.zamimg.com/images/wow/icons/medium/${name}.jpg`;

  function fetchOne(id, type = 'spell') {
    const key = `${type}:${id}`;
    if (cache[key] || inFlight.has(key)) return;
    inFlight.add(key);

    fetch(ENDPOINT(type, id))
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((json) => {
        const tooltipHtml = sanitize(json.tooltip || '');
        cache[key] = {
          name: json.name || '',
          icon: json.icon ? ICON_URL(json.icon) : null,
          descHtml: tooltipHtml,
        };
        inFlight.delete(key);
        fire();
      })
      .catch(() => {
        inFlight.delete(key);
        // If 'spell' failed, try 'pvp-talent'
        if (type === 'spell') {
          fetchOne(id, 'pvp-talent');
        }
      });
  }

  // ... (sanitize function remains same) ...

  function preload(ids, type = 'spell') {
    ids.forEach((id) => { if (id) fetchOne(id, type); });
  }

  function get(id, type = 'spell') {
    if (!id) return null;
    return cache[`${type}:${id}`] || (type === 'spell' ? cache[`pvp-talent:${id}`] : null);
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
