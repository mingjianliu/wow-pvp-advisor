const { test, expect } = require('@playwright/test');

// Setup mock player injection before page load so the frontend has individual player data
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    // Mock the Wowhead metadata cache using a Proxy to avoid external network calls.
    // This serves mock icons and description tooltips to all nodes in the talent tree.
    const mockCache = {};
    const mockSpell = {
      name: "Mock Talent Effect",
      icon: "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='32' height='32'><rect width='32' height='32' fill='%232a2f3a'/><circle cx='16' cy='16' r='6' fill='%234d9fff'/></svg>",
      descHtml: "<div style='color:var(--text-1);font-family:sans-serif;padding:4px;'>Mock spell description detailing the PvP effect.</div>"
    };
    window.__talentMetaCache = new Proxy(mockCache, {
      get(target, prop) {
        if (prop === 'then') return undefined; // Promise safety
        if (!(prop in target)) {
          target[prop] = { ...mockSpell };
        }
        return target[prop];
      },
      set(target, prop, value) {
        target[prop] = value;
        return true;
      }
    });

    let clusterDataVal = null;
    Object.defineProperty(window, 'CLUSTER_DATA', {
      get() {
        return clusterDataVal;
      },
      set(val) {
        clusterDataVal = val;
        if (clusterDataVal) {
          // Inject mock player details for player view testing
          clusterDataVal.players = [
            {
              name: "Testplayer",
              realm: "Sargeras",
              region: "us",
              class: "Shaman",
              spec: "Restoration",
              ilvl: 630,
              rating: 2400,
              talent: {
                loadout_code: "mock-loadout-code",
                node_ranks: {
                  81022: 1, // Healing Stream Totem
                  80976: 1, // Primal Tide Core
                  81018: 1  // Living Stream
                },
                class_node_ids: [],
                spec_node_ids: [80976, 81018, 81022],
                hero_node_ids: [],
                pvp_talent_ids: [],
                pvp_talent_names: []
              },
              gear: [
                { slot: "Head", item_id: 1001, item_name: "Test Visual Helm", ilvl: 630 },
                { slot: "Shoulder", item_id: 1002, item_name: "Test Visual Pauldrons", ilvl: 630 }
              ]
            }
          ];

          // Inject picker lists into all nodes so Testplayer shows up in the tooltip no matter which node is hovered
          const mockPickers = [{ n: "Testplayer", r: "Sargeras" }];
          if (clusterDataVal.clusters && clusterDataVal.clusters[0]) {
            if (clusterDataVal.clusters[0].takes) {
              clusterDataVal.clusters[0].takes.forEach(t => { t.pickers = mockPickers; });
            }
            if (clusterDataVal.clusters[0].skips) {
              clusterDataVal.clusters[0].skips.forEach(t => { t.pickers = mockPickers; });
            }
            if (clusterDataVal.clusters[0].flex_takes) {
              clusterDataVal.clusters[0].flex_takes.forEach(t => { t.pickers = mockPickers; });
            }
          }
          if (clusterDataVal.talents) {
            if (clusterDataVal.talents.core) {
              clusterDataVal.talents.core.forEach(t => { t.pickers = mockPickers; });
            }
            if (clusterDataVal.talents.flex) {
              clusterDataVal.talents.flex.forEach(t => { t.pickers = mockPickers; });
            }
          }
        }
      },
      configurable: true
    });
  });
});

test.describe('WoW PvP Advisor Visual Regression Tests', () => {

  test('1. Default Cluster View (English)', async ({ page }) => {
    await page.goto('/index.html');
    await page.waitForSelector('.app');
    await page.waitForSelector('.tree-svg-wrap');
    
    // Wait for Babel compilation and React rendering to settle
    await page.waitForTimeout(1000);

    // Assert visual snapshot of the main page
    await expect(page).toHaveScreenshot('default-cluster-view.png');
  });

  test('2. Sidebar Cluster Switch Flow', async ({ page }) => {
    await page.goto('/index.html');
    await page.waitForSelector('.app');
    await page.waitForTimeout(1000);

    // Verify multiple cluster tabs are present and select the second tab (#2)
    const secondTab = page.locator('button.tab').filter({ has: page.locator('.tab-rank', { hasText: /^#2$/ }) });
    await secondTab.click();
    await page.waitForTimeout(500); // Wait for transition and tree redraw

    // Assert visual snapshot of Cluster #2 view
    await expect(page).toHaveScreenshot('cluster-2-view.png');
  });

  test('3. Individual Player View Flow', async ({ page }) => {
    await page.goto('/index.html');
    await page.waitForSelector('.app');
    await page.waitForTimeout(1000);

    // Trigger the custom tooltip by dispatching both mouseenter and mouseover events directly on a contested core talent node group (which is guaranteed to have player pickers)
    await page.dispatchEvent('.node-group.contested-take', 'mouseenter');
    await page.dispatchEvent('.node-group.contested-take', 'mouseover');

    
    // Wait for the custom tooltip to appear
    await page.waitForSelector('.tooltip');

    // Click the mock player link in the tooltip list
    const playerLink = page.locator('a.tooltip-picker-link').first();
    await playerLink.waitFor({ state: 'visible' });
    await playerLink.click();
    await page.waitForTimeout(500); // Wait for active player view rendering




    // Assert visual snapshot of individual player view (should display header banner and highlighted player choices)
    await expect(page).toHaveScreenshot('individual-player-view.png');

    // Click the back button to return to the cluster view
    const backBtn = page.locator('button.btn-back');
    await backBtn.click();
    await page.waitForTimeout(500);

    // Verify we successfully exited back to the default cluster view
    await expect(page.locator('button.btn-back')).not.toBeVisible();
  });

  test('4. Localization View (Chinese)', async ({ page }) => {
    // Navigate to the Chinese translation path.
    // server.js intercepts this and serves index.html, but getLocale() evaluates to zh_CN
    await page.goto('/index_zh.html');
    await page.waitForSelector('.app');
    await page.waitForSelector('.tree-svg-wrap');
    await page.waitForTimeout(1000);

    // Assert visual snapshot of Chinese layout and labels
    await expect(page).toHaveScreenshot('chinese-localization-view.png');
  });

  test('5. Tweaks Panel Interaction (Heatmap Mode)', async ({ page }) => {
    await page.goto('/index.html');
    await page.waitForSelector('.app');
    await page.waitForTimeout(1000);

    // Open Tweaks Panel by posting activation message
    await page.evaluate(() => {
      window.postMessage({ type: '__activate_edit_mode' }, '*');
    });

    // Wait for Tweaks panel to render
    await page.waitForSelector('.twk-panel');
    await page.waitForTimeout(300);

    // Toggle heatmap mode switch
    const heatmapToggle = page.locator('button.twk-toggle').first();
    await heatmapToggle.click();
    await page.waitForTimeout(500); // Wait for heatmap coloring rendering

    // Assert visual snapshot of dashboard with heatmap mode enabled and tweaks panel open
    await expect(page).toHaveScreenshot('tweaks-heatmap-enabled.png');
  });

});

