// ================ 汉化模块（演员详情页 + 场景详情页） ================
// 字段/值映射复用 stash-jellyfin-proxy-zh 项目的映射表
const Hanhua = {
    FIELD_LABELS: {
        'Career': '职业生涯',
        'Birthdate': '出生日期',
        'Height': '身高',
        'Measurements': '三围',
        'Breast type': '胸型',
        'Nationality': '国籍',
        'Ethnicity': '族裔',
        'Eye color': '瞳色',
        'Hair color': '发色',
        'Tattoos': '纹身',
        'Piercings': '穿孔',
        'Aliases': '别名',
    },

    // 值映射（SJP _FAKE_TITS_ZH / _ETHNICITY_ZH / _HAIR_COLOR_ZH / _EYE_COLOR_ZH + 国家全名）
    FIELD_VALUES: {
        // fake_tits
        'Natural': '天然', 'Na': '未标注', 'Fake': '假体', 'Augmented': '假体',
        // ethnicity
        'Asian': '亚洲', 'Caucasian': '白种', 'Latin': '拉丁', 'Black': '黑人',
        'Mixed': '混血', 'Middle Eastern': '中东',
        // hair_color
        'Brunette': '深棕', 'Blonde': '金色', 'Blond': '金色', 'Auburn': '红棕', 'Bald': '光头',
        'Various': '多变', 'Other': '其他',
        // eye_color（Black/Red/Grey 与上重复，合并）
        'Brown': '棕色', 'Blue': '蓝色', 'Hazel': '榛色', 'Green': '绿色', 'Grey': '灰色',
        // country 全名
        'United States': '美国', 'Canada': '加拿大', 'Japan': '日本', 'Russia': '俄罗斯',
        'Brazil': '巴西', 'France': '法国', 'United Kingdom': '英国', 'Germany': '德国',
        'Spain': '西班牙', 'Italy': '意大利', 'Ukraine': '乌克兰', 'Czechia': '捷克',
        'Czech Republic': '捷克', 'Hungary': '匈牙利', 'Netherlands': '荷兰', 'Poland': '波兰',
        'Romania': '罗马尼亚', 'Colombia': '哥伦比亚', 'Venezuela': '委内瑞拉', 'Argentina': '阿根廷',
        'Mexico': '墨西哥', 'Thailand': '泰国', 'South Korea': '韩国', 'China': '中国',
        'Taiwan': '台湾', 'Hong Kong': '香港', 'Philippines': '菲律宾', 'Vietnam': '越南',
        'India': '印度', 'Australia': '澳大利亚', 'New Zealand': '新西兰', 'Israel': '以色列',
        'Turkey': '土耳其', 'Greece': '希腊', 'Sweden': '瑞典', 'Norway': '挪威',
        'Denmark': '丹麦', 'Finland': '芬兰', 'Belgium': '比利时', 'Switzerland': '瑞士',
        'Austria': '奥地利', 'Portugal': '葡萄牙', 'Ireland': '爱尔兰', 'Croatia': '克罗地亚',
        'Serbia': '塞尔维亚', 'Bulgaria': '保加利亚', 'Estonia': '爱沙尼亚', 'Latvia': '拉脱维亚',
        'Lithuania': '立陶宛', 'Slovakia': '斯洛伐克', 'Slovenia': '斯洛文尼亚',
        'Dominican Republic': '多米尼加', 'Puerto Rico': '波多黎各', 'Cuba': '古巴',
        'Jamaica': '牙买加', 'Haiti': '海地', 'Nigeria': '尼日利亚', 'Ghana': '加纳',
        'Kenya': '肯尼亚', 'Morocco': '摩洛哥', 'South Africa': '南非', 'Egypt': '埃及',
        'Indonesia': '印度尼西亚', 'Malaysia': '马来西亚', 'Singapore': '新加坡',
        'Mongolia': '蒙古', 'Kazakhstan': '哈萨克斯坦', 'Belarus': '白俄罗斯',
        'Moldova': '摩尔多瓦', 'Albania': '阿尔巴尼亚', 'North Macedonia': '北马其顿',
        'Bosnia and Herzegovina': '波黑', 'Montenegro': '黑山', 'Georgia': '格鲁吉亚',
        'Armenia': '亚美尼亚', 'Azerbaijan': '阿塞拜疆', 'Uzbekistan': '乌兹别克斯坦',
        'Iran': '伊朗', 'Iraq': '伊拉克', 'Saudi Arabia': '沙特阿拉伯',
        'United Arab Emirates': '阿联酋', 'Lebanon': '黎巴嫩', 'Jordan': '约旦',
        'Pakistan': '巴基斯坦', 'Bangladesh': '孟加拉国', 'Sri Lanka': '斯里兰卡',
        'Nepal': '尼泊尔', 'Myanmar': '缅甸', 'Cambodia': '柬埔寨', 'Laos': '老挝',
        'Chile': '智利', 'Peru': '秘鲁', 'Ecuador': '厄瓜多尔', 'Bolivia': '玻利维亚',
        'Paraguay': '巴拉圭', 'Uruguay': '乌拉圭', 'Guatemala': '危地马拉',
        'Honduras': '洪都拉斯', 'El Salvador': '萨尔瓦多', 'Nicaragua': '尼加拉瓜',
        'Costa Rica': '哥斯达黎加', 'Panama': '巴拿马', 'Cameroon': '喀麦隆',
        'Congo': '刚果', 'Angola': '安哥拉', 'Mozambique': '莫桑比克',
        'Ethiopia': '埃塞俄比亚', 'Tanzania': '坦桑尼亚', 'Zambia': '赞比亚',
        'Zimbabwe': '津巴布韦', 'Ivory Coast': '科特迪瓦', 'Senegal': '塞内加尔',
        'Togo': '多哥', 'Benin': '贝宁', 'Equatorial Guinea': '赤道几内亚',
        'Gabon': '加蓬', 'Chad': '乍得', 'Sudan': '苏丹', 'Libya': '利比亚',
        'Tunisia': '突尼斯', 'Algeria': '阿尔及利亚', 'Guyana': '圭亚那',
        'Trinidad and Tobago': '特立尼达和多巴哥', 'Bahamas': '巴哈马', 'Fiji': '斐济',
        'Papua New Guinea': '巴布亚新几内亚', 'Samoa': '萨摩亚', 'Tonga': '汤加',
        'Greenland': '格陵兰', 'Iceland': '冰岛', 'Luxembourg': '卢森堡', 'Malta': '马耳他',
        'Cyprus': '塞浦路斯', 'Kosovo': '科索沃', 'Qatar': '卡塔尔',
        'Kuwait': '科威特', 'Oman': '阿曼', 'Yemen': '也门', 'Syria': '叙利亚',
        'Afghanistan': '阿富汗', 'Turkmenistan': '土库曼斯坦', 'Kyrgyzstan': '吉尔吉斯斯坦',
        'Tajikistan': '塔吉克斯坦', 'Bhutan': '不丹', 'Maldives': '马尔代夫',
        'Brunei': '文莱', 'East Timor': '东帝汶', 'Palestine': '巴勒斯坦',
    },

    TABS: {
        'Scenes': '场景',
        'Scene Pairings': '场景搭档',
        'Links': '链接',
        'Edits': '编辑',
        'Description': '简介',
        'Fingerprints': '指纹',
        'Fingerprint': '指纹',
    },

    // 场景详情页元数据标签（.scene-info 内 "Studio Code:" 等）
    SCENE_META_LABELS: {
        'Studio Code:': '工作室编号：',
        'Duration:': '时长：',
        'Director:': '导演：',
        'Date:': '日期：',
        'Description:': '简介：',
        'Tags:': '标签：',
        'Studio:': '工作室：',
        // 注意：无冒号版必须放最后（"Studio Code:" / "Studio:" 会先匹配各自的带冒号 key）
        'Studio': '工作室',
    },

    // 导航栏（全局，精确匹配避免误伤用户菜单/搜索框）
    NAV_LABELS: {
        'Home': '首页',
        'Performers': '演员',
        'Scenes': '场景',
        'Studios': '工作室',
        'Tags': '标签',
        'Edits': '编辑',
        'Sites': '站点',
        'Guidelines': '指南',
    },

    // 主页区块标题
    HEADINGS: {
        'Trending scenes': '热门场景',
        'Recently added scenes': '最新添加',
    },

    // 原生排序 select 选项（value 即 GraphQL 枚举，只改显示文本）
    SORT_OPTIONS: {
        'Release Date': '发行日期',
        'Title': '标题',
        'Trending': '热门',
        'Popularity': '热度',
        'Created At': '创建时间',
        'Updated At': '更新时间',
        'Duration': '时长',
    },

    // 原生场景列表控件（排序 select + 标签/收藏筛选 react-select + 收藏 checkbox）
    SCENE_CONTROLS_LABELS: {
        'Filter by tag': '按标签筛选',
        'Favorite filter': '收藏筛选',
        'All Favorites': '全部收藏',
        'Favorite Performers': '收藏演员',
        'Favorite Studios': '收藏工作室',
        'Only favorite performers': '仅收藏演员',
        'Only favorite studios': '仅收藏工作室',
    },

    _translateSceneControls() {
        // 排序 select 选项（场景/工作室/演员页通用，value 即 GraphQL 枚举，只改显示文本）
        document.querySelectorAll('select option').forEach(opt => {
            const zh = this.SORT_OPTIONS[opt.textContent.trim()];
            if (zh) opt.textContent = zh;
        });
        // 标签/收藏筛选 react-select（placeholder/当前值/菜单选项）
        document.querySelectorAll('.react-select__single-value, .react-select__option, .react-select__placeholder').forEach(el => {
            const t = el.textContent.trim();
            const zh = this.SCENE_CONTROLS_LABELS[t];
            if (zh) el.textContent = zh;
        });
        // 收藏 checkbox（Only favorite performers/studios）
        document.querySelectorAll('label, .form-check-label').forEach(el => {
            const t = el.textContent.trim();
            const zh = this.SCENE_CONTROLS_LABELS[t];
            if (zh) el.textContent = zh;
        });
    },

    _translateHeadings() {
        document.querySelectorAll('h4').forEach(h => {
            const zh = this.HEADINGS[h.textContent.trim()];
            if (!zh) return;
            // 标题链接在 <a> 内（<h4><a>Trending scenes</a></h4>）：
            // 递归替换 h4 下所有非空文本节点，保留链接元素（点击跳转列表）
            const walker = document.createTreeWalker(h, NodeFilter.SHOW_TEXT);
            let node;
            while ((node = walker.nextNode())) {
                if (node.textContent.trim()) node.textContent = zh;
            }
        });
    },

    _translateNav() {
        document.querySelectorAll('nav a, header a, .navbar a').forEach(a => {
            const zh = this.NAV_LABELS[a.textContent.trim()];
            if (!zh) return;
            // 只替换直接文本节点，保留子元素（如外部链接图标）
            a.childNodes.forEach(node => {
                if (node.nodeType === Node.TEXT_NODE) {
                    node.textContent = node.textContent.trim() ? zh : '';
                }
            });
        });
    },

    _translatePerformerInfo() {
        // 演员信息字段表格（限定 .PerformerInfo 内，避免误伤其它表格）
        document.querySelectorAll('.PerformerInfo table.table-striped tr').forEach(tr => {
            const tds = tr.querySelectorAll('td');
            if (tds.length < 2) return;
            const label = tds[0].textContent.trim();
            if (this.FIELD_LABELS[label]) {
                tds[0].textContent = this.FIELD_LABELS[label];
                // 中文 label 在窄列里会逐字竖排（原站列宽按英文设计）：
                // 强制不换行让列自适应 + 与多行值列顶部对齐
                tds[0].style.whiteSpace = 'nowrap';
                tds[0].style.verticalAlign = 'top';
            }
            const val = tds[1].textContent.trim();
            if (this.FIELD_VALUES[val]) {
                tds[1].textContent = this.FIELD_VALUES[val];
            } else if (label === 'Birthdate') {
                // 2005-01-1421 years old → 2005-01-14 · 21岁
                const m = val.match(/^(\d{4}-\d{2}-\d{2})(\d+)\s*years? old$/i);
                if (m) tds[1].textContent = m[1] + ' · ' + m[2] + '岁';
            } else if (label === 'Height') {
                const m = val.match(/^(\d+)\s*cm$/i);
                if (m) tds[1].textContent = m[1] + ' 厘米';
            } else if (label === 'Career') {
                if (/^Active\b/.test(val)) tds[1].textContent = val.replace(/^Active\b/, '活跃');
            }
        });
    },

    _translateSceneMeta() {
        // 场景详情页元数据行（"Studio Code: 107142" 等，值可能在 <strong> 里）
        // 只替换文本节点前缀，保留子元素结构；全页遍历，key 为带冒号精确前缀，误伤率极低
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        let node;
        while ((node = walker.nextNode())) {
            const t = node.textContent;
            for (const [en, zh] of Object.entries(this.SCENE_META_LABELS)) {
                if (t.startsWith(en)) {
                    const rest = t.slice(en.length);
                    // 词边界保护：'Studios' 不能匹配 'Studio'（rest 以字母开头则跳过）
                    if (/[A-Za-z]/.test(rest.charAt(0))) continue;
                    node.textContent = zh + rest.replace(/^\s+/, '');
                    // React 可能把冒号拆成独立文本节点（<b>Studio</b> + ":"）
                    // 无冒号 key 完全匹配时，把下一兄弟节点的半角冒号统一为全角
                    if (rest === '' && !en.endsWith(':') && node.nextSibling &&
                        node.nextSibling.nodeType === Node.TEXT_NODE &&
                        /^[:：]/.test(node.nextSibling.textContent)) {
                        node.nextSibling.textContent = node.nextSibling.textContent.replace(/^[:：]/, '：');
                    }
                    break;
                }
            }
        }
    },

    _translateFilters() {
        // 筛选控件（label / react-select placeholder）
        document.querySelectorAll('.react-select__placeholder, label, .form-check-label, span').forEach(el => {
            if (el.closest('.PerformerInfo')) return;
            const t = el.textContent.trim();
            if (t.startsWith('Filter by studios')) el.textContent = '按工作室筛选';
            else if (t.startsWith('Filter by tag')) el.textContent = '按标签筛选';
            else if (t.startsWith('Only favorite studios')) el.textContent = '仅收藏工作室';
        });
    },

    _translateTabs() {
        // 详情页 tabs（仅 [role=tab] 与 #scene-tabs-tab-*，避免误伤导航栏）
        document.querySelectorAll('[role="tab"]').forEach(el => {
            const t = el.textContent.trim();
            if (this.TABS[t]) el.textContent = this.TABS[t];
        });
    },

    // 原生渲染的图片直连原站（https://stashdb.org/images/...），
    // 改写为相对路径走反代 /images/ 磁盘缓存：重复浏览命中缓存，省回源流量
    _proxyImages() {
        const hosts = ['stashdb.org', 'javstash.org', 'fansdb.cc', 'pmvstash.org'];
        document.querySelectorAll('img').forEach(img => {
            const s = img.getAttribute('src');
            if (!s || !s.startsWith('http')) return;
            let m;
            try { m = new URL(s); } catch (e) { return; }
            if (hosts.includes(m.hostname) && m.pathname.startsWith('/images/')) {
                img.src = m.pathname + m.search;
            }
        });
    },

    translate() {
        this._translateNav();
        this._translateHeadings();
        this._proxyImages();
        const p = location.pathname;
        if (p.includes('/performers/')) {
            this._translatePerformerInfo();
            this._translateFilters();
            this._translateSceneControls(); // 场景 tab 的原生排序/筛选
        } else if (p.includes('/scenes/')) {
            this._translateSceneMeta();
        } else if (p.includes('/studios/')) {
            this._translateSceneControls(); // All Scenes tab 的原生排序/筛选
        } else if (p.endsWith('/scenes')) {
            // 场景列表页：原生排序/收藏筛选控件汉化
            this._translateSceneControls();
        }
        this._translateTabs();

        // 场景详情页：标签增强（别名→本地主名 / 本地不存在标记）
        if (p.includes('/scenes/')) {
            TagResolver.process();
        }

        // 本地场景匹配（卡片 + 详情页"本地播放"按钮）
        SceneMatch.process();
    },

    start() {
        this.translate();
        // 立即翻译（无 debounce）：React 每插入一批节点就马上翻译，
        // 消除"先英文后中文"的闪现。translate 幂等（已翻译文本不匹配英文映射），不会死循环。
        const mo = new MutationObserver(() => this.translate());
        mo.observe(document.body, { childList: true, subtree: true });
    },
};

// ================ 场景标签增强解析 ================
// 前端只负责收集标签文本 → 批量 POST /api/resolve-tags（后端内存索引，毫秒级）→ 渲染结果。
// 结果三类：
//   found && isAlias          → 替换为本地主名 + 绿边 + title
//   found && !isAlias         → 本地已有同名主标签，保持原样
//   !found                    → 红框 + "❌ 本地不存在" + title
const TagResolver = {
    cache: {},       // 标签文本 → {primary, isAlias, found}
    inflight: null,  // 当前请求 promise（防止并发重复请求）

    process() {
        if (!location.pathname.includes('/scenes/')) return;
        const anchors = [...document.querySelectorAll('.scene-tag-list .tag-item a')];
        const pending = anchors.filter(a => !a.dataset.tagResolved);
        if (!pending.length) return;

        const names = [...new Set(pending.map(a => a.textContent.trim()).filter(Boolean))];
        if (!names.length) return;

        const apply = () => {
            anchors.forEach(a => {
                if (a.dataset.tagResolved) return;
                const name = a.textContent.trim();
                const r = this.cache[name];
                if (!r || !r.found) return; // 只处理找到的（别名替换），不存在的留给 markNotFound
                a.dataset.tagResolved = '1';
                const item = a.closest('.tag-item');
                if (r.isAlias && r.primary && r.primary !== name) {
                    a.textContent = r.primary;
                    if (item) {
                        item.classList.add('tag-alias-replaced');
                        item.setAttribute('title', `本地标签: ${name} → ${r.primary}`);
                    }
                }
            });
        };

        const markNotFound = () => {
            anchors.forEach(a => {
                if (a.dataset.tagResolved) return;
                const name = a.textContent.trim();
                const r = this.cache[name];
                if (!r || r.found) return; // 只处理确认不存在的
                a.dataset.tagResolved = '1';
                const item = a.closest('.tag-item');
                if (item) {
                    item.classList.add('tag-not-found');
                    item.setAttribute('title', '本地 Stash 不存在此标签');
                }
            });
        };

        const uncached = names.filter(n => !(n in this.cache));
        if (!uncached.length) {
            apply();
            markNotFound();
            return;
        }

        if (this.inflight) {
            // 有请求在飞：等它结束后再处理新出现的元素
            this.inflight.then(() => this.process()).catch(() => {});
            return;
        }

        this.inflight = fetch('/api/resolve-tags', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tags: uncached }),
        })
            .then(r => r.json())
            .then(data => {
                this.inflight = null;
                if (!data.results) return; // enabled:false 或 error，静默跳过
                data.results.forEach(r => { this.cache[r.name] = r; });
                apply();
                markNotFound();
            })
            .catch(() => { this.inflight = null; });
    },
};

// 标签增强样式（与失败品脚本同款视觉）
if (!document.getElementById('sewf-tag-css')) {
    const style = document.createElement('style');
    style.id = 'sewf-tag-css';
    style.textContent = `
        .scene-tag-list .tag-item.tag-not-found {
            border: 2px solid #ff4757 !important;
            background-color: #ffe6e6 !important;
            position: relative;
        }
        .scene-tag-list .tag-item.tag-not-found::after {
            content: "❌ 本地不存在";
            position: absolute;
            top: -20px;
            right: 0;
            background: #ff4757;
            color: white;
            padding: 2px 5px;
            border-radius: 3px;
            font-size: 10px;
            white-space: nowrap;
            z-index: 10;
        }
        .scene-tag-list .tag-item.tag-alias-replaced {
            border-left: 3px solid #4CAF50 !important;
        }
        /* 本地播放按钮（深色玻璃风） */
        .sewf-local-btn {
            display: inline-block;
            margin-top: 6px;
            margin-right: 6px;
            padding: 4px 10px;
            border-radius: 6px;
            background: linear-gradient(135deg, #28a745, #1e7e34);
            color: #fff !important;
            font-size: 12px;
            font-weight: 600;
            text-decoration: none !important;
            cursor: pointer;
            opacity: .9;
            transition: opacity .2s;
        }
        .sewf-local-btn:hover { opacity: 1; }
        .sewf-local-btn-lg { margin-top: 8px; padding: 6px 14px; font-size: 14px; }
        /* 卡片内播放图标（演员统计行内，圆形小按钮） */
        .sewf-local-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: linear-gradient(135deg, #28a745, #1e7e34);
            color: #fff !important;
            font-size: 10px;
            line-height: 1;
            text-decoration: none !important;
            cursor: pointer;
            opacity: .9;
            transition: opacity .2s, transform .2s;
            flex: none;
        }
        .sewf-local-icon:hover { opacity: 1; transform: scale(1.12); }
    `;
    document.head.appendChild(style);
}

// ================ 本地场景匹配（stashdb 场景 ID → 本地库） ================
// 前端只负责收集页面上的 stashdb 场景 ID → 批量 POST /api/resolve-scenes
// （后端内存索引，毫秒级）→ 命中的卡片/详情页加"本地播放"按钮（跳转本地 Stash）。
const SceneMatch = {
    cache: {},      // stashdb 场景 ID → {localId, url, found}
    inflight: null, // 当前请求 promise

    process() {
        const ids = new Set();
        // 脚本渲染的卡片（#sewf-grid 内）
        document.querySelectorAll('#sewf-grid .col-3[data-scene-id]:not([data-local-matched])').forEach(col => {
            const id = col.getAttribute('data-scene-id');
            if (id) ids.add(id);
        });
        // 场景详情页
        if (location.pathname.includes('/scenes/')) {
            const m = location.pathname.match(/\/scenes\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/);
            if (m && !document.querySelector('[data-local-scene-match]')) ids.add(m[1]);
        }
        if (!ids.size) return;

        const pending = [...ids].filter(id => !(id in this.cache));
        if (!pending.length) { this.apply(); return; }

        if (this.inflight) {
            this.inflight.then(() => this.process()).catch(() => {});
            return;
        }

        this.inflight = fetch('/api/resolve-scenes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ids: pending }),
        })
            .then(r => r.json())
            .then(data => {
                this.inflight = null;
                if (!data.results) return; // enabled:false 或 error，静默跳过
                data.results.forEach(r => { this.cache[r.id] = r; });
                this.apply();
            })
            .catch(() => { this.inflight = null; });
    },

    apply() {
        // 卡片：命中本地 → card-footer 加按钮
        document.querySelectorAll('#sewf-grid .col-3[data-scene-id]:not([data-local-matched])').forEach(col => {
            const id = col.getAttribute('data-scene-id');
            const r = this.cache[id];
            if (!r) return;
            col.setAttribute('data-local-matched', '1');
            if (r.found && r.url) this._addCardButton(col, r);
        });
        // 详情页：标题下加按钮
        if (location.pathname.includes('/scenes/')) {
            const m = location.pathname.match(/\/scenes\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/);
            if (m && !document.querySelector('[data-local-scene-match]')) {
                const r = this.cache[m[1]];
                if (r && r.found && r.url) this._addDetailButton(r);
            }
        }
        // 本地筛选（隐藏本地已有/只看本地）依赖匹配结果，查询完成后重新过滤
        if (typeof Sorter !== 'undefined' && Sorter.apply) {
            Sorter.apply();
        }
    },

    _addCardButton(col, r) {
        // ① 优先插入指纹条中间（"指纹: 50  ▶  提交: 219"）
        const fpBar = col.querySelector('.sewf-fingerprint');
        if (fpBar && fpBar.children.length >= 2) {
            if (fpBar.querySelector('.sewf-local-icon')) return;
            const icon = this._makeIcon(r);
            fpBar.insertBefore(icon, fpBar.children[1]);
            return;
        }
        // ② 其次插入演员统计行（"演员 (N)  ▶  ♀️1 ♂️1 ⭐1"）
        const statsRow = col.querySelector('.performer-section > div');
        if (statsRow) {
            if (statsRow.querySelector('.sewf-local-icon')) return;
            const icon = this._makeIcon(r);
            if (statsRow.children.length >= 2) {
                statsRow.insertBefore(icon, statsRow.children[1]);
            } else {
                statsRow.appendChild(icon);
            }
            return;
        }
        // ③ fallback 到 card-footer 末尾
        const footer = col.querySelector('.card-footer');
        if (!footer || footer.querySelector('.sewf-local-icon, .sewf-local-btn')) return;
        footer.appendChild(this._makeIcon(r));
    },

    _makeIcon(r) {
        const icon = document.createElement('a');
        icon.className = 'sewf-local-icon';
        icon.href = r.url;
        icon.target = '_blank';
        icon.rel = 'noopener';
        icon.textContent = '▶';
        icon.title = '本地 Stash 已有此场景，点击播放';
        return icon;
    },

    _addDetailButton(r) {
        const h3 = document.querySelector('main h3');
        if (!h3) return;
        const btn = document.createElement('a');
        btn.className = 'sewf-local-btn sewf-local-btn-lg';
        btn.href = r.url;
        btn.target = '_blank';
        btn.rel = 'noopener';
        btn.textContent = '🎬 本地播放';
        btn.setAttribute('data-local-scene-match', '1');
        btn.title = '本地 Stash 已有此场景，点击跳转播放';
        h3.insertAdjacentElement('afterend', btn);
    },
};

Hanhua.start();
