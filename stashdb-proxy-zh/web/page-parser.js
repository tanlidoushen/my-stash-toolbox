// ================ 页面解析模块 ================
const PageParser = {
    parse() {
        const path = window.location.pathname;
        const parts = path.split('/').filter(Boolean);
        const sp = new URLSearchParams(window.location.search);

        let type = null;
        let id = null;

        if (path === '/' || path === '') {
            type = Config.PAGE_TYPES.HOME;
            return {
                type,
                id: null,
                extraTagId: null,
                extraStudioIds: [],
                sortType: 'DATE',
                currentPage: 1,
            };
        }

        const studioIdx = parts.indexOf('studios');
        const tagIdx = parts.indexOf('tags');
        const perIdx = parts.indexOf('performers');

        if (studioIdx !== -1 && parts[studioIdx + 1] && Utils.isUUID(parts[studioIdx + 1])) {
            type = Config.PAGE_TYPES.STUDIO;
            id = parts[studioIdx + 1];
        } else if (tagIdx !== -1 && parts[tagIdx + 1] && Utils.isUUID(parts[tagIdx + 1])) {
            type = Config.PAGE_TYPES.TAG;
            id = parts[tagIdx + 1];
        } else if (perIdx !== -1 && parts[perIdx + 1] && Utils.isUUID(parts[perIdx + 1])) {
            type = Config.PAGE_TYPES.PERFORMER;
            id = parts[perIdx + 1];
        } else if (parts[parts.length - 1] === 'scenes') {
            type = Config.PAGE_TYPES.SCENES;
        }

        if (!type) return null;

        const tagParam = sp.get('tag');
        const studioParams = sp.getAll('studios');
        const sortParam = sp.get('sort') || 'DATE';
        const favoriteParam = sp.get('favorite');
        const pageParam = parseInt(sp.get('page')) || 1;

        return {
            type,
            id,
            extraTagId: (tagParam && Utils.isUUID(tagParam)) ? tagParam : null,
            extraStudioIds: studioParams.filter(s => Utils.isUUID(s)),
            sortType: Config.SORT_PARAM_MAP[sortParam] || 'DATE',
            favoriteType: Config.FAVORITE_PARAM_MAP[favoriteParam] || null,
            currentPage: pageParam,
        };
    },

    getGridContainer(pageType) {
        let selector;
        switch (pageType) {
            case Config.PAGE_TYPES.PERFORMER:
                selector = Config.GRID_SELECTOR.PERFORMER;
                break;
            case Config.PAGE_TYPES.SCENES:
                selector = Config.GRID_SELECTOR.SCENES;
                break;
            default:
                selector = Config.GRID_SELECTOR.DEFAULT;
        }
        const el = document.querySelector(selector);
        return el || document.querySelector(Config.GRID_SELECTOR.DEFAULT);
    },
};