"use strict";
(() => {
    // The packaged Hub serves its UI at this loopback origin on an ephemeral port.
    if (window.top !== window || location.protocol !== "https:" ||
        location.hostname !== "127.0.0.1" || !location.port) return;

    const catalogue = /* CATALOGUE */ {};
    const testId = id => `[data-testid="${id}"]`;
    const settings = testId("settings-sidebar");
    const composer = testId("agent-input-box");
    const settingsContent = `[data-split-root] > div:has(${settings}) ~ div .max-w-2xl.mx-auto`;
    const translatedSettingsTitles = new Set(Object.values(catalogue.settingsTitles));
    const settingsClose = `[role="dialog"]:has(${settings}) button[aria-label]`;
    const settingAttributes = ["aria-label", "placeholder", "title"];
    const protectedSettingsData = [
        "[role='log']", "[data-testid='settings-error-messages-card']",
        // The permission editor displays a user-supplied command, path or URL in this span.
        "span.flex-1.truncate.text-sm.min-w-0[title]"
    ].join(",");
    const protectedFormText = "input, textarea, select";
    const installedExtensions = testId("customizations-installed");
    const marketplace = testId("customizations-marketplace");
    const tabs = testId("plugins-tabs");
    const mcpModal = `[role="dialog"]:has(${testId("add-mcp-screen")})`;
    const customizationsLink = `${testId("sidebar-navigation-items")} a[href^="/customizations"]`;
    const mcpSearch = [
        `${testId("add-mcp-screen")} input`,
        '[role="dialog"] input[data-autofocus]'
    ].join(",");
    const excluded = [
        "pre", "code", "kbd", "samp", "script", "style", "template", "svg", "webview", "iframe",
        ".monaco-editor", ".prism-code", ".cm-editor", ".xterm", ".agy-user-bubble", ".agy-user-bubble-frame",
        "[class*='language-']", "[data-lexical-editor]", "[data-quotable]", "[data-step-rows]", "[data-step-list]",
        "[data-testid^='user-message']", "[data-testid^='agent-response']", "[data-testid^='terminal-']",
        "[data-testid^='side-question-answer']", "[data-testid^='artifact-']", "[data-testid='bottom-terminal-panel']",
        "[data-testid='standalone-terminal-view']", "[data-testid='background-task-command']",
        "[contenteditable]:not([contenteditable='false'])"
    ].join(",");

    // Each rule identifies a Hub control and the static labels known for that control.
    const textRules = [
        [testId("new-conversation-button"), catalogue.controls.newConversation],
        [testId("settings-button"), catalogue.controls.settingsButton],
        [testId("automations-button"), catalogue.controls.automations],
        [`${testId("section-header")}[data-title="Projects"] :is(h2,h3,button), ${testId("section-header")}[data-title="Conversations"] :is(h2,h3,button)`, catalogue.controls.sidebarHeading],
        [testId("plugins-section-header"), catalogue.controls.extensionsHeader],
        [testId("add-mcp-button"), catalogue.controls.addMcp],
        [`${settings} h1, ${settings} h2`, catalogue.controls.settingsHeading],
        [[
            "General", "App", "Appearance", "Shortcuts", "Notifications", "Models", "Customizations",
            "Browser", "Developer", "Provide Feedback", "Projects", "Agents", "Environments", "Running",
            "Conversations"
        ].map(name => `${settings} ${testId("settings-nav-item-" + name)}`).join(","),
            catalogue.controls.settingsNavigation],
        [`${settingsContent} :is(h2,h3)`, catalogue.controls.settingsSections],
        ["#project4kMode [data-testid^='mode-option-']", catalogue.controls.layoutMode],
        [customizationsLink, catalogue.controls.customizationHeading],
        [`div:has(> div > ${tabs}) > h1`, catalogue.controls.customizationTabs],
        [`${tabs} a`, catalogue.controls.customizationsTabsLabels],
        [`${installedExtensions} section > div > h3 > button`,
            catalogue.controls.installedSections],
        [`${marketplace} section > div > h2`, catalogue.controls.marketplaceHeading],
        [`${mcpModal} h2`, catalogue.controls.addMcpDialog],
        [testId("model-selector-header"), catalogue.controls.modelHeading],
        [testId("model-selector-effort-option"), catalogue.controls.modelEffort],
        [`${testId("model-selector-trigger")} > span > span.opacity-70`, catalogue.controls.activeModelEffort],
        [testId("model-selector-empty"), catalogue.controls.emptyModels],
        [`${composer} p.pointer-events-none.select-none.overflow-hidden.text-ellipsis`,
            catalogue.controls.composerHint]
    ];
    const attributeRules = [
        ["aria-label", settingsClose, catalogue.controls.closeSettings],
        ["aria-label", customizationsLink, catalogue.controls.customizeNavigation],
        ["aria-label", tabs, catalogue.controls.customizeViews],
        ["aria-label", `${mcpModal} button[aria-label]`, catalogue.controls.closeMcp],
        ["aria-label", "#project4kMode", catalogue.controls.layoutName],
        ["aria-label", "#project4kMode [data-testid^='mode-option-']", catalogue.controls.layoutChoice],
        ["placeholder", testId("customizations-search"), catalogue.controls.customizeSearch],
        ["aria-label", [testId("new-conversation-button"), testId("app-icon-new-conversation-button")].join(","), catalogue.controls.newConversationA11y],
        ["aria-label", testId("sidebar-toggle"), catalogue.controls.sidebarToggle],
        ["aria-label", testId("toggle-aux-sidebar"), catalogue.controls.auxSidebar],
        ["aria-label", testId("toggle-overview-panel"), catalogue.controls.overview],
        ["aria-label", testId("conversation-archive-button"), catalogue.controls.archiveConversation],
        ["aria-label", `${composer} button[aria-label]`, catalogue.controls.addContext],
        ["aria-label", testId("send-button") + "," + testId("send-button-loading"), catalogue.controls.sendMessage],
        ["aria-label", testId("sidebar-search-button"), catalogue.controls.searchConversations],
        ["aria-label", testId("settings-button"), catalogue.controls.openSettings],
        ["aria-label", testId("sidebar-add-project-button"), catalogue.controls.addProject],
        ["aria-label", testId("add-mcp-button"), catalogue.controls.addMcpButton],
        ["aria-label", testId("plugins-visibility-trigger"), catalogue.controls.extensionVisibility],
        ["aria-label", testId("conversations-palette-filter-trigger"), catalogue.controls.sortConversations],
        ["placeholder", mcpSearch, catalogue.controls.mcpSearchPlaceholder],
        ["aria-label", mcpSearch, catalogue.controls.mcpSearchA11y],
        ["placeholder", testId("rename-conversation-input"), catalogue.controls.renameConversation],
        ["title", testId("new-conversation-button"), catalogue.controls.newConversationTooltip],
        ["title", testId("settings-button"), catalogue.controls.settingsTooltip]
    ];
    const modelTrigger = testId("model-selector-trigger");
    const candidates = [modelTrigger, settingsContent, ...textRules.map(([selector]) => selector),
        ...attributeRules.map(([, selector]) => selector)].join(",");
    const encoder = new TextEncoder();
    const eligibleLengths = new WeakMap();

    function fingerprint(value, cache) {
        if (!cache.has(value)) {
            const digest = crypto.subtle.digest("SHA-256", encoder.encode(value)).then(buffer =>
                value.length + ":" + Array.from(new Uint8Array(buffer), byte =>
                    byte.toString(16).padStart(2, "0")).join("")
            );
            cache.set(value, digest);
        }
        return cache.get(value);
    }

    async function lookup(table, label, cache) {
        if (!eligibleLengths.has(table)) {
            eligibleLengths.set(table, new Set(Object.keys(table).map(key => Number(key.split(":", 1)[0]))));
        }
        if (!eligibleLengths.get(table).has(label.length)) return null;
        return table[await fingerprint(label, cache)] ?? null;
    }

    async function matchesPattern(value, pattern, cache) {
        return value.length === Number(pattern.split(":", 1)[0]) && await fingerprint(value, cache) === pattern;
    }

    function prefixLength(pattern) {
        return Number(pattern.split(":", 1)[0]);
    }

    function isProtected(element) {
        return !element || element.isContentEditable || element.closest(excluded);
    }

    async function translateValue(value, table, cache) {
        const label = value.trim();
        const translation = await lookup(table, label, cache);
        return translation === null ? value : value.replace(label, () => translation);
    }

    async function translateSetting(value, cache) {
        const translation = await translateValue(value, catalogue.settings, cache);
        if (translation !== value) return translation;

        const label = value.trim();
        const duration = label.match(/(\d+ (?:days?|hours?|minutes?)(?:, \d+ (?:days?|hours?|minutes?))*)\.$/);
        if (!duration) return value;
        const prefix = label.slice(0, duration.index);
        let period;
        if (await matchesPattern(prefix, catalogue.patterns.weekRefresh, cache)) period = "本周";
        else if (await matchesPattern(prefix, catalogue.patterns.hourRefresh, cache)) period = "五小时";
        else return value;

        const units = { day: "天", hour: "小时", minute: "分钟" };
        const interval = duration[1].replace(/(\d+) (day|hour|minute)s?/g, (_, count, unit) => count + units[unit])
            .replaceAll(", ", "");
        return value.replace(label, () => `你已使用部分${period}配额，将在 ${interval}后全部恢复。`);
    }

    async function translateShortcut(value, cache) {
        const patterns = catalogue.patterns;
        const addLength = prefixLength(patterns.addShortcut);
        if (await matchesPattern(value.slice(0, addLength), patterns.addShortcut, cache)) {
            const title = await lookup(catalogue.settings, value.slice(addLength), cache);
            return title ? `为「${title}」添加快捷键` : value;
        }
        const separator = value.lastIndexOf(" for ");
        if (separator < 0) return value;
        for (const [pattern, remove] of [[patterns.shortcut, false], [patterns.removeShortcut, true]]) {
            const length = prefixLength(pattern);
            if (separator <= length || !await matchesPattern(value.slice(0, length), pattern, cache)) continue;
            const title = await lookup(catalogue.settings, value.slice(separator + 5), cache);
            if (!title) return value;
            const keys = value.slice(length, separator);
            return remove ? `移除「${title}」的快捷键 ${keys}` : `「${title}」的快捷键 ${keys}`;
        }
        return value;
    }

    async function rewriteText(node, translate, belongsToControl) {
        const value = node.data;
        const next = await translate(value);
        const parent = node.parentElement;
        if (next !== value && node.data === value && node.isConnected && !isProtected(parent) &&
            !parent.closest(protectedFormText) && belongsToControl(parent)) {
            node.data = next;
        }
    }

    async function rewriteAttribute(node, attribute, translate, belongsToControl) {
        const value = node.getAttribute(attribute);
        if (!value) return;
        const next = await translate(value);
        if (next !== value && node.getAttribute(attribute) === value && node.isConnected &&
            !isProtected(node) && belongsToControl(node)) {
            node.setAttribute(attribute, next);
        }
    }

    async function translateSettingsPage(page, cache) {
        const heading = page.querySelector(":scope > .mb-2 h2");
        if (!heading) return;
        const initialTitle = heading.textContent.trim();
        const translatedTitle = translatedSettingsTitles.has(initialTitle)
            ? initialTitle : await lookup(catalogue.settingsTitles, initialTitle, cache);
        if (!translatedTitle) return;
        const belongsToPage = node => {
            const current = heading.textContent.trim();
            return page.matches(settingsContent) && page.contains(heading) && page.contains(node) &&
                (current === initialTitle || current === translatedTitle) && !node.closest(protectedSettingsData);
        };
        if (!belongsToPage(page)) return;

        const walker = document.createTreeWalker(page, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
            acceptNode(node) {
                if (node.nodeType === Node.TEXT_NODE) return NodeFilter.FILTER_ACCEPT;
                return isProtected(node) || node.matches(protectedSettingsData)
                    ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
            }
        });
        const jobs = [];
        for (let node = walker.nextNode(); node; node = walker.nextNode()) {
            if (node.nodeType === Node.TEXT_NODE) {
                if (!node.parentElement.closest(protectedFormText)) {
                    jobs.push(rewriteText(node, value => translateSetting(value, cache), belongsToPage));
                }
                continue;
            }
            const element = node;
            for (const attribute of settingAttributes) {
                if (!element.hasAttribute(attribute)) continue;
                const translate = async value => {
                    // This functional label is read by the host's grant editor when focus leaves an input.
                    if (attribute === "aria-label" &&
                        await matchesPattern(value, catalogue.patterns.functionalCancel, cache)) return value;
                    if (attribute === "aria-label" && element.closest("[data-testid^='shortcut-row-']")) {
                        const shortcut = await translateShortcut(value, cache);
                        if (shortcut !== value) return shortcut;
                    }
                    return translateSetting(value, cache);
                };
                jobs.push(rewriteAttribute(element, attribute, translate, belongsToPage));
            }
        }
        await Promise.all(jobs);
    }

    async function translateControl(control, cache) {
        if (!control.isConnected || isProtected(control)) return;
        const jobs = [];
        if (control.matches(settingsContent)) jobs.push(translateSettingsPage(control, cache));
        if (control.matches(modelTrigger)) {
            const pattern = catalogue.patterns.modelPrefix;
            const length = prefixLength(pattern);
            jobs.push(rewriteAttribute(control, "aria-label", async value =>
                await matchesPattern(value.slice(0, length), pattern, cache)
                    ? "选择模型，当前为： " + value.slice(length) : value,
            node => node.matches(modelTrigger)));
        }
        for (const [attribute, selector, table] of attributeRules) {
            if (control.hasAttribute(attribute) && control.matches(selector)) {
                jobs.push(rewriteAttribute(control, attribute, value => translateValue(value, table, cache),
                    node => node.matches(selector)));
            }
        }
        for (const [selector, table] of textRules) {
            if (!control.matches(selector)) continue;
            const walker = document.createTreeWalker(control, NodeFilter.SHOW_TEXT);
            const belongsToControl = node => control.matches(selector) && control.contains(node);
            for (let node = walker.nextNode(); node; node = walker.nextNode()) {
                const parent = node.parentElement;
                if (isProtected(parent) || parent.closest(protectedFormText)) continue;
                jobs.push(rewriteText(node, value => translateValue(value, table, cache), belongsToControl));
            }
        }
        await Promise.all(jobs);
    }

    function start() {
        if (!document.body || !globalThis.crypto?.subtle) return;
        const controls = new Set();

        function add(node, includeChildren) {
            const element = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
            if (isProtected(element)) return;
            const page = element.closest(settingsContent);
            if (page) controls.add(page);
            const control = element.closest(candidates);
            if (control) controls.add(control);
            if (includeChildren) {
                for (const child of element.querySelectorAll(candidates)) controls.add(child);
            }
        }

        function flush() {
            // Keep lookup inputs only for the current mutation batch.
            const cache = new Map();
            for (const control of controls) {
                void translateControl(control, cache).catch(() => {});
            }
            controls.clear();
        }

        const observer = new MutationObserver(records => {
            for (const record of records) {
                add(record.target, false);
                for (const node of record.addedNodes) {
                    if (node.nodeType === Node.TEXT_NODE || node.nodeType === Node.ELEMENT_NODE) {
                        add(node, node.nodeType === Node.ELEMENT_NODE);
                    }
                }
            }
            flush();
        });
        observer.observe(document.documentElement, {
            subtree: true, childList: true, characterData: true,
            attributeFilter: settingAttributes
        });
        add(document.body, true);
        flush();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start, { once: true });
    } else {
        start();
    }
})();
