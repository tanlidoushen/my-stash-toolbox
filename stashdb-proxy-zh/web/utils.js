// ================ 工具模块 ================
const Utils = {
    isUUID(str) {
        return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(str);
    },

    getDomainFromUrl(url) {
        try {
            return new URL(url).hostname.replace('www.', '');
        } catch {
            return '链接';
        }
    },

    waitForElement(selector, timeout = 10000) {
        return new Promise(resolve => {
            const el = document.querySelector(selector);
            if (el) return resolve(el);
            const obs = new MutationObserver(() => {
                const found = document.querySelector(selector);
                if (found) { obs.disconnect(); resolve(found); }
            });
            obs.observe(document.body, { childList: true, subtree: true });
            setTimeout(() => { obs.disconnect(); resolve(null); }, timeout);
        });
    },

    $(sel, root = document) {
        return root.querySelector(sel);
    },

    $$(sel, root = document) {
        return Array.from(root.querySelectorAll(sel));
    },

    createElement(tag, attrs = {}, children = []) {
        const el = document.createElement(tag);
        for (const [k, v] of Object.entries(attrs)) {
            if (k === 'style' && typeof v === 'object') {
                Object.assign(el.style, v);
            } else if (k === 'className') {
                el.className = v;
            } else if (k.startsWith('on') && typeof v === 'function') {
                el.addEventListener(k.slice(2).toLowerCase(), v);
            } else if (k === 'html') {
                el.innerHTML = v;
            } else if (k === 'text') {
                el.textContent = v;
            } else {
                el.setAttribute(k, v);
            }
        }
        for (const child of children) {
            if (typeof child === 'string') {
                el.appendChild(document.createTextNode(child));
            } else if (child instanceof Node) {
                el.appendChild(child);
            }
        }
        return el;
    },
};// hot-reload-test
