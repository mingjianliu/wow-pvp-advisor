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
  const cache = (window.__talentMetaCache = window.__talentMetaCache || {});
  const subscribers = new Set();
  const inFlight = new Set();
  const fire = () => subscribers.forEach((fn) => fn(cache));

  const getWowheadLocale = () =>
    window.location.pathname.endsWith("_zh.html") ? 4 : 0;
  const ENDPOINT = (type, id) =>
    `https://nether.wowhead.com/tooltip/${type}/${id}?dataEnv=1&locale=${getWowheadLocale()}`;
  const ICON_URL = (name) =>
    `https://wow.zamimg.com/images/wow/icons/medium/${name}.jpg`;

  return {
    subscribe: (fn) => {
      subscribers.add(fn);
      return () => subscribers.delete(fn);
    },
    get: (id) => cache[id],
    getCache: () => cache,

    preload: (ids) => {
      ids.forEach((id) => {
        if (cache[id] || inFlight.has(id)) return;
        // Don't try to fetch 'ench-xxx' from network if not in cache (they are server-prefetched only)
        if (typeof id === "string" && id.startsWith("ench-")) return;

        inFlight.add(id);
        fetch(ENDPOINT("spell", id))
          .then((r) => r.json())
          .then((data) => {
            cache[id] = { ...cache[id], icon: ICON_URL(data.icon) };
            inFlight.delete(id);
            fire();
          })
          .catch(() => inFlight.delete(id));
      });
    },

    fetchDesc: (id) => {
      if (cache[id]?.descHtml || inFlight.has(`desc-${id}`)) return;
      inFlight.add(`desc-${id}`);
      fetch(ENDPOINT("spell", id))
        .then((r) => r.json())
        .then((data) => {
          cache[id] = { ...cache[id], name: data.name, descHtml: data.tooltip };
          inFlight.delete(`desc-${id}`);
          fire();
        })
        .catch(() => inFlight.delete(`desc-${id}`));
    },
  };
})();

window.useTalentMeta = () => {
  const [data, setData] = React.useState(window.__talentMetaCache);
  React.useEffect(() => window.TalentMeta.subscribe(setData), []);
  return { get: (id) => data[id] };
};
