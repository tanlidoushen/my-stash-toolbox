// ================ 工具栏模块（深色玻璃风格 + 集成分页） ================
const Toolbar = {
    containerEl: null,

    _buttonConfigs: [
        {
            id: 'sewf-sort-default',
            text: '📵 默认排序',
            activeText: '✅ 默认排序',
            color: '#6c757d',
            activeColor: '#28a745',
            isActive: () => Sorter.currentMethod === Config.SORT_METHODS.DEFAULT,
            onAction: () => Sorter.restoreDefault(),
        },
        {
            id: 'sewf-sort-age',
            text: '🎂 按年龄排序',
            activeText: '🎂 按年龄排序',
            color: '#6c757d',
            activeColor: '#28a745',
            isActive: () => Sorter.currentMethod === Config.SORT_METHODS.AGE,
            onAction: () => Sorter.sortByAge(),
        },
        {
            id: 'sewf-sort-sub',
            text: '📳 按提交排序',
            activeText: '📳 按提交排序',
            color: '#6c757d',
            activeColor: '#28a745',
            isActive: () => Sorter.currentMethod === Config.SORT_METHODS.SUBMISSIONS,
            onAction: () => Sorter.sortBySubmissions(),
        },
        {
            id: 'sewf-hide-nofemale',
            text: '🚺 隐藏无女演员',
            activeText: '🔙 显示所有场景',
            color: '#fd7e14',
            activeColor: '#dc3545',
            isActive: () => Sorter.hideNoFemale,
            onAction: () => Sorter.toggleHideNoFemale(),
        },
        {
            id: 'sewf-local-hide',
            text: '🎬 隐藏本地已有',
            activeText: '🎬 隐藏本地已有',
            color: '#6c757d',
            activeColor: '#dc3545',
            isActive: () => Sorter.localFilter === Config.LOCAL_FILTERS.HIDE,
            onAction: () => Sorter.setLocalFilter(Config.LOCAL_FILTERS.HIDE),
        },
        {
            id: 'sewf-local-only',
            text: '🎬 只看本地',
            activeText: '🎬 只看本地',
            color: '#6c757d',
            activeColor: '#28a745',
            isActive: () => Sorter.localFilter === Config.LOCAL_FILTERS.ONLY,
            onAction: () => Sorter.setLocalFilter(Config.LOCAL_FILTERS.ONLY),
        },
    ],

    create() {
        if (this.containerEl) this.containerEl.remove();

        this.containerEl = Utils.createElement('div', { id: 'sewf-toolbar', className: 'sewf-toolbar' });

        const total = State.totalScenes;
        const perPage = Pagination.getPerPage();
        const totalPages = Math.max(1, Math.ceil(total / perPage));
        const cur = State.currentPage;

        // ==================== 上排 ====================
        const topRow = Utils.createElement('div', { className: 'sewf-toolbar-top' });

        // --- 左侧：状态 ---
        const statusDiv = Utils.createElement('div', { id: 'sewf-toolbar-status', className: 'sewf-toolbar-left' });

        // --- 中间：排序/过滤按钮 ---
        const btnGroup = Utils.createElement('div', { className: 'sewf-toolbar-btns' });

        this._buttonConfigs.forEach(cfg => {
            const isActive = cfg.isActive();
            const btn = Utils.createElement('button', {
                id: cfg.id,
                text: isActive ? cfg.activeText : cfg.text,
                className: 'sewf-tb-btn' + (isActive ? ' active' : ''),
            });
            btn.addEventListener('click', () => {
                cfg.onAction();
                this._updateAllButtons();
            });
            btnGroup.appendChild(btn);
        });

        // --- 右侧：每页数量 ---
        const rightGroup = Utils.createElement('div', { className: 'sewf-toolbar-right' });

        const perPageLabel = Utils.createElement('span', { className: 'sewf-tb-label', text: '每页' });
        const perPageSelect = Utils.createElement('select', { className: 'sewf-tb-select' });
        Config.PAGINATION.PER_PAGE_OPTIONS.forEach(n => {
            const opt = Utils.createElement('option', { value: n, text: n });
            if (n === perPage) opt.selected = true;
            perPageSelect.appendChild(opt);
        });
        perPageSelect.addEventListener('change', () => {
            Pagination.setPerPage(parseInt(perPageSelect.value));
            Main.loadPage(1);
        });
        rightGroup.appendChild(perPageLabel);
        rightGroup.appendChild(perPageSelect);

        topRow.appendChild(statusDiv);
        topRow.appendChild(btnGroup);
        topRow.appendChild(rightGroup);

        // ==================== 分割线 ====================
        const divider = Utils.createElement('div', { className: 'sewf-toolbar-divider' });

        // ==================== 下排：分页导航 ====================
        const navRow = Utils.createElement('div', { className: 'sewf-toolbar-nav' });

        // 上一页
        const prevBtn = Utils.createElement('button', {
            text: '\u2039',
            className: 'sewf-tb-nav-btn' + (cur <= 1 ? ' disabled' : ''),
        });
        if (cur > 1) prevBtn.addEventListener('click', () => Main.loadPage(cur - 1));
        navRow.appendChild(prevBtn);

        // 页码按钮
        const addPageBtn = (page) => {
            const isCurrent = page === cur;
            const btn = Utils.createElement('button', {
                text: page,
                className: 'sewf-tb-nav-btn' + (isCurrent ? ' active' : ''),
            });
            if (!isCurrent) btn.addEventListener('click', () => Main.loadPage(page));
            navRow.appendChild(btn);
        };

        const addDots = () => {
            navRow.appendChild(Utils.createElement('span', { className: 'sewf-tb-dots', text: '\u2026' }));
        };

        if (totalPages <= 7) {
            for (let i = 1; i <= totalPages; i++) addPageBtn(i);
        } else {
            addPageBtn(1);
            if (cur > 3) addDots();
            const start = Math.max(2, cur - 1);
            const end = Math.min(totalPages - 1, cur + 1);
            for (let i = start; i <= end; i++) addPageBtn(i);
            if (cur < totalPages - 2) addDots();
            addPageBtn(totalPages);
        }

        // 下一页
        const nextBtn = Utils.createElement('button', {
            text: '\u203A',
            className: 'sewf-tb-nav-btn' + (cur >= totalPages ? ' disabled' : ''),
        });
        if (cur < totalPages) nextBtn.addEventListener('click', () => Main.loadPage(cur + 1));
        navRow.appendChild(nextBtn);

        // 跳转输入
        const jumpWrap = Utils.createElement('div', { className: 'sewf-tb-jump' });
        const jumpInput = Utils.createElement('input', {
            type: 'number', min: '1', max: totalPages, value: cur,
            className: 'sewf-tb-input',
        });
        jumpInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                const v = parseInt(jumpInput.value);
                if (v >= 1 && v <= totalPages && v !== cur) Main.loadPage(v);
            }
        });
        jumpInput.addEventListener('blur', () => {
            const v = parseInt(jumpInput.value);
            if (v >= 1 && v <= totalPages && v !== cur) Main.loadPage(v);
            else jumpInput.value = cur;
        });
        const jumpBtn = Utils.createElement('button', { text: '跳转', className: 'sewf-tb-jump-btn' });
        jumpBtn.addEventListener('click', () => {
            const v = parseInt(jumpInput.value);
            if (v >= 1 && v <= totalPages && v !== cur) Main.loadPage(v);
        });
        jumpWrap.appendChild(jumpInput);
        jumpWrap.appendChild(jumpBtn);
        navRow.appendChild(jumpWrap);

        this.containerEl.appendChild(topRow);
        this.containerEl.appendChild(divider);
        this.containerEl.appendChild(navRow);

        this.updateStatus();
        return this.containerEl;
    },

    _updateAllButtons() {
        const inactiveCls = 'sewf-tb-btn';
        const activeCls = 'sewf-tb-btn active';
        this._buttonConfigs.forEach(cfg => {
            const btn = document.getElementById(cfg.id);
            if (!btn) return;
            const isActive = cfg.isActive();
            btn.textContent = isActive ? cfg.activeText : cfg.text;
            btn.className = isActive ? activeCls : inactiveCls;
        });
    },

    updateStatus() {
        const el = document.getElementById('sewf-toolbar-status');
        if (!el) return;

        const methodNames = {
            [Config.SORT_METHODS.DEFAULT]: '默认排序',
            [Config.SORT_METHODS.AGE]: '按年龄排序 (升序)',
            [Config.SORT_METHODS.SUBMISSIONS]: '按提交数排序',
        };
        const methodIcons = {
            [Config.SORT_METHODS.DEFAULT]: '\uD83D\uDCF5',
            [Config.SORT_METHODS.AGE]: '\uD83C\uDF82',
            [Config.SORT_METHODS.SUBMISSIONS]: '\uD83D\uDCF3',
        };

        const icon = methodIcons[Sorter.currentMethod] || '\uD83D\uDCF5';
        const name = methodNames[Sorter.currentMethod] || '默认排序';

        const allCards = document.querySelectorAll('.col-3[data-scene-id]');
        const visibleCards = Array.from(allCards).filter(c => c.style.display !== 'none');
        const visible = visibleCards.length;
        const total = allCards.length;

        let filterInfo = '';
        if (Sorter.hideNoFemale) filterInfo += ' [隐藏无女演员]';
        if (Sorter.hideYoungFemaleAge > 0) filterInfo += ` [年龄\u2264${Sorter.hideYoungFemaleAge}]`;
        if (Sorter.localFilter === Config.LOCAL_FILTERS.HIDE) filterInfo += ' [隐藏本地已有]';
        if (Sorter.localFilter === Config.LOCAL_FILTERS.ONLY) filterInfo += ' [只看本地]';

        const typeLabel = Utils.createElement('span', { className: 'sewf-tb-tag' });
        typeLabel.textContent = `${icon} ${name}`;

        const countSpan = Utils.createElement('span', { className: 'sewf-tb-count' });
        countSpan.innerHTML = `共 <b>${total}</b> 个场景 (显示 ${visible}${filterInfo})`;

        el.textContent = '';
        el.appendChild(typeLabel);
        el.appendChild(countSpan);
    },
};
