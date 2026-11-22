function hubTranslateNativeMenu(menu) {
    const labels = /* MENU_LABELS */ {};
    const { createHash } = require("node:crypto");
    function translateItems(current) {
        for (const item of current?.items ?? []) {
            if (typeof item.label === "string" && item.label) {
                const digest = createHash("sha256").update(item.label).digest("hex");
                if (Object.hasOwn(labels, digest)) item.label = labels[digest];
            }
            if (item.submenu) translateItems(item.submenu);
        }
    }
    translateItems(menu);
}
