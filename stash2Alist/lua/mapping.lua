-- mapping.lua: 路径映射函数
local cjson = require "cjson"
local M = {}

-- 从 config/mappings.json 加载映射规则
local function load_mappings()
    local file, err = io.open("/usr/local/openresty/nginx/config/mappings.json", "r")
    if not file then
        ngx.log(ngx.ERR, "failed to open mappings.json: ", err)
        return { alist = {}, cd2 = {} }
    end
    local content = file:read("*a")
    file:close()
    local ok, data = pcall(cjson.decode, content)
    if not ok then
        ngx.log(ngx.ERR, "failed to parse mappings.json")
        return { alist = {}, cd2 = {} }
    end
    return data
end

-- 按最长前缀排序
local function sort_by_prefix_len(mappings)
    table.sort(mappings, function(a, b) return #a["local"] > #b["local"] end)
    return mappings
end

-- Alist 路径映射
function M.map_to_alist_path(local_path)
    local data = load_mappings()
    local rules = sort_by_prefix_len(data.alist or {})
    if string.sub(local_path, 1, 1) ~= "/" then
        local_path = "/" .. local_path
    end
    for _, m in ipairs(rules) do
        local lp = m["local"]
        if string.sub(local_path, 1, #lp) == lp then
            local remaining = string.sub(local_path, #lp + 1)
            if string.sub(remaining, 1, 1) ~= "/" then
                remaining = "/" .. remaining
            end
            return string.gsub(m["remote"], "/+$", "") .. remaining
        end
    end
    return nil
end

-- CloudDrive2 路径映射
function M.map_to_cd2_path(local_path)
    local data = load_mappings()
    local rules = sort_by_prefix_len(data.cd2 or {})
    if string.sub(local_path, 1, 1) ~= "/" then
        local_path = "/" .. local_path
    end
    for _, m in ipairs(rules) do
        local lp = m["local"]
        if string.sub(local_path, 1, #lp) == lp then
            local remaining = string.sub(local_path, #lp + 1)
            if string.sub(remaining, 1, 1) ~= "/" then
                remaining = "/" .. remaining
            end
            return string.gsub(m["remote"], "/+$", "") .. remaining
        end
    end
    return nil
end

-- CloudDrive2 下载链接构造
function M.build_cd2_download_url(cd2_path)
    local function encode_cd2_path(path)
        local result = ""
        local i = 1
        while i <= #path do
            local c = string.sub(path, i, i)
            if c == "/" then
                result = result .. "%2F"
            else
                result = result .. ngx.escape_uri(c)
            end
            i = i + 1
        end
        return result
    end
    local encoded = encode_cd2_path(cd2_path)
    return CD2_SERVER_URL .. "/static/http/" .. CD2_HOST .. ":" .. CD2_PORT .. "/False/" .. encoded
end

-- URL 编码路径（保留 /）
function M.encode_alist_path(path)
    local prefix = string.sub(path, 1, 1) == "/" and "/" or ""
    local segments = {}
    for segment in string.gmatch(path, "([^/]+)") do
        table.insert(segments, ngx.escape_uri(segment))
    end
    return prefix .. table.concat(segments, "/")
end

-- 动态 TTL 计算
function M.calc_dynamic_ttl(url, safety_margin)
    safety_margin = safety_margin or 300
    local t = string.match(url, "[?&]t=(%d+)")
    if t then
        local expire_ts = tonumber(t)
        local now = ngx.time()
        return math.max(1, expire_ts - now - safety_margin)
    end
    return 0
end

return M
