// ================ 排序与过滤模块 ================
const Sorter = {
    currentMethod: 'default',
    hideNoFemale: false,
    hideYoungFemaleAge: 0,
    localFilter: 'none',

    init() {
        this.currentMethod = localStorage.getItem(Config.STORAGE_KEYS.SORT_METHOD) || Config.SORT_METHODS.DEFAULT;
        this.hideNoFemale = localStorage.getItem(Config.STORAGE_KEYS.HIDE_NO_FEMALE) === 'true';
        this.hideYoungFemaleAge = parseInt(localStorage.getItem(Config.STORAGE_KEYS.HIDE_YOUNG_FEMALE_AGE) || '0', 10) || 0;
        this.localFilter = localStorage.getItem(Config.STORAGE_KEYS.LOCAL_FILTER) || Config.LOCAL_FILTERS.NONE;
    },

    save() {
        localStorage.setItem(Config.STORAGE_KEYS.SORT_METHOD, this.currentMethod);
        localStorage.setItem(Config.STORAGE_KEYS.HIDE_NO_FEMALE, String(this.hideNoFemale));
        localStorage.setItem(Config.STORAGE_KEYS.HIDE_YOUNG_FEMALE_AGE, String(this.hideYoungFemaleAge));
        localStorage.setItem(Config.STORAGE_KEYS.LOCAL_FILTER, this.localFilter);
    },

    sortByAge() {
        this.currentMethod = Config.SORT_METHODS.AGE;
        this.save();
        this.apply();
    },

    sortBySubmissions() {
        this.currentMethod = Config.SORT_METHODS.SUBMISSIONS;
        this.save();
        this.apply();
    },

    restoreDefault() {
        this.currentMethod = Config.SORT_METHODS.DEFAULT;
        this.save();
        this.apply();
    },

    toggleHideNoFemale() {
        this.hideNoFemale = !this.hideNoFemale;
        this.save();
        this.apply();
    },

    setHideYoungFemaleAge(age) {
        this.hideYoungFemaleAge = age;
        this.save();
        this.apply();
    },

    // 本地场景筛选切换（hide=隐藏本地已有 / only=只看本地 / 再点恢复 none）
    setLocalFilter(mode) {
        this.localFilter = (this.localFilter === mode) ? Config.LOCAL_FILTERS.NONE : mode;
        this.save();
        this.apply();
    },

    isSceneVisible(card) {
        if (this.hideNoFemale && card.dataset.hasFemale !== 'true') return false;
        if (this.hideYoungFemaleAge > 0 && card.dataset.hasFemale === 'true') {
            const sceneId = card.getAttribute('data-scene-id');
            const data = State.sceneDataCache[sceneId];
            if (data && data.performers && data.date) {
                const youngestAge = CardRenderer.getYoungestFemaleAge(data.performers, data.date);
                if (youngestAge !== null && youngestAge <= this.hideYoungFemaleAge) return false;
            }
        }
        // 本地筛选：只在 SceneMatch 查询完成后（data-local-matched）才过滤，
        // 未查询完的卡片保持显示，避免闪烁
        if (this.localFilter !== Config.LOCAL_FILTERS.NONE && card.dataset.localMatched === '1') {
            const hasLocal = !!card.querySelector('.sewf-local-icon, .sewf-local-btn');
            if (this.localFilter === Config.LOCAL_FILTERS.HIDE && hasLocal) return false;
            if (this.localFilter === Config.LOCAL_FILTERS.ONLY && !hasLocal) return false;
        }
        return true;
    },

    apply() {
        const container = document.getElementById('sewf-grid');
        if (!container) return;

        const cards = Utils.$$('.col-3[data-scene-id]', container);
        if (!cards.length) return;

        // 记录原始顺序（首次）
        if (!State.originalOrder.length) {
            State.originalOrder = cards.map(c => c.getAttribute('data-scene-id'));
        }

        const sorted = this._sortCards(cards);

        container.innerHTML = '';
        let visibleCount = 0;

        sorted.forEach(card => {
            if (this.isSceneVisible(card)) {
                card.style.display = '';
                container.appendChild(card);
                visibleCount++;
            } else {
                card.style.display = 'none';
                container.appendChild(card);
            }
        });

        this._updateNoScenesMessage(container, visibleCount, cards.length);
        Toolbar.updateStatus();
    },

    _sortCards(cards) {
        switch (this.currentMethod) {
            case Config.SORT_METHODS.AGE:
                return this._sortByAge(cards);
            case Config.SORT_METHODS.SUBMISSIONS:
                return [...cards].sort((a, b) => {
                    return parseInt(b.dataset.totalSubmissions) - parseInt(a.dataset.totalSubmissions);
                });
            default:
                return this._sortByOriginalOrder(cards);
        }
    },

    _sortByAge(cards) {
        const withAge = cards.map(card => {
            const sceneId = card.getAttribute('data-scene-id');
            const data = State.sceneDataCache[sceneId];
            let minAge = Infinity;
            if (data && data.performers && data.date) {
                const age = CardRenderer.getYoungestFemaleAge(data.performers, data.date);
                if (age !== null) minAge = age;
            }
            return { card, minAge };
        });
        return withAge.sort((a, b) => a.minAge - b.minAge).map(e => e.card);
    },

    _sortByOriginalOrder(cards) {
        if (!State.originalOrder.length) return [...cards];
        const map = new Map(cards.map(c => [c.getAttribute('data-scene-id'), c]));
        const sorted = [];
        State.originalOrder.forEach(id => { if (map.has(id)) sorted.push(map.get(id)); });
        cards.forEach(c => { if (!State.originalOrder.includes(c.getAttribute('data-scene-id'))) sorted.push(c); });
        return sorted;
    },

    _updateNoScenesMessage(container, visibleCount, totalCount) {
        const old = document.querySelector('.sewf-no-scenes-msg');
        if (old) old.remove();

        if ((this.hideNoFemale || this.hideYoungFemaleAge > 0) && visibleCount === 0 && totalCount > 0) {
            const msg = Utils.createElement('div', { className: 'sewf-no-scenes-msg sewf-msg', style: {
                textAlign: 'center', padding: '20px', color: '#666',
                background: '#f8f9fa', borderRadius: '8px', margin: '20px auto', maxWidth: '80%',
            }});

            let filterText = '';
            if (this.hideNoFemale && this.hideYoungFemaleAge > 0) filterText = '没有女演员或女演员年龄过小';
            else if (this.hideNoFemale) filterText = '没有女演员参与';
            else filterText = `所有女演员年龄 ≤ ${this.hideYoungFemaleAge} 岁`;

            msg.textContent = `🔍 所有场景都已被过滤（${filterText}）`;
            container.parentNode.appendChild(msg);
        }
    },
};