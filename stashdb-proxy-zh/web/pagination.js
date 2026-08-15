// ================ 分页模块（暗色风格） ================
const Pagination = {
    containerEl: null,

    getPerPage() {
        return parseInt(localStorage.getItem(Config.STORAGE_KEYS.PER_PAGE))
            || (State.pageInfo && State.pageInfo.type === Config.PAGE_TYPES.PERFORMER
                ? Config.PAGINATION.PERFORMER_PER_PAGE
                : Config.PAGINATION.DEFAULT_PER_PAGE);
    },

    setPerPage(n) {
        localStorage.setItem(Config.STORAGE_KEYS.PER_PAGE, n);
    },

    create() {
        if (this.containerEl) this.containerEl.remove();

        const total = State.totalScenes;
        const perPage = this.getPerPage();
        const totalPages = Math.max(1, Math.ceil(total / perPage));
        const cur = State.currentPage;

        this.containerEl = Utils.createElement('div', { id: 'sewf-pagination', className: 'sewf-pagination' });

        // 左侧：总数 + 每页选择
        const leftDiv = Utils.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' } });

        const countSpan = Utils.createElement('span');
        countSpan.innerHTML = `共 <b>${total.toLocaleString()}</b> 个场景`;
        leftDiv.appendChild(countSpan);

        // 每页选择
        const perPageWrap = Utils.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: '4px' } });
        const perPageLabel = Utils.createElement('span', { text: '每页' });
        const perPageSelect = Utils.createElement('select');
        Config.PAGINATION.PER_PAGE_OPTIONS.forEach(n => {
            const opt = Utils.createElement('option', { value: n, text: n });
            if (n === perPage) opt.selected = true;
            perPageSelect.appendChild(opt);
        });
        perPageSelect.addEventListener('change', () => {
            this.setPerPage(parseInt(perPageSelect.value));
            Main.loadPage(1);
        });
        perPageWrap.appendChild(perPageLabel);
        perPageWrap.appendChild(perPageSelect);
        leftDiv.appendChild(perPageWrap);

        // 右侧：分页按钮
        const navRight = Utils.createElement('div', { style: { display: 'flex', alignItems: 'center', gap: '4px' } });

        // 上一页
        const prevBtn = Utils.createElement('button', { text: '\u2039' });
        prevBtn.className = cur <= 1 ? 'sewf-pg-btn disabled' : 'sewf-pg-btn';
        if (cur > 1) prevBtn.addEventListener('click', () => Main.loadPage(cur - 1));
        navRight.appendChild(prevBtn);

        // 页码按钮
        const addPageBtn = (page) => {
            const isCurrent = page === cur;
            const btn = Utils.createElement('button', { text: page });
            btn.className = 'sewf-pg-btn' + (isCurrent ? ' active' : '');
            if (!isCurrent) btn.addEventListener('click', () => Main.loadPage(page));
            navRight.appendChild(btn);
        };

        const addDots = () => {
            navRight.appendChild(Utils.createElement('span', { className: 'sewf-pg-dots', text: '\u2026' }));
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
        const nextBtn = Utils.createElement('button', { text: '\u203A' });
        nextBtn.className = cur >= totalPages ? 'sewf-pg-btn disabled' : 'sewf-pg-btn';
        if (cur < totalPages) nextBtn.addEventListener('click', () => Main.loadPage(cur + 1));
        navRight.appendChild(nextBtn);

        // 跳转
        const jumpWrap = Utils.createElement('div', { className: 'sewf-pg-jump' });
        const jumpInput = Utils.createElement('input', {
            type: 'number', min: '1', max: totalPages, value: cur,
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
        const jumpBtn = Utils.createElement('button', { text: '跳转', className: 'sewf-pg-jump-btn' });
        jumpBtn.addEventListener('click', () => {
            const v = parseInt(jumpInput.value);
            if (v >= 1 && v <= totalPages && v !== cur) Main.loadPage(v);
        });
        jumpWrap.appendChild(jumpInput);
        jumpWrap.appendChild(jumpBtn);
        navRight.appendChild(jumpWrap);

        this.containerEl.appendChild(leftDiv);
        this.containerEl.appendChild(navRight);

        return this.containerEl;
    },
};
