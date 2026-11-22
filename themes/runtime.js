"use strict";

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const file = path.join(os.homedir(), "Library", "Application Support", "Antigravity Hub Tools", "skin.json");
const probeFlag = path.join(path.dirname(file), ".skin-probe");
const probeFile = path.join(path.dirname(file), "skin-render.json");
const chatControls = '[data-testid="sidebar-navigation-items"], [data-testid="agent-input-box"]';
const settingsSidebar = '[data-testid="settings-sidebar"]';
const art = {
    jade: "radial-gradient(ellipse at 22% 23%, #a4eed5 0%, transparent 44%), radial-gradient(ellipse at 84% 67%, #2c867c 0%, transparent 66%), linear-gradient(143deg, #12384d, #6fa090 52%, #233b69)",
    dusk: "radial-gradient(ellipse at 70% 22%, #a8a8ef 0%, transparent 42%), radial-gradient(ellipse at 10% 65%, #356470 0%, transparent 65%), linear-gradient(130deg, #253854, #4a4585 56%, #151431)",
    sand: "radial-gradient(ellipse at 23% 76%, #96758c 0%, transparent 60%), radial-gradient(ellipse at 85% 30%, #ffc38a 0%, transparent 65%), linear-gradient(160deg, #634a71, #ce856d 63%, #463353)",
};

function skinCSS(skin) {
    if (!skin || !Object.hasOwn(art, skin.art) || !/^#[\da-f]{6}$/i.test(skin.tint) ||
        !Number.isInteger(skin.veil) || skin.veil < 45 || skin.veil > 96 ||
        !Number.isInteger(skin.blur) || skin.blur < 0 || skin.blur > 24) return "";
    let image = art[skin.art];
    if (skin.image !== undefined) {
        if (typeof skin.image !== "string" || skin.image.length > 4194304 ||
            !/^\/9j\/[A-Za-z0-9+/]+={0,2}$/.test(skin.image) || skin.image.length % 4 !== 0) return "";
        image = `url("data:image/jpeg;base64,${skin.image}"), ${image}`;
    }
    const hub = `html[data-agy-skin-active]:has(${chatControls}):not(:has(${settingsSidebar}))`;
    const shell = `:is(body, body > #root, body > #app, [data-split-root], [data-split-root] > div,
        :is(div, main, aside, section, header):has(${chatControls}))`;
    const base = "var(--color-background-primary, light-dark(#fafafa, #17191f))";
    const panelOpacity = Math.max(37, Math.round(skin.veil * 0.78));
    return `
        @media not (forced-colors: active) {
        ${hub} {
            --agy-skin-base: ${base};
            --agy-skin-veil: color-mix(in srgb, var(--agy-skin-base) ${skin.veil}%, transparent);
            --agy-skin-panel: color-mix(in srgb, var(--agy-skin-base) ${panelOpacity}%, transparent);
            --agy-skin-border: color-mix(in srgb, ${skin.tint} 28%, transparent);
            --agy-skin-blur: blur(${skin.blur}px);
            background-image: linear-gradient(var(--agy-skin-veil), var(--agy-skin-veil)), ${image} !important;
            background-color: var(--agy-skin-base) !important;
            background-position: center !important;
            background-size: cover !important;
            background-attachment: fixed !important;
            background-repeat: no-repeat !important;
        }
        ${hub} ${shell}:not(:is(pre, code, iframe, webview, [data-testid^="artifact-"])) {
            background-color: transparent !important;
            background-image: none !important;
        }
        ${hub} :is([data-agy-skin-sidebar], [data-testid="agent-input-box"]) {
            background-color: var(--agy-skin-panel) !important;
            backdrop-filter: var(--agy-skin-blur) !important;
        }
        ${hub} [data-agy-skin-sidebar] :is([data-testid="sidebar-navigation-items"],
            [data-testid="section-header"], div:has(> [data-testid="section-header"]),
            [data-testid="new-conversation-button"], [data-agy-skin-rail-block]) {
            background-color: transparent !important;
            background-image: none !important;
        }
        ${hub} :is([data-agy-skin-fade], [data-testid="toggle-aux-sidebar"],
            [data-testid="toggle-overview-panel"]) {
            background-color: transparent !important;
            background-image: none !important;
        }
        ${hub} [data-agy-skin-fade-before]::before,
        ${hub} [data-agy-skin-fade-after]::after {
            background-color: transparent !important;
            background-image: none !important;
        }
        ${hub} :is([data-testid="new-conversation-button"], [data-testid="toggle-aux-sidebar"],
            [data-testid="toggle-overview-panel"], [data-agy-skin-rail-block]:is(button, [role="button"])):hover {
            background-color: var(--agy-skin-panel) !important;
        }
        ${hub} [data-agy-skin-sidebar] [data-agy-skin-project-row] {
            background-color: color-mix(in srgb, var(--agy-skin-base) 18%, transparent) !important;
        }
        ${hub} [data-agy-skin-sidebar] [data-agy-skin-project-row]:hover {
            background-color: var(--agy-skin-panel) !important;
        }
        ${hub} [data-testid="agent-input-box"] {
            border-color: var(--agy-skin-border) !important;
        }
        ${hub} [data-testid="agent-input-box"] :where(div:has([contenteditable="true"])) {
            background-color: transparent !important;
            background-image: none !important;
        }
        }
    `;
}

function origin(url) {
    try {
        const parsed = new URL(url);
        return parsed.protocol === "https:" && parsed.hostname === "127.0.0.1" && parsed.port ? parsed.origin : "";
    } catch {
        return "";
    }
}

function readCSS() {
    try {
        if (fs.statSync(file).size > 4250000) return "";
        return skinCSS(JSON.parse(fs.readFileSync(file, "utf8")));
    } catch {
        return "";
    }
}

function markHubChrome(enabled) {
    const sidebarMark = "data-agy-skin-sidebar";
    const fadeMark = "data-agy-skin-fade";
    const railMark = "data-agy-skin-rail-block";
    const projectMark = "data-agy-skin-project-row";
    const activeMark = "data-agy-skin-active";
    const pseudoMarks = [`${fadeMark}-before`, `${fadeMark}-after`];
    const markers = [sidebarMark, railMark, projectMark, fadeMark, ...pseudoMarks];
    if (globalThis.agySkinChrome) {
        if (!enabled) globalThis.agySkinChrome();
        return;
    }
    if (!enabled) return;
    document.documentElement.setAttribute(activeMark, "");

    function clear(attribute) {
        for (const node of document.querySelectorAll(`[${attribute}]`)) node.removeAttribute(attribute);
    }
    function locate() {
        for (const mark of markers) clear(mark);
        const nav = document.querySelector('[data-testid="sidebar-navigation-items"]');
        const composer = document.querySelector('[data-testid="agent-input-box"]');
        let sidebar = nav?.parentElement;
        while (sidebar && sidebar !== document.body && !sidebar.querySelector('[data-testid="section-header"]')) {
            sidebar = sidebar.parentElement;
        }
        if (sidebar && sidebar !== document.body && !sidebar.contains(composer) &&
            sidebar.getBoundingClientRect().width < innerWidth * 0.5) {
            sidebar.setAttribute(sidebarMark, "");
            const width = sidebar.getBoundingClientRect().width;
            const projects = sidebar.querySelector('[data-testid="section-header"][data-title="Projects"]')?.getBoundingClientRect();
            const conversations = sidebar.querySelector('[data-testid="section-header"][data-title="Conversations"]')?.getBoundingClientRect();
            for (const block of sidebar.querySelectorAll('div, section, header, button, [role="button"]')) {
                const box = block.getBoundingClientRect();
                if (box.width < width * 0.84 || box.height < 12 || box.height > 142) continue;
                if (block.closest('[role="menu"], [role="dialog"], [role="listbox"]')) continue;
                const style = getComputedStyle(block);
                if (style.borderRadius === "0px" && style.backgroundColor !== "rgba(0, 0, 0, 0)") {
                    block.setAttribute(railMark, "");
                }
                if (projects && box.top >= projects.bottom - 5 &&
                    box.bottom <= (conversations?.top ?? projects.bottom + 160) &&
                    block.matches('button, [role="button"]') && style.backgroundColor !== "rgba(0, 0, 0, 0)") {
                    block.setAttribute(projectMark, "");
                }
            }
        }
        if (!composer) return;
        const editable = composer.querySelector('[contenteditable="true"], textarea');
        const anchor = (editable || composer).getBoundingClientRect();
        // The timeline fade can be painted on a sibling of the entire composer footer.
        const decorations = document.querySelectorAll(
            'div[style], div[class*="gradient"], div[class*="linear"], div[class*="fade"], div.pointer-events-none, div[aria-hidden="true"]'
        );
        const protectedContent = '.agy-user-bubble, [data-quotable], [data-testid^="agent-response"], [data-testid^="artifact-"], [data-testid^="terminal-"], pre, code';
        for (const node of decorations) {
            const bounds = node.getBoundingClientRect();
            if (bounds.width < Math.max(anchor.width * 0.86, innerWidth * 0.42) || bounds.height < 4 ||
                bounds.height > 174 || bounds.bottom < anchor.top - 120 ||
                bounds.bottom > anchor.top + 48 || bounds.top >= anchor.top ||
                bounds.right <= anchor.left || bounds.left >= anchor.right || node.closest(protectedContent)) continue;
            const style = getComputedStyle(node);
            if (node.childElementCount > 0 && style.pointerEvents !== "none") continue;
            if (style.backgroundImage.includes("gradient(")) {
                node.setAttribute(fadeMark, "");
            }
            for (const [index, pseudo] of ["::before", "::after"].entries()) {
                const paint = getComputedStyle(node, pseudo);
                if (paint.backgroundImage.includes("gradient(")) node.setAttribute(pseudoMarks[index], "");
            }
        }
    }
    let timer;
    const schedule = () => {
        if (timer !== undefined) return;
        timer = setTimeout(() => {
            timer = undefined;
            locate();
        }, 160);
    };
    const observer = new MutationObserver(schedule);
    observer.observe(document.body, { childList: true, subtree: true });
    addEventListener("resize", schedule);
    globalThis.agySkinChrome = () => {
        observer.disconnect();
        removeEventListener("resize", schedule);
        clearTimeout(timer);
        for (const mark of markers) clear(mark);
        document.documentElement.removeAttribute(activeMark);
        delete globalThis.agySkinChrome;
    };
    locate();
}

async function report(contents, stage) {
    if (!fs.existsSync(probeFlag)) return;
    let surface;
    if (stage === "inserted" || stage === "disabled") {
        const code = `(() => {
            const root = getComputedStyle(document.documentElement);
            const crop = document.querySelector('[data-testid="agent-input-box"]');
            const sidebar = document.querySelector('[data-agy-skin-sidebar]');
            const fades = [...document.querySelectorAll('[data-agy-skin-fade]')];
            return {
                wallpaperRaster: root.backgroundImage.includes('data:image/jpeg;base64,'),
                hasBackground: root.backgroundImage !== 'none',
                composerGlass: crop ? getComputedStyle(crop).backdropFilter : null,
                sidebarGlass: sidebar ? getComputedStyle(sidebar).backdropFilter : null,
                hiddenFades: fades.filter(fade => getComputedStyle(fade).backgroundImage === 'none').length,
                hiddenRailBlocks: document.querySelectorAll('[data-agy-skin-rail-block]').length,
            };
        })()`;
        surface = await contents.executeJavaScriptInIsolatedWorld(1292, [{ code }]).catch(() => null);
    }
    fs.writeFileSync(probeFile, JSON.stringify({ stage, surface }, null, 2), { mode: 0o600 });
}

function attachSkin(contents, initialUrl) {
    const allowed = origin(initialUrl);
    if (!allowed) {
        void report(contents, "unsupported-origin").catch(() => {});
        return;
    }
    let stylesheet;
    let decorated = false;
    let documentVersion = 0;
    let pending = Promise.resolve();
    function update(stat, previous) {
        if (stat && previous && stat.mtimeMs === previous.mtimeMs && stat.ino === previous.ino) return;
        const version = documentVersion;
        pending = pending.then(async () => {
            if (version !== documentVersion || contents.isDestroyed()) return;
            if (origin(contents.getURL()) !== allowed) {
                await report(contents, "origin-mismatch");
                return;
            }
            if (stylesheet !== undefined) {
                await contents.removeInsertedCSS(stylesheet).catch(() => {});
                stylesheet = undefined;
            }
            if (version !== documentVersion || contents.isDestroyed() || origin(contents.getURL()) !== allowed) return;
            const css = readCSS();
            if (css || decorated) {
                await contents.executeJavaScriptInIsolatedWorld(1292, [
                    { code: `(${markHubChrome})(${Boolean(css)})` }
                ]);
                decorated = Boolean(css);
            }
            if (css) {
                const key = await contents.insertCSS(css, { cssOrigin: "user" });
                if (version === documentVersion) stylesheet = key;
            }
            await report(contents, css ? "inserted" : "disabled");
        }).catch(() => { void report(contents, "error").catch(() => {}); });
    }
    contents.on("dom-ready", () => {
        documentVersion++;
        stylesheet = undefined;
        decorated = false;
        update();
    });
    contents.on("did-finish-load", () => update());
    fs.watchFile(file, { interval: 750, persistent: false }, update);
    contents.once("destroyed", () => fs.unwatchFile(file, update));
}

module.exports = { attachSkin, skinCSS, markHubChrome };
