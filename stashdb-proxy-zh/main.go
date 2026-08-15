package main

import (
	"bytes"
	"crypto/md5"
	_ "embed"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"
)

//go:embed enhanced.js
var enhancedJS []byte

// ============ 配置 ============

type Config struct {
	Listen string `json:"listen"`
	Site   struct {
		Target string `json:"target"`
		Cookie string `json:"cookie"`
	} `json:"site"`
	ImageCache struct {
		MaxSizeGB int `json:"maxSizeGB"`
		TTLDays   int `json:"ttlDays"`
	} `json:"imageCache"`
	CacheDir     string `json:"cacheDir"`
	FaviconProxy string `json:"faviconProxy"` // favicon 回源专用代理（DDG 需代理可达）
	ListCache    struct {
		TTLSeconds int `json:"ttlSeconds"` // 场景列表查询缓存 TTL，默认 300（5 分钟）
		MaxMB      int `json:"maxMB"`      // 缓存容量上限 MB，默认 50
	} `json:"listCache"`
	LocalStash   struct {
		GraphQL        string `json:"graphql"`        // 本地 Stash GraphQL 端点，如 http://192.168.4.1:9999/graphql
		RefreshMinutes int    `json:"refreshMinutes"` // 标签/场景索引刷新周期，默认 60
		PlayerURL      string `json:"playerUrl"`      // 本地播放器基础 URL（跳转播放用），如 https://stash.932177.xyz:8081
	} `json:"localStash"`
}

func loadConfig(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}
	if cfg.Listen == "" {
		cfg.Listen = ":8900"
	}
	if cfg.Site.Target == "" {
		cfg.Site.Target = "https://stashdb.org"
	}
	if cfg.ImageCache.MaxSizeGB == 0 {
		cfg.ImageCache.MaxSizeGB = 10
	}
	if cfg.ImageCache.TTLDays == 0 {
		cfg.ImageCache.TTLDays = 30
	}
	if cfg.CacheDir == "" {
		cfg.CacheDir = "./cache"
	}
	return &cfg, nil
}

// ============ 磁盘缓存（图片/flag/favicon 通用） ============

type cacheMeta struct {
	ContentType string `json:"ct"`
	ETag        string `json:"etag"`
	LastMod     string `json:"lm"`
	SavedAt     int64  `json:"sa"`
}

type diskCache struct {
	dir   string
	ttl   time.Duration
	max   int64
	mu    sync.Mutex
	locks map[string]*sync.Mutex
}

func newDiskCache(dir string, ttl time.Duration, maxBytes int64) *diskCache {
	return &diskCache{dir: dir, ttl: ttl, max: maxBytes, locks: make(map[string]*sync.Mutex)}
}

func (c *diskCache) keyOf(path, rawQuery string) string {
	h := md5.Sum([]byte(path + "?" + rawQuery))
	return hex.EncodeToString(h[:])
}

func (c *diskCache) filePaths(k string) (body, meta string) {
	sub := filepath.Join(c.dir, k[:2])
	return filepath.Join(sub, k[2:]), filepath.Join(sub, k[2:]+".meta")
}

func (c *diskCache) getLock(k string) *sync.Mutex {
	c.mu.Lock()
	defer c.mu.Unlock()
	l, ok := c.locks[k]
	if !ok {
		l = &sync.Mutex{}
		c.locks[k] = l
	}
	return l
}

func (c *diskCache) get(k string) ([]byte, cacheMeta, bool) {
	bodyPath, metaPath := c.filePaths(k)
	body, err := os.ReadFile(bodyPath)
	if err != nil {
		return nil, cacheMeta{}, false
	}
	var m cacheMeta
	metaData, err := os.ReadFile(metaPath)
	if err == nil {
		_ = json.Unmarshal(metaData, &m)
	}
	return body, m, true
}

func (c *diskCache) put(k string, body []byte, m cacheMeta) {
	bodyPath, metaPath := c.filePaths(k)
	_ = os.MkdirAll(filepath.Dir(bodyPath), 0o755)
	if err := os.WriteFile(bodyPath, body, 0o644); err != nil {
		log.Printf("[cache] write body err: %v", err)
		return
	}
	m.SavedAt = time.Now().Unix()
	metaData, _ := json.Marshal(m)
	if err := os.WriteFile(metaPath, metaData, 0o644); err != nil {
		log.Printf("[cache] write meta err: %v", err)
	}
}

func (c *diskCache) touch(k string) {
	bodyPath, _ := c.filePaths(k)
	_ = os.Chtimes(bodyPath, time.Now(), time.Now())
}

// 定期容量控制：超限按 mtime 从旧到新删
func (c *diskCache) enforceLoop() {
	for {
		time.Sleep(5 * time.Minute)
		c.enforceOnce()
	}
}

func (c *diskCache) enforceOnce() {
	var files []struct {
		path string
		size int64
		m    time.Time
	}
	var total int64
	_ = filepath.Walk(c.dir, func(path string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() {
			return nil
		}
		if strings.HasSuffix(path, ".meta") {
			return nil
		}
		files = append(files, struct {
			path string
			size int64
			m    time.Time
		}{path, info.Size(), info.ModTime()})
		total += info.Size()
		return nil
	})
	if total <= c.max {
		return
	}
	sort.Slice(files, func(i, j int) bool { return files[i].m.Before(files[j].m) })
	for _, f := range files {
		if total <= c.max {
			break
		}
		_ = os.Remove(f.path)
		_ = os.Remove(f.path + ".meta")
		total -= f.size
		log.Printf("[cache] evict %s", filepath.Base(f.path))
	}
}

// ============ 缓存代理（图片/flag/favicon） ============

type proxyHandler struct {
	cfg      *Config
	cache    *diskCache
	upstream *url.URL
	client   *http.Client
	rewrite  func(path string) (string, string) // 返回 (新path, 新query)，nil 则原样
}

var nocacheRe = regexp.MustCompile(`(^|&)nocache=[^&]*`)

func stripQuery(rawQuery string) string {
	return nocacheRe.ReplaceAllString(rawQuery, "")
}

func (h *proxyHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	rawQuery := stripQuery(r.URL.RawQuery)
	key := h.cache.keyOf(r.URL.Path, rawQuery)
	noCache := r.URL.Query().Get("nocache") != ""

	// 1. 缓存命中（TTL 内）
	if !noCache {
		if body, m, ok := h.cache.get(key); ok {
			age := time.Now().Unix() - m.SavedAt
			if age < int64(h.cache.ttl.Seconds()) {
				w.Header().Set("Content-Type", m.ContentType)
				w.Header().Set("X-Cache-Status", "HIT")
				w.Header().Set("Content-Length", strconv.Itoa(len(body)))
				w.Write(body)
				return
			}
		}
	}

	// 2. 单飞：同 key 并发只回源一次
	lock := h.cache.getLock(key)
	lock.Lock()
	defer lock.Unlock()

	// 锁内复查缓存（别的 goroutine 可能已回源）
	if !noCache {
		if body, m, ok := h.cache.get(key); ok {
			age := time.Now().Unix() - m.SavedAt
			if age < int64(h.cache.ttl.Seconds()) {
				w.Header().Set("Content-Type", m.ContentType)
				w.Header().Set("X-Cache-Status", "HIT")
				w.Header().Set("Content-Length", strconv.Itoa(len(body)))
				w.Write(body)
				return
			}
		}
	}

	// 3. 回源
	up := *h.upstream
	if h.rewrite != nil {
		up.Path, up.RawQuery = h.rewrite(r.URL.Path)
	} else {
		up.Path = r.URL.Path
		up.RawQuery = rawQuery
	}
	req, err := http.NewRequestWithContext(r.Context(), "GET", up.String(), nil)
	if err != nil {
		http.Error(w, "bad upstream", 500)
		return
	}
	req.Header.Set("Cookie", h.cfg.Site.Cookie)
	req.Header.Set("User-Agent", "Mozilla/5.0 (stashdb-proxy)")
	req.Header.Del("Accept-Encoding")

	// 过期缓存带协商头
	if body, m, ok := h.cache.get(key); ok {
		_ = body
		if m.ETag != "" {
			req.Header.Set("If-None-Match", m.ETag)
		}
		if m.LastMod != "" {
			req.Header.Set("If-Modified-Since", m.LastMod)
		}
	}

	client := h.client
	if client == nil {
		client = http.DefaultClient
	}
	resp, err := client.Do(req)
	if err != nil {
		log.Printf("[fetch] %s err: %v", up.String(), err)
		http.Error(w, "upstream fetch failed", 502)
		return
	}
	defer resp.Body.Close()

	switch {
	case resp.StatusCode == 304:
		// 上游未变，续期本地缓存
		if body, m, ok := h.cache.get(key); ok {
			h.cache.touch(key)
			m.SavedAt = time.Now().Unix()
			if metaData, err := json.Marshal(m); err == nil {
				_, metaPath := h.cache.filePaths(key)
				_ = os.WriteFile(metaPath, metaData, 0o644)
			}
			w.Header().Set("Content-Type", m.ContentType)
			w.Header().Set("X-Cache-Status", "REVALIDATED")
			w.Header().Set("Content-Length", strconv.Itoa(len(body)))
			w.Write(body)
			return
		}
		http.Error(w, "304 but no cache", 502)
		return
	case resp.StatusCode == 200:
		body, err := io.ReadAll(resp.Body)
		if err != nil {
			http.Error(w, "read upstream", 502)
			return
		}
		m := cacheMeta{
			ContentType: resp.Header.Get("Content-Type"),
			ETag:        resp.Header.Get("ETag"),
			LastMod:     resp.Header.Get("Last-Modified"),
		}
		h.cache.put(key, body, m)
		w.Header().Set("Content-Type", m.ContentType)
		w.Header().Set("X-Cache-Status", "MISS")
		w.Header().Set("Content-Length", strconv.Itoa(len(body)))
		w.Write(body)
		return
	default:
		// 非 200/304 不缓存，原样透传
		for k, vv := range resp.Header {
			for _, v := range vv {
				w.Header().Add(k, v)
			}
		}
		w.WriteHeader(resp.StatusCode)
		_, _ = io.Copy(w, resp.Body)
		return
	}
}

// ============ 全量反代 + HTML 注入 ============

var injectMarker = []byte(`id="sewf-inject"`)

// 反代下登录态保持：Set-Cookie 去掉 Domain/Secure/SameSite=None 属性
// （浏览器访问反代地址，Domain=stashdb.org 会被拒绝存储；HTTP 下 Secure cookie 不发送；
//   SameSite=None 强制要求 Secure，HTTP 下同样被拒收）
var cookieAttrRe = regexp.MustCompile(`(?i)(;\s*(?:domain|secure|samesite=none)(?:=[^;]*)?)`)

func rewriteCookie(c string) string {
	return cookieAttrRe.ReplaceAllString(c, "")
}

func rewriteSetCookies(h http.Header) {
	cookies := h.Values("Set-Cookie")
	if len(cookies) == 0 {
		return
	}
	h.Del("Set-Cookie")
	for _, c := range cookies {
		h.Add("Set-Cookie", rewriteCookie(c))
	}
}

func injectScript(body []byte) []byte {
	if bytes.Contains(body, injectMarker) {
		return body
	}
	tag := []byte(`<script id="sewf-inject" src="/enhanced.js"></script>`)
	idx := bytes.LastIndex(bytes.ToLower(body), []byte("</body>"))
	if idx < 0 {
		return body
	}
	out := make([]byte, 0, len(body)+len(tag)+8)
	out = append(out, body[:idx]...)
	out = append(out, tag...)
	out = append(out, body[idx:]...)
	return out
}

func (p *Proxy) reverseHandler() http.Handler {
	target := p.cfg.Site.Target
	rp := &httputil.ReverseProxy{
		Director: func(req *http.Request) {
			u, _ := url.Parse(target)
			req.URL.Scheme = u.Scheme
			req.URL.Host = u.Host
			req.Host = u.Host
			if req.Header.Get("Cookie") == "" {
				req.Header.Set("Cookie", p.cfg.Site.Cookie)
			}
			// 非 GET/HEAD 补 Origin/Referer，过 stashdb 的 CSRF 校验
			if req.Method != "GET" && req.Method != "HEAD" {
				req.Header.Set("Origin", target+"/")
				req.Header.Set("Referer", target+"/")
			}
			req.Header.Del("Accept-Encoding")
		},
		ModifyResponse: func(resp *http.Response) error {
			// 重定向 Location 指回 target 域名 → 改为相对路径（避免浏览器跳回原站）
			if loc := resp.Header.Get("Location"); loc != "" && strings.HasPrefix(loc, target) {
				if u, err := url.Parse(loc); err == nil {
					resp.Header.Set("Location", u.RequestURI())
				}
			}
			// 登录态保持：改写 Set-Cookie
			rewriteSetCookies(resp.Header)
			ct := resp.Header.Get("Content-Type")
			if !strings.Contains(ct, "text/html") {
				return nil
			}
			body, err := io.ReadAll(resp.Body)
			if err != nil {
				return err
			}
			_ = resp.Body.Close()
			newBody := injectScript(body)
			resp.Body = io.NopCloser(bytes.NewReader(newBody))
			resp.ContentLength = int64(len(newBody))
			resp.Header.Set("Content-Length", strconv.Itoa(len(newBody)))
			return nil
		},
	}
	return rp
}

// ============ 列表查询缓存（queryScenes 结果，内存 TTL） ============

type listEntry struct {
	data    []byte
	savedAt time.Time
}

// listCache 缓存场景列表 GraphQL 查询结果：key=md5(请求 body)，
// 排序/筛选/页码已编码在 body 中，天然区分；TTL 过期自动失效。
type listCache struct {
	mu        sync.Mutex
	items     map[string]*listEntry
	ttl       time.Duration
	maxBytes  int64
	totalBytes int64
}

func newListCache(ttl time.Duration, maxBytes int64) *listCache {
	return &listCache{items: make(map[string]*listEntry), ttl: ttl, maxBytes: maxBytes}
}

func (lc *listCache) get(key string) ([]byte, bool) {
	lc.mu.Lock()
	defer lc.mu.Unlock()
	e, ok := lc.items[key]
	if !ok {
		return nil, false
	}
	if time.Since(e.savedAt) > lc.ttl {
		delete(lc.items, key)
		lc.totalBytes -= int64(len(e.data))
		return nil, false
	}
	return e.data, true
}

func (lc *listCache) put(key string, data []byte) {
	lc.mu.Lock()
	defer lc.mu.Unlock()
	if old, ok := lc.items[key]; ok {
		lc.totalBytes -= int64(len(old.data))
	}
	lc.items[key] = &listEntry{data: data, savedAt: time.Now()}
	lc.totalBytes += int64(len(data))
	// 超限：清最旧 25%
	for lc.totalBytes > lc.maxBytes && len(lc.items) > 4 {
		var oldestKey string
		var oldest time.Time
		for k, v := range lc.items {
			if oldestKey == "" || v.savedAt.Before(oldest) {
				oldestKey, oldest = k, v.savedAt
			}
		}
		lc.totalBytes -= int64(len(lc.items[oldestKey].data))
		delete(lc.items, oldestKey)
	}
}

// 可缓存条件：POST 的 queryScenes 列表查询，且非 mutation
func isCacheableListQuery(body []byte) bool {
	var req struct {
		Query string `json:"query"`
	}
	if err := json.Unmarshal(body, &req); err != nil || req.Query == "" {
		return false
	}
	if strings.Contains(strings.ToLower(req.Query), "mutation") {
		return false
	}
	return strings.Contains(req.Query, "queryScenes")
}

// 可缓存响应：无 GraphQL errors
func isCacheableListResponse(data []byte) bool {
	var resp struct {
		Errors []any `json:"errors"`
	}
	if err := json.Unmarshal(data, &resp); err != nil {
		return false
	}
	return len(resp.Errors) == 0
}

// forwardGraphQL 直接转发上游（与 graphQLReverseProxy 等价，但可读回响应体）
func (p *Proxy) forwardGraphQL(r *http.Request, body []byte) ([]byte, error) {
	target := p.cfg.Site.Target
	req, err := http.NewRequestWithContext(r.Context(), "POST", strings.TrimRight(target, "/")+"/graphql", bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	if c := r.Header.Get("Cookie"); c != "" {
		req.Header.Set("Cookie", c)
	} else {
		req.Header.Set("Cookie", p.cfg.Site.Cookie)
	}
	if k := r.Header.Get("ApiKey"); k != "" {
		req.Header.Set("ApiKey", k)
	}
	req.Header.Set("Origin", target+"/")
	req.Header.Set("Referer", target+"/")
	req.Header.Set("User-Agent", "Mozilla/5.0 (stashdb-proxy)")
	req.Header.Del("Accept-Encoding")
	client := &http.Client{Timeout: 60 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return nil, fmt.Errorf("upstream graphql status %d", resp.StatusCode)
	}
	return io.ReadAll(resp.Body)
}

// ============ GraphQL 转发 ============

func (p *Proxy) graphQLHandler() http.Handler {
	// 可缓存的列表查询走缓存层，其余保持原 ReverseProxy
	rp := &httputil.ReverseProxy{
		Director: func(req *http.Request) {
			target := p.cfg.Site.Target
			u, _ := url.Parse(target)
			req.URL.Scheme = u.Scheme
			req.URL.Host = u.Host
			req.Host = u.Host
			req.Header.Set("Origin", target+"/")
			req.Header.Set("Referer", target+"/")
			if req.Header.Get("Cookie") == "" {
				req.Header.Set("Cookie", p.cfg.Site.Cookie)
			}
			req.Header.Del("Accept-Encoding")
		},
	}
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			rp.ServeHTTP(w, r)
			return
		}
		body, err := io.ReadAll(io.LimitReader(r.Body, 1<<20))
		if err != nil {
			http.Error(w, "bad body", http.StatusBadRequest)
			return
		}
		if !isCacheableListQuery(body) {
			r.Body = io.NopCloser(bytes.NewReader(body))
			rp.ServeHTTP(w, r)
			return
		}
		key := fmt.Sprintf("%x", md5.Sum(body))
		if data, ok := p.listCache.get(key); ok {
			w.Header().Set("Content-Type", "application/json; charset=utf-8")
			w.Header().Set("X-Cache-Status", "HIT")
			w.Write(data)
			return
		}
		data, err := p.forwardGraphQL(r, body)
		if err != nil {
			http.Error(w, "upstream graphql failed", http.StatusBadGateway)
			return
		}
		if isCacheableListResponse(data) {
			p.listCache.put(key, data)
		}
		w.Header().Set("Content-Type", "application/json; charset=utf-8")
		w.Header().Set("X-Cache-Status", "MISS")
		w.Write(data)
	})
}

// ============ 本地 Stash 标签索引（一次性全量拉取 + 内存查询） ============

type tagEntry struct {
	ID      string
	Name    string
	Aliases []string
}

// tagIndex 保存本地 Stash 全量标签（含别名），提供 O(1) 名字/别名 → 主名 解析。
type tagIndex struct {
	cfg *Config

	mu      sync.RWMutex
	byName  map[string]tagEntry // strings.ToLower(name) → entry
	byAlias map[string]tagEntry // strings.ToLower(alias) → entry（值存主 entry）
	synced  bool
	lastAt  time.Time

	refreshMu sync.Mutex // 单飞：并发首查只刷新一次
}

func newTagIndex(cfg *Config) *tagIndex {
	return &tagIndex{
		cfg:     cfg,
		byName:  make(map[string]tagEntry),
		byAlias: make(map[string]tagEntry),
	}
}

// ensureFresh 懒加载 + TTL：首次调用或超过 refreshMinutes 时全量拉取重建索引。
func (ti *tagIndex) ensureFresh() error {
	ti.mu.RLock()
	fresh := ti.synced && time.Since(ti.lastAt) < time.Duration(ti.refreshMinutes())*time.Minute
	ti.mu.RUnlock()
	if fresh {
		return nil
	}

	ti.refreshMu.Lock()
	defer ti.refreshMu.Unlock()

	// 单飞复查
	ti.mu.RLock()
	fresh = ti.synced && time.Since(ti.lastAt) < time.Duration(ti.refreshMinutes())*time.Minute
	ti.mu.RUnlock()
	if fresh {
		return nil
	}
	return ti.syncAll()
}

func (ti *tagIndex) refreshMinutes() int {
	if ti.cfg.LocalStash.RefreshMinutes <= 0 {
		return 60
	}
	return ti.cfg.LocalStash.RefreshMinutes
}

// syncAll 一次性拉取本地 Stash 全部标签（per_page: -1）并重建索引。
func (ti *tagIndex) syncAll() error {
	const query = `{"query":"{ findTags(filter: { per_page: -1 }) { tags { id name aliases } } }"}`
	req, err := http.NewRequest("POST", ti.cfg.LocalStash.GraphQL, bytes.NewReader([]byte(query)))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	client := &http.Client{Timeout: 60 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return fmt.Errorf("local stash %s: status %d", ti.cfg.LocalStash.GraphQL, resp.StatusCode)
	}
	var payload struct {
		Data struct {
			FindTags struct {
				Tags []struct {
					ID      string   `json:"id"`
					Name    string   `json:"name"`
					Aliases []string `json:"aliases"`
				} `json:"tags"`
			} `json:"findTags"`
		} `json:"data"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&payload); err != nil {
		return err
	}

	byName := make(map[string]tagEntry, len(payload.Data.FindTags.Tags))
	byAlias := make(map[string]tagEntry)
	for _, t := range payload.Data.FindTags.Tags {
		if t.Name == "" {
			continue
		}
		e := tagEntry{ID: t.ID, Name: t.Name, Aliases: t.Aliases}
		byName[strings.ToLower(strings.TrimSpace(t.Name))] = e
		for _, a := range t.Aliases {
			key := strings.ToLower(strings.TrimSpace(a))
			if key == "" {
				continue
			}
			if _, dup := byAlias[key]; !dup {
				byAlias[key] = e
			}
		}
	}

	ti.mu.Lock()
	ti.byName = byName
	ti.byAlias = byAlias
	ti.synced = true
	ti.lastAt = time.Now()
	ti.mu.Unlock()
	log.Printf("[local-stash] 标签索引已刷新: %d 主名 / %d 别名 (来源 %s)",
		len(byName), len(byAlias), ti.cfg.LocalStash.GraphQL)
	return nil
}

// resolve 解析单个页面标签：返回本地主名、是否别名、是否在本地库找到。
func (ti *tagIndex) resolve(name string) (primary string, isAlias bool, found bool) {
	key := strings.ToLower(strings.TrimSpace(name))
	if key == "" {
		return "", false, false
	}
	ti.mu.RLock()
	defer ti.mu.RUnlock()
	if e, ok := ti.byName[key]; ok {
		return e.Name, false, true
	}
	if e, ok := ti.byAlias[key]; ok {
		return e.Name, true, true
	}
	return "", false, false
}

// resolveTagsHandler POST /api/resolve-tags
// body:  {"tags": ["Blowjob", "Creampie", ...]}
// resp:  {"results": [{"name": "Blowjob", "primary": "口交", "isAlias": true, "found": true}, ...]}
// 未配置 localStash 时返回 200 + {"enabled": false}，前端静默跳过。
func (p *Proxy) resolveTagsHandler() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if p.cfg.LocalStash.GraphQL == "" {
			writeJSON(w, map[string]any{"enabled": false})
			return
		}
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		var body struct {
			Tags []string `json:"tags"`
		}
		if err := json.NewDecoder(io.LimitReader(r.Body, 1<<20)).Decode(&body); err != nil {
			http.Error(w, "bad json", http.StatusBadRequest)
			return
		}
		if len(body.Tags) == 0 {
			writeJSON(w, map[string]any{"results": []any{}})
			return
		}
		if err := p.tagIdx.ensureFresh(); err != nil {
			log.Printf("[local-stash] 索引刷新失败: %v", err)
			writeJSON(w, map[string]any{"error": "tag index unavailable"})
			return
		}
		seen := make(map[string]bool, len(body.Tags))
		results := make([]map[string]any, 0, len(body.Tags))
		for _, t := range body.Tags {
			norm := strings.TrimSpace(t)
			if norm == "" || seen[norm] {
				continue
			}
			seen[norm] = true
			primary, isAlias, found := p.tagIdx.resolve(norm)
			results = append(results, map[string]any{
				"name":    norm,
				"primary": primary,
				"isAlias": isAlias,
				"found":   found,
			})
		}
		writeJSON(w, map[string]any{"results": results})
	}
}

func writeJSON(w http.ResponseWriter, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	_ = json.NewEncoder(w).Encode(v)
}

// ============ 本地 Stash 场景索引（stashdb 场景 ID → 本地场景 ID） ============

// sceneIndex 一次性拉取本地库全部场景的 stash_id（per_page: -1），
// 只索引 stashdb.org 的条目，提供 O(1) stashdb 场景 ID → 本地场景 ID 解析。
type sceneIndex struct {
	cfg *Config

	mu           sync.RWMutex
	byStashdbID  map[string]string // stashdb 场景 ID → 本地场景 ID
	synced       bool
	lastAt       time.Time
	refreshMu    sync.Mutex
}

func newSceneIndex(cfg *Config) *sceneIndex {
	return &sceneIndex{cfg: cfg, byStashdbID: make(map[string]string)}
}

func (si *sceneIndex) ensureFresh() error {
	si.mu.RLock()
	fresh := si.synced && time.Since(si.lastAt) < time.Duration(si.refreshMinutes())*time.Minute
	si.mu.RUnlock()
	if fresh {
		return nil
	}
	si.refreshMu.Lock()
	defer si.refreshMu.Unlock()
	si.mu.RLock()
	fresh = si.synced && time.Since(si.lastAt) < time.Duration(si.refreshMinutes())*time.Minute
	si.mu.RUnlock()
	if fresh {
		return nil
	}
	return si.syncAll()
}

func (si *sceneIndex) refreshMinutes() int {
	if si.cfg.LocalStash.RefreshMinutes <= 0 {
		return 60
	}
	return si.cfg.LocalStash.RefreshMinutes
}

// syncAll 拉取本地库全部场景的 id + stash_ids，建立 stashdb.org → 本地 ID 映射。
func (si *sceneIndex) syncAll() error {
	const query = `{"query":"{ findScenes(scene_filter: {}, filter: { per_page: -1 }) { scenes { id stash_ids { endpoint stash_id } } } }"}`
	req, err := http.NewRequest("POST", si.cfg.LocalStash.GraphQL, bytes.NewReader([]byte(query)))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	client := &http.Client{Timeout: 120 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != 200 {
		return fmt.Errorf("local stash %s: status %d", si.cfg.LocalStash.GraphQL, resp.StatusCode)
	}
	var payload struct {
		Data struct {
			FindScenes struct {
				Scenes []struct {
					ID       string `json:"id"`
					StashIDs []struct {
						Endpoint string `json:"endpoint"`
						StashID  string `json:"stash_id"`
					} `json:"stash_ids"`
				} `json:"scenes"`
			} `json:"findScenes"`
		} `json:"data"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&payload); err != nil {
		return err
	}

	byID := make(map[string]string, 8000)
	for _, s := range payload.Data.FindScenes.Scenes {
		for _, sid := range s.StashIDs {
			if strings.Contains(sid.Endpoint, "stashdb.org") && sid.StashID != "" {
				if _, dup := byID[sid.StashID]; !dup {
					byID[sid.StashID] = s.ID
				}
			}
		}
	}

	si.mu.Lock()
	si.byStashdbID = byID
	si.synced = true
	si.lastAt = time.Now()
	si.mu.Unlock()
	log.Printf("[local-stash] 场景索引已刷新: %d 个 stashdb 场景映射 (来源 %s)",
		len(byID), si.cfg.LocalStash.GraphQL)
	return nil
}

// resolve 解析 stashdb 场景 ID → 本地场景 ID。
func (si *sceneIndex) resolve(stashdbID string) (localID string, found bool) {
	si.mu.RLock()
	defer si.mu.RUnlock()
	id, ok := si.byStashdbID[stashdbID]
	return id, ok
}

// resolveScenesHandler POST /api/resolve-scenes
// body:  {"ids": ["stashdb-scene-uuid", ...]}
// resp:  {"results": [{"id": "...", "localId": "...", "found": true, "url": "https://.../scenes/<localId>"}, ...]}
// 未配置 localStash 时返回 200 + {"enabled": false}，前端静默跳过。
func (p *Proxy) resolveScenesHandler() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if p.cfg.LocalStash.GraphQL == "" {
			writeJSON(w, map[string]any{"enabled": false})
			return
		}
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		var body struct {
			IDs []string `json:"ids"`
		}
		if err := json.NewDecoder(io.LimitReader(r.Body, 1<<20)).Decode(&body); err != nil {
			http.Error(w, "bad json", http.StatusBadRequest)
			return
		}
		if len(body.IDs) == 0 {
			writeJSON(w, map[string]any{"results": []any{}})
			return
		}
		if err := p.sceneIdx.ensureFresh(); err != nil {
			log.Printf("[local-stash] 场景索引刷新失败: %v", err)
			writeJSON(w, map[string]any{"error": "scene index unavailable"})
			return
		}
		seen := make(map[string]bool, len(body.IDs))
		results := make([]map[string]any, 0, len(body.IDs))
		for _, id := range body.IDs {
			id = strings.TrimSpace(id)
			if id == "" || seen[id] {
				continue
			}
			seen[id] = true
			localID, found := p.sceneIdx.resolve(id)
			res := map[string]any{"id": id, "found": found}
			if found {
				res["localId"] = localID
				if p.cfg.LocalStash.PlayerURL != "" {
					res["url"] = strings.TrimRight(p.cfg.LocalStash.PlayerURL, "/") + "/scenes/" + localID
				}
			}
			results = append(results, res)
		}
		writeJSON(w, map[string]any{"results": results})
	}
}

// ============ 主程序 ============

type Proxy struct {
	cfg       *Config
	cache     *diskCache
	tagIdx    *tagIndex
	sceneIdx  *sceneIndex
	listCache *listCache
}

func main() {
	configPath := os.Getenv("CONFIG_PATH")
	if configPath == "" {
		configPath = "./config.json"
	}
	cfg, err := loadConfig(configPath)
	if err != nil {
		log.Fatalf("load config: %v", err)
	}
	if len(enhancedJS) == 0 {
		log.Fatal("enhanced.js is empty — run build.sh first")
	}

	cache := newDiskCache(
		filepath.Join(cfg.CacheDir, "images"),
		time.Duration(cfg.ImageCache.TTLDays)*24*time.Hour,
		int64(cfg.ImageCache.MaxSizeGB)*1024*1024*1024,
	)
	lcTTL := time.Duration(cfg.ListCache.TTLSeconds) * time.Second
	if lcTTL <= 0 {
		lcTTL = 24 * time.Hour // 站点更新不频繁，默认 24 小时
	}
	lcMax := int64(cfg.ListCache.MaxMB) * 1024 * 1024
	if lcMax <= 0 {
		lcMax = 500 * 1024 * 1024 // 默认 500MB
	}
	p := &Proxy{cfg: cfg, cache: cache, tagIdx: newTagIndex(cfg), sceneIdx: newSceneIndex(cfg), listCache: newListCache(lcTTL, lcMax)}
	go cache.enforceLoop()

	flagCache := newDiskCache(filepath.Join(cfg.CacheDir, "flag"), 30*24*time.Hour, 512*1024*1024)
	iconCache := newDiskCache(filepath.Join(cfg.CacheDir, "favicon"), 7*24*time.Hour, 512*1024*1024)

	flagUp, _ := url.Parse("https://flagcdn.com")
	iconUp, _ := url.Parse("https://icons.duckduckgo.com")

	mux := http.NewServeMux()
	mux.HandleFunc("/enhanced.js", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/javascript; charset=utf-8")
		w.Header().Set("Cache-Control", "no-cache") // 迭代期禁止缓存，改脚本立即生效
		w.Write(enhancedJS)
	})
	upClient := &http.Client{Timeout: 60 * time.Second}
	mux.Handle("/images/", &proxyHandler{cfg: cfg, cache: cache, upstream: mustParse(cfg.Site.Target), client: upClient})
	mux.Handle("/flag/", &proxyHandler{cfg: cfg, cache: flagCache, upstream: flagUp, client: upClient,
		rewrite: func(path string) (string, string) {
			return strings.TrimPrefix(path, "/flag"), ""
		}})
	iconClient := upClient
	if cfg.FaviconProxy != "" {
		if pu, err := url.Parse(cfg.FaviconProxy); err == nil {
			iconClient = &http.Client{Timeout: 60 * time.Second,
				Transport: &http.Transport{Proxy: http.ProxyURL(pu)}}
			log.Printf("favicon proxy: %s", cfg.FaviconProxy)
		}
	}
	mux.Handle("/favicon/", &proxyHandler{cfg: cfg, cache: iconCache, upstream: iconUp, client: iconClient,
		rewrite: func(path string) (string, string) {
			domain := strings.TrimPrefix(path, "/favicon/")
			return "/ip3/" + domain + ".ico", ""
		}})
	mux.Handle("/graphql", p.graphQLHandler())
	mux.HandleFunc("/api/resolve-tags", p.resolveTagsHandler())
	mux.HandleFunc("/api/resolve-scenes", p.resolveScenesHandler())
	mux.Handle("/", p.reverseHandler())

	log.Printf("stashdb-proxy listening on %s → %s (cache %s, %dGB/%dd)",
		cfg.Listen, cfg.Site.Target, cfg.CacheDir, cfg.ImageCache.MaxSizeGB, cfg.ImageCache.TTLDays)
	if err := http.ListenAndServe(cfg.Listen, mux); err != nil {
		log.Fatal(err)
	}
}

func mustParse(s string) *url.URL {
	u, err := url.Parse(s)
	if err != nil {
		log.Fatalf("bad url %s: %v", s, err)
	}
	return u
}
