// ================ 全局状态 ================
const State = {
    pageInfo: null,
    currentPage: 1,
    totalScenes: 0,
    isLoading: false,
    originalOrder: [],
    sceneDataCache: {},
};

// ================ 主入口 ================
const Main = {
    gridEl: null,
    toolbarEl: null,
    paginationEl: null,
    loadingEl: null,

    showLoading() {
        this.hideLoading();
        this.loadingEl = Utils.createElement('div', { className: 'sewf-loading', text: '⏳ 加载中...' });
        if (this.gridEl) this.gridEl.appendChild(this.loadingEl);
    },

    hideLoading() {
        if (this.loadingEl) { this.loadingEl.remove(); this.loadingEl = null; }
    },

    showError(msg) {
        this.hideLoading();
        const el = Utils.createElement('div', { className: 'sewf-error', text: '❌ ' + msg });
        if (this.gridEl) this.gridEl.appendChild(el);
    },

    resetState() {
        this.hideLoading();
        const oldToolbar = document.getElementById('sewf-toolbar');
        if (oldToolbar) oldToolbar.remove();
        const oldGrid = document.getElementById('sewf-grid');
        if (oldGrid) oldGrid.remove();
        const oldPagination = document.getElementById('sewf-pagination');
        if (oldPagination) oldPagination.remove();
        const oldMsg = document.querySelector('.sewf-no-scenes-msg');
        if (oldMsg) oldMsg.remove();

        this.gridEl = null;
        this.toolbarEl = null;
        this.paginationEl = null;
        State.isLoading = false;
        State.currentPage = 1;
        State.totalScenes = 0;
        State.originalOrder = [];
        State.sceneDataCache = {};
    },

    async init() {
        State.pageInfo = PageParser.parse();
        if (!State.pageInfo) {
            console.log('[SEWF] 不是支持的页面，跳过');
            return;
        }

        // 首页：Trending / Recently added 双区块增强
        if (State.pageInfo.type === Config.PAGE_TYPES.HOME) {
            await this.initHome();
            return;
        }

        console.log('[SEWF] 页面类型:', State.pageInfo.type, 'ID:', State.pageInfo.id);
        Sorter.init();

        // 读取记忆的页码
        const savedPage = parseInt(localStorage.getItem(
            `${Config.STORAGE_KEYS.PAGE}_${State.pageInfo.type}_${State.pageInfo.id || 'all'}`
        )) || 1;

        // 等待原生页面内容加载
        const container = await this._waitForContainer(State.pageInfo.type);
        if (!container) {
            console.error('[SEWF] 未找到页面容器');
            return;
        }

        // 不清空 React 容器（清空会与 React 渲染并发冲突导致 NotFoundError 崩溃）：
        // 隐藏 React 卡片容器，脚本 grid 挂到其兄弟位置，React 重建时互不干扰
        container.style.display = 'none';

        // 原生排序/收藏筛选控件保留（脚本已兼容其 URL 参数，切换后自动重新加载）；
        // 原生分页交给 hideNativePagination 隐藏
        this.hideNativePagination();

        // 创建网格容器（挂到 React 容器旁边，不成为其子节点）
        this.gridEl = Utils.createElement('div', { id: 'sewf-grid', className: 'row' });
        container.parentNode.insertBefore(this.gridEl, container.nextSibling);

        // 加载记忆的页码
        await this.loadPage(savedPage);
    },

    async initHome() {
        console.log('[SEWF] 首页增强: Trending / Recently added');
        // 1. 立即隐藏原生卡片容器（CSS 声明式，元素一出现即隐藏，杜绝闪现）
        if (!document.getElementById('sewf-home-css')) {
            const style = Utils.createElement('style', {
                id: 'sewf-home-css',
                text: '.HomePage-scenes{display:none!important}',
            });
            document.head.appendChild(style);
        }
        // 清理旧首页网格（SPA 重复进入时）
        document.querySelectorAll('[id^="sewf-home-grid"]').forEach(el => el.remove());

        // 2. 预加载两个区块数据（并行，不等 DOM）
        const sections = [
            { kw: 'Trending scenes', sort: 'TRENDING' },
            { kw: 'Recently added scenes', sort: 'DATE' },
        ];
        const loaders = sections.map(async s => {
            try {
                const pageInfo = {
                    type: Config.PAGE_TYPES.HOME,
                    id: null,
                    extraTagId: null,
                    extraStudioIds: [],
                    sortType: s.sort,
                    currentPage: 1,
                };
                const result = await API.fetchScenes(pageInfo, 1, 8); // 与原版一致：每区块 8 张
                return { s, scenes: result.scenes || [], err: null };
            } catch (e) {
                console.error('[SEWF] 首页区块加载失败:', s.kw, e);
                return { s, scenes: [], err: e };
            }
        });
        const results = await Promise.all(loaders);

        // 3. 等 DOM 就绪后渲染
        const home = await Utils.waitForElement('.HomePage.mx-4', 15000);
        if (!home) {
            console.error('[SEWF] 未找到首页容器 .HomePage.mx-4');
            return;
        }

        for (const { s, scenes, err } of results) {
            // 汉化后标题可能是中文（Hanhua.HEADINGS），原文/译文都匹配
            const zhTitle = (typeof Hanhua !== 'undefined' && Hanhua.HEADINGS) ? Hanhua.HEADINGS[s.kw] : null;
            const h4 = [...home.querySelectorAll('h4')].find(h => {
                const t = h.textContent.trim();
                return t === s.kw || (zhTitle && t === zhTitle);
            });
            if (!h4) {
                console.warn('[SEWF] 未找到区块:', s.kw);
                continue;
            }
            // 在 h4 之后插入独立网格（block 流，Bootstrap row 正常排布；原生容器已被 CSS 隐藏）
            const grid = Utils.createElement('div', { className: 'row', id: 'sewf-home-grid-' + s.sort.toLowerCase() });
            h4.insertAdjacentElement('afterend', grid);
            if (err) {
                grid.innerHTML = '<div style="text-align:center;padding:20px;color:#999;">加载失败</div>';
                continue;
            }
            const fragment = document.createDocumentFragment();
            scenes.forEach(scene => {
                fragment.appendChild(CardRenderer.renderCard(scene));
            });
            grid.appendChild(fragment);
            console.log(`[SEWF] ${s.kw}: ${scenes.length} 张卡片`);
        }
    },

    async _waitForContainer(pageType) {
        let selector;
        switch (pageType) {
            case Config.PAGE_TYPES.PERFORMER:
                selector = '.PerformerScenes .row';
                break;
            case Config.PAGE_TYPES.SCENES:
                selector = '.scenes-list .row';
                break;
            default:
                selector = '.row';
        }

        const el = await Utils.waitForElement(selector, 15000);
        if (el) return el;

        // fallback
        const fallback = await Utils.waitForElement('.row', 3000);
        return fallback;
    },

    async loadPage(page) {
        if (State.isLoading) return;
        State.isLoading = true;

        const pageChanged = page !== State.currentPage; // 仅页码变化才滚动（排序/筛选/首次加载不打扰）
        State.currentPage = page;
        this.showLoading();

        try {
            const perPage = Pagination.getPerPage();
            const result = await API.fetchScenes(State.pageInfo, page, perPage);
            State.totalScenes = result.count || 0;

            // 清空网格
            if (this.gridEl) this.gridEl.textContent = '';

            // 渲染卡片
            this._renderGrid(result.scenes);

            // 记忆当前页码
            try {
                localStorage.setItem(
                    `${Config.STORAGE_KEYS.PAGE}_${State.pageInfo.type}_${State.pageInfo.id || 'all'}`,
                    page
                );
            } catch (e) { /* localStorage 不可用时静默忽略 */ }

            // 移除加载提示
            this.hideLoading();

            // 插入工具栏（在网格前面）
            this._insertToolbar();

            // 插入分页控件（在网格后面）
            this._insertPagination();

            // 应用排序/过滤（如果之前有设置的话）
            Sorter.apply();

            // 仅翻页时滚动到网格顶部（避免停留在页面底部）
            if (pageChanged) this._scrollToGrid();

        } catch (err) {
            console.error('[SEWF] 加载失败:', err);
            this.showError(err.message || '加载失败');
        } finally {
            State.isLoading = false;
        }
    },

    _scrollToGrid() {
        if (!this.gridEl || !this.gridEl.isConnected) return;
        const y = this.gridEl.getBoundingClientRect().top + window.scrollY - 80; // 80px 固定导航偏移
        window.scrollTo(0, Math.max(0, y));
    },

    _renderGrid(scenes) {
        if (!this.gridEl || !scenes || !scenes.length) {
            if (this.gridEl) {
                this.gridEl.innerHTML = '<div style="text-align:center;padding:40px;color:#999;">没有找到场景</div>';
            }
            return;
        }

        const fragment = document.createDocumentFragment();
        scenes.forEach(scene => {
            const card = CardRenderer.renderCard(scene);
            State.sceneDataCache[scene.id] = scene;
            fragment.appendChild(card);
        });

        this.gridEl.appendChild(fragment);
    },

    _insertToolbar() {
        if (this.toolbarEl) this.toolbarEl.remove();
        this.toolbarEl = Toolbar.create();
        this.gridEl.parentNode.insertBefore(this.toolbarEl, this.gridEl);
    },


    // 持续隐藏原生分页与 React 卡片容器（SPA 重渲染可能重建/重置样式）；
    // 原生排序/收藏筛选控件保留。排除脚本自己的 #sewf-grid。
    hideNativePagination() {
        const hideIt = () => {
            // 隐藏分页容器
            document.querySelectorAll('.ms-auto.d-flex').forEach(el => {
                if (el.querySelector('.pagination')) el.style.display = 'none';
            });
            // 持续隐藏 React 卡片容器（React 重渲染重建的新容器没有 display:none）
            const sel = State.pageInfo ? {
                [Config.PAGE_TYPES.PERFORMER]: '.PerformerScenes .row',
                [Config.PAGE_TYPES.SCENES]: '.scenes-list .row',
                [Config.PAGE_TYPES.STUDIO]: '.row',
                [Config.PAGE_TYPES.TAG]: '.row',
                [Config.PAGE_TYPES.HOME]: '.HomePage-scenes',
            }[State.pageInfo.type] : null;
            if (sel) {
                document.querySelectorAll(sel).forEach(c => {
                    if (c.id !== 'sewf-grid') c.style.display = 'none';
                });
            }
        };
        hideIt();
        // 持续监视新插入的分页
        if (!this._pagObs) {
            this._pagObs = new MutationObserver(() => hideIt());
            this._pagObs.observe(document.body, { childList: true, subtree: true });
        }
    },

    _insertPagination() {
        if (this.paginationEl) this.paginationEl.remove();
        this.paginationEl = Pagination.create();
        if (this.paginationEl && this.gridEl.nextSibling) {
            this.gridEl.parentNode.insertBefore(this.paginationEl, this.gridEl.nextSibling);
        } else if (this.paginationEl) {
            this.gridEl.parentNode.appendChild(this.paginationEl);
        }
    },
};

// ================ SPA 路由监听 ================
let lastUrl = location.href;
let routeTimer = null;
let initRunning = false;

function setupRouteObserver() {
    new MutationObserver(() => {
        if (location.href !== lastUrl) {
            lastUrl = location.href;
            if (routeTimer) clearTimeout(routeTimer);
            routeTimer = setTimeout(() => {
                if (!initRunning) runInit();
            }, 500);
        }
    }).observe(document, { subtree: true, childList: true });
}

async function runInit() {
    if (initRunning) return;
    initRunning = true;
    try {
        Main.resetState();
        Styles.add();
        await Main.init();
    } catch (e) {
        console.error('[SEWF] init error:', e);
    } finally {
        initRunning = false;
    }
}

// ================ 启动 ================
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        setupRouteObserver();
        setTimeout(runInit, 500);
    });
} else {
    setupRouteObserver();
    setTimeout(runInit, 500);
}