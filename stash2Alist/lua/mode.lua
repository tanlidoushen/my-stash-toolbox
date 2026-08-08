local cjson = require "cjson"
local cache = ngx.shared.link_mode
local method = ngx.req.get_method()

if method == "GET" then
    local mode = cache:get("current_mode") or DEFAULT_LINK_MODE
    ngx.status = 200
    ngx.header["Content-Type"] = "application/json"
    ngx.say(cjson.encode({ mode = mode, default = DEFAULT_LINK_MODE }))
    return
end

if method == "POST" then
    ngx.req.read_body()
    local body = ngx.req.get_body_data()
    if not body then
        ngx.status = 400
        ngx.header["Content-Type"] = "application/json"
        ngx.say(cjson.encode({ error = "missing body" }))
        return
    end

    local ok, data = pcall(cjson.decode, body)
    if not ok or not data or not data.mode then
        ngx.status = 400
        ngx.header["Content-Type"] = "application/json"
        ngx.say(cjson.encode({ error = "invalid body, need {\"mode\":\"alist\"|\"cd2\"}" }))
        return
    end

    local new_mode = data.mode
    if new_mode ~= "alist" and new_mode ~= "cd2" then
        ngx.status = 400
        ngx.header["Content-Type"] = "application/json"
        ngx.say(cjson.encode({ error = "mode must be 'alist' or 'cd2'" }))
        return
    end

    cache:set("current_mode", new_mode)
    ngx.log(ngx.INFO, "link mode switched to: ", new_mode)
    ngx.status = 200
    ngx.header["Content-Type"] = "application/json"
    ngx.say(cjson.encode({ mode = new_mode, message = "switched to " .. new_mode }))
    return
end

ngx.status = 405
ngx.header["Content-Type"] = "application/json"
ngx.say(cjson.encode({ error = "method not allowed" }))

