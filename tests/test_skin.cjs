const { test } = require("node:test");
const assert = require("node:assert/strict");
const { skinCSS } = require("../themes/runtime.js");
const presets = require("../themes/presets.json");

test("skin CSS only uses allowlisted gradients and local raster data", () => {
    for (const preset of Object.values(presets)) {
        const css = skinCSS(preset);
        assert.match(css, /background-size: cover/);
        assert.match(css, /backdrop-filter:/);
        assert.match(css, /data-testid="agent-input-box"/);
        assert.doesNotMatch(css, /url\(/);
    }
    assert.match(skinCSS({ ...presets.jade, image: "/9j/AA==" }), /url\("data:image\/jpeg;base64,/);
    for (const bogus of ["https://site", "file:///tmp/picture", "/9j/\");@import", "data:image/svg+xml;base64,foo"]) {
        assert.equal(skinCSS({ ...presets.jade, image: bogus }), "");
    }
    assert.equal(skinCSS({ ...presets.jade, art: "constructor" }), "");
    assert.equal(skinCSS({}), "");
});


test("settings uses the native surfaces even when chat remains mounted", () => {
    const css = skinCSS(presets.dusk);
    // Every skin rule starts with this guard, including the rules clearing shell backgrounds.
    const guard = ':not(:has([data-testid="settings-sidebar"]))';
    const selectors = css.split(/[{}]/).map(part => part.trim())
        .filter(part => part.startsWith("html[data-agy-skin-active]"));
    assert.ok(selectors.length > 1);
    for (const selector of selectors) {
        assert.ok(selector.includes(guard));
        assert.ok(!selector.replaceAll(guard, "").includes('[data-testid="settings-sidebar"]'));
    }
});
