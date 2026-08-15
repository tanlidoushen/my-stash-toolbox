// ================ 配置模块 ================
const Config = {
    SITES: {
        'stashdb.org': {
            API_URL: 'https://stashdb.org/graphql',
            API_KEY: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOiIxYTkzN2NhYS05YjIyLTRiODAtYTdiMy1hMmRmMjRiMjJiNTIiLCJzdWIiOiJBUElLZXkiLCJpYXQiOjE3MDk1NTYzMzV9.A3e1xKO6igNzUu063q6t9lSj_9r__84aauo5ZZinfm8',
            BASE_URL: 'https://stashdb.org',
        },
        'javstash.org': {
            API_URL: 'https://javstash.org/graphql',
            API_KEY: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOiJkMmVkYmI3Zi1hNTQ1LTQzMTktYTRmMS05YjcwMTNlNDg1NWMiLCJzdWIiOiJBUElLZXkiLCJpYXQiOjE3NDMyMDYyNDR9.RfTCDEJBAcHs1OcBfG6SRjJWzo6UmglDvDQiv3ymnxo',
            BASE_URL: 'https://javstash.org',
        },
        'fansdb.cc': {
            API_URL: 'https://fansdb.cc/graphql',
            API_KEY: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOiJmNDk4MDY3MS1iOTYxLTQ1ZTAtOGRlOC1kYjY5Y2UxMzQzNmQiLCJzdWIiOiJBUElLZXkiLCJpYXQiOjE3NDY4OTIxMTN9._mshdDJJu1LvUNFR7_UYCLTjhBBdnNLOSEKZoXvoZ8w',
            BASE_URL: 'https://fansdb.cc',
        },
    },

    get API_URL() { return location.origin + '/graphql'; },
    get API_KEY() { return this._currentSite().API_KEY; },
    get BASE_URL() { return location.origin; },

    _currentSite() {
        const host = location.hostname.replace('www.', '');
        return this.SITES[host] || this.SITES['stashdb.org'];
    },


    STORAGE_KEYS: {
        SORT_METHOD: 'sewf_sort_method',
        HIDE_NO_FEMALE: 'sewf_hide_no_female',
        HIDE_YOUNG_FEMALE_AGE: 'sewf_hide_young_female_age',
        LOCAL_FILTER: 'sewf_local_filter',
        PER_PAGE: 'sewf_per_page',
        PAGE: 'sewf_page',
    },

    PAGE_TYPES: {
        HOME: 'home',
        TAG: 'tag',
        PERFORMER: 'performer',
        STUDIO: 'studio',
        SCENES: 'scenes',
    },

    SORT_METHODS: {
        DEFAULT: 'default',
        AGE: 'age',
        SUBMISSIONS: 'submissions',
    },

    // 本地场景筛选：none=不过滤, hide=隐藏本地已有, only=只看本地
    LOCAL_FILTERS: {
        NONE: 'none',
        HIDE: 'hide',
        ONLY: 'only',
    },

    PAGINATION: {
        DEFAULT_PER_PAGE: 20,
        PERFORMER_PER_PAGE: 40,
        PER_PAGE_OPTIONS: [10, 20, 30, 40, 50, 100],
    },

    // 自建卡片容器选择器
    GRID_SELECTOR: {
        PERFORMER: '.PerformerScenes',
        SCENES: '.scenes-list',
        DEFAULT: '.page-content',
    },

    COLORS: {
        FINGERPRINT: {
            LOW: '#4CAF50',
            MEDIUM: '#f093fb',
            HIGH: '#f5576c',
            DEFAULT: '#667eea',
        },
        BUTTONS: {
            DEFAULT: 'linear-gradient(135deg, #6c757d 0%, #495057 100%)',
            ACTIVE: '#28a745',
            AGE: 'linear-gradient(135deg, #f7971e 0%, #ffd200 100%)',
            SUBMISSIONS: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            HIDE_FEMALE: 'linear-gradient(135deg, #fd7e14 0%, #e8590c 100%)',
            SHOW_ALL: '#dc3545',
        },
        PERFORMER_AVATAR: {
            FEMALE: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
            MALE: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
            OTHER: 'linear-gradient(135deg, #9c27b0 0%, #673ab7 100%)',
            FAVORITE_FEMALE: 'linear-gradient(135deg, #FFD700 0%, #FFA500 100%)',
            FAVORITE_MALE: 'linear-gradient(135deg, #FFD700 0%, #FF8C00 100%)',
            FAVORITE_OTHER: 'linear-gradient(135deg, #FFD700 0%, #DAA520 100%)',
        },
    },

    THRESHOLDS: {
        SUBMISSIONS: {
            LOW: 5,
            MEDIUM: 20,
            HIGH: 50,
        },
    },

    SORT_PARAM_MAP: {
        date: 'DATE',
        title: 'TITLE',
        trending: 'TRENDING',
        popularity: 'POPULARITY',
        created_at: 'CREATED_AT',
        updated_at: 'UPDATED_AT',
        duration: 'DURATION',
    },

    // URL ?favorite= → GraphQL FavoriteFilter 枚举（原站原生筛选控件值）
    FAVORITE_PARAM_MAP: {
        performer: 'PERFORMER',
        studio: 'STUDIO',
        all: 'ALL',
    },
};