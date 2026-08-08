local cjson = require "cjson"
local mapping = require "mapping"

local id = tonumber(ngx.var.scene_id)
if not id then
    return ngx.exec("@stash_direct")
end

local mode_cache = ngx.shared.link_mode
local current_mode = mode_cache:get("current_mode") or DEFAULT_LINK_MODE

local ua = ngx.var.http_user_agent or ""
local ua_hash = ngx.md5(ua):sub(1, 8)

local api_key = ngx.var.arg_apikey or ""
if api_key == "" then
    api_key = ngx.var.http_apikey or STASH_API_KEY
end

local stash_headers = { ["Content-Type"] = "application/json" }
if api_key and api_key ~= "" then
    stash_headers["ApiKey"] = api_key
end

local stash_body = '{"query":"query{findScene(id:' .. id .. '){files{path}}}"}'
local stash_res = ngx.location.capture("/internal_stash_graphql", {
    method = ngx.HTTP_POST,
    body = stash_body,
    headers = stash_headers,
})

local path = nil
if stash_res and stash_res.status == 200 then
    local ok, data = pcall(cjson.decode, stash_res.body)
    if ok and data and data.data and data.data.findScene then
        local scene = data.data.findScene
        if scene.files and #scene.files > 0 and scene.files[1].path then
            path = scene.files[1].path
        end
    end
end

if not path then
    return ngx.exec("@stash_direct")
end

if current_mode == "cd2" then
    local cd2_path = mapping.map_to_cd2_path(path)
    if not cd2_path then
        ngx.log(ngx.WARN, "cd2 no mapping for path: ", path)
        return ngx.exec("@stash_direct")
    end
    local direct_url = mapping.build_cd2_download_url(cd2_path)
    ngx.log(ngx.INFO, "cd2 download: ", direct_url)
    return ngx.redirect(direct_url, 302)
else
    local cache = ngx.shared.alist_url_cache
    local alist_path = mapping.map_to_alist_path(path)
    if not alist_path then
        return ngx.exec("@stash_direct")
    end

    local cache_key = "alink:" .. alist_path .. "@" .. ua_hash
    local cached_url = cache:get(cache_key)
    if cached_url then
        ngx.log(ngx.INFO, "cache hit: ", cached_url)
        return ngx.redirect(cached_url, 302)
    end

    local encoded_path = mapping.encode_alist_path(alist_path)
    local alist_dl_path = string.gsub(encoded_path, "^/", "")
    local alist_headers = {}
    if ua and ua ~= "" then
        alist_headers["User-Agent"] = ua
    end

    local alist_res = ngx.location.capture(
        "/internal_alist_dl/d/" .. alist_dl_path,
        { method = ngx.HTTP_GET, headers = alist_headers }
    )

    if not alist_res then
        return ngx.exec("@stash_direct")
    end

    local direct_url = nil
    local ttl = CACHE_TTL

    if alist_res.status == 302 then
        direct_url = alist_res.header["Location"] or alist_res.header["location"]
        if direct_url then
            local dynamic_ttl = mapping.calc_dynamic_ttl(direct_url)
            if dynamic_ttl > 0 then
                ttl = dynamic_ttl
            end
            ngx.log(ngx.INFO, "alist 302: ", direct_url, " ttl=", ttl)
        end
    elseif alist_res.status == 200 then
        direct_url = ngx.var.scheme .. "://" .. (ngx.var.http_host or ngx.var.host) .. "/d/" .. string.gsub(encoded_path, "^/", "")
        ngx.log(ngx.INFO, "alist 200 direct: ", direct_url)
    else
        ngx.log(ngx.WARN, "alist /d/ returned ", alist_res.status, " for path: ", alist_path)
        return ngx.exec("@stash_direct")
    end

    if not direct_url then
        return ngx.exec("@stash_direct")
    end

    cache:set(cache_key, direct_url, ttl)
    return ngx.redirect(direct_url, 302)
end

