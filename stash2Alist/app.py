"""stash2Alist 鏍稿績搴旂敤 - Starlette 璺敱涓庨€忔槑浠ｇ悊"""
import asyncio
import logging
import re
import time

import httpx
import websockets
import yaml
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response, JSONResponse, StreamingResponse
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket as StarletteWebSocket

from .stash.client import StashClient
from .alist.client import AlistClient
from .path_mapper import PathMapper

logger = logging.getLogger("stash2alist.app")

HOP_BY_HOP_HEADERS = {
    "host", "connection", "keep-alive", "proxy-authenticate",
    "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade",
}

DROP_RESPONSE_HEADERS = HOP_BY_HOP_HEADERS | {
    "content-length", "content-encoding",
    "content-security-policy", "content-security-policy-report-only",
}

STREAM_PATH_RE = re.compile(r"^/scene/(\d+)/(stream|download)(\.\w+)?$")


def _filename(path: str) -> str:
    """浠庤矾寰勪腑鎻愬彇鏂囦欢鍚?""
    return path.rsplit("/", 1)[-1] if "/" in path else path


class Stash2AlistApp:

    def __init__(self, config: dict, debug: bool = False):
        self.config = config
        self.debug = debug
        stash_cfg = config.get("stash", {})
        alist_cfg = config.get("alist", {})
        cache_cfg = config.get("cache", {})

        self.stash_client = StashClient(
            stash_url=stash_cfg.get("url", "http://localhost:9999"),
            api_key=stash_cfg.get("api_key", ""),
            cache_ttl=cache_cfg.get("stash", {}).get("ttl", 3600),
            cache_maxsize=cache_cfg.get("max_size", 1000),
        )
        req_cfg = alist_cfg.get("request", {})
        self.alist_client = AlistClient(
            alist_url=alist_cfg.get("url", "http://localhost:5244"),
            token=alist_cfg.get("token", ""),
            cache_maxsize=cache_cfg.get("max_size", 1000),
            timeout=req_cfg.get("timeout", 1),
            retries=req_cfg.get("retries", 3),
            retry_delay=req_cfg.get("retry_delay", 0.5),
        )
        self.path_mapper = PathMapper(mappings=config.get("path_mappings", []))
        self.stash_origin = stash_cfg.get("url", "http://localhost:9999").rstrip("/")
        self.stash_ws_origin = self.stash_origin.replace("http://", "ws://").replace("https://", "wss://")
        # Build list of Stash URL variants for rewriting (e.g. both 192.168.x.x:9999 and localhost:9999)
        self._stash_urls_to_rewrite = {self.stash_origin}
        # Add localhost variant if different from configured origin
        if "localhost" not in self.stash_origin:
            from urllib.parse import urlparse
            parsed = urlparse(self.stash_origin)
            localhost_url = f"{parsed.scheme}://localhost:{parsed.port}" if parsed.port else f"{parsed.scheme}://localhost"
            self._stash_urls_to_rewrite.add(localhost_url)
        # Also add 127.0.0.1 variant
        if "127.0.0.1" not in self.stash_origin:
            from urllib.parse import urlparse
            parsed = urlparse(self.stash_origin)
            loopback_url = f"{parsed.scheme}://127.0.0.1:{parsed.port}" if parsed.port else f"{parsed.scheme}://127.0.0.1"
            self._stash_urls_to_rewrite.add(loopback_url)
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=False,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
            headers={"Accept-Encoding": "identity"},
        )

        if self.debug:
            logger.info("=" * 50)
            logger.info("璋冭瘯妯″紡宸插惎鐢?)
            logger.info(f"Stash: {self.stash_origin}")
            logger.info(f"Alist: {alist_cfg.get('url', 'N/A')}")
            logger.info(f"璺緞鏄犲皠 ({len(config.get('path_mappings', []))} 鏉?:")
            for m in config.get("path_mappings", []):
                logger.info(f"  {m.get('local')}")
                logger.info(f"  -> {m.get('alist')}")
            logger.info(f"Stash 缓存 TTL: {cache_cfg.get('stash', {}).get('ttl', 3600)}s（固定）")
            logger.info(f"Alist 直链缓存: 动态 TTL（仅缓存含 t 参数的直链）")
            logger.info("=" * 50)

    # 鈹€鈹€ 璺敱鍏ュ彛 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

    async def handle_request(self, request: Request):
        path = request.url.path
        method = request.method
        client_ip = request.client.host if request.client else "unknown"
        query = str(request.url.query) if request.url.query else ""

        stream_match = STREAM_PATH_RE.match(path)
        if stream_match:
            return await self._handle_stream(request, int(stream_match.group(1)), client_ip)

        is_gql = "/graphql" in path and method == "POST"
        tag = "GQL" if is_gql else method
        qs = f"?{query[:60]}" if query else ""
        self._debug_log(f"> [{tag}] {path}{qs}", client_ip=client_ip)
        return await self._proxy_to_stash(request, client_ip, is_gql)

    # 鈹€鈹€ 娴佸獟浣撻噸瀹氬悜 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

    async def _handle_stream(self, request: Request, scene_id: int, client_ip: str) -> Response:
        t_start = time.time()
        debug_info = {}
        self._debug_log(f">> 娴?#{scene_id}", client_ip=client_ip)

        # 1. 鏌ヨ Stash 鑾峰彇鏈湴璺緞
        t1 = time.time()
        local_path = await self.stash_client.get_file_path(scene_id)
        t1_ms = (time.time() - t1) * 1000
        debug_info["scene_id"] = str(scene_id)

        if not local_path:
            self._debug_log(f"  鉁?鍦烘櫙鏈壘鍒?, client_ip=client_ip)
            return JSONResponse({"error": f"鍦烘櫙 {scene_id} 鏈壘鍒?}, status_code=404,
                                headers=self._debug_headers(debug_info))
        self._debug_log(f"  Scene file: {local_path} [{t1_ms:.0f}ms]", client_ip=client_ip)

        # 2. 鏄犲皠涓?Alist 璺緞
        t2 = time.time()
        alist_path = self.path_mapper.to_alist_path(local_path)
        t2_ms = (time.time() - t2) * 1000
        debug_info["local_path"] = local_path
        debug_info["alist_path"] = alist_path if alist_path else "N/A"
        debug_info["path_mapping_ms"] = f"{t2_ms:.0f}"

        if not alist_path:
            self._debug_log(f"  鉁?璺緞鏈尮閰? {local_path}", client_ip=client_ip)
            return JSONResponse({"error": f"璺緞鏄犲皠澶辫触: {local_path}"}, status_code=404,
                                headers=self._debug_headers(debug_info))
        self._debug_log(f"  -> Alist: {alist_path} [{t2_ms:.0f}ms]", client_ip=client_ip)

        # 3. 鑾峰彇鐩撮摼
        t3 = time.time()
        client_ua = request.headers.get("user-agent", "")
        direct_url = await self.alist_client.get_direct_link(alist_path, client_ua=client_ua)
        t3_ms = (time.time() - t3) * 1000
        debug_info["direct_url"] = direct_url if direct_url else "N/A"
        debug_info["direct_link_ms"] = f"{t3_ms:.0f}"
        if direct_url:
            debug_info["direct_url_short"] = direct_url

        if not direct_url:
            self._debug_log(f"  鉁?鐩撮摼鑾峰彇澶辫触", client_ip=client_ip)
            return JSONResponse({"error": "鑾峰彇鐩撮摼澶辫触"}, status_code=502,
                                headers=self._debug_headers(debug_info))

        t_total = (time.time() - t_start) * 1000
        debug_info["total_ms"] = f"{t_total:.0f}"
        self._debug_log(f"  OK [{t_total:.0f}ms]", client_ip=client_ip)

        # 302 閲嶅畾鍚戝埌 Alist 鐩撮摼锛屼繚鐣欏垵濮嬭姹傚弬鏁?
        redirect_url = direct_url
        original_qs = str(request.url.query) if request.url.query else ""
        if original_qs:
            from urllib.parse import urlparse, urlencode, parse_qs
            parsed = urlparse(direct_url)
            existing = parse_qs(parsed.query)
            merged = {}
            for k, v in existing.items():
                merged[k] = v[-1] if isinstance(v, list) else v
            for k, v in parse_qs(original_qs).items():
                if k not in merged:
                    merged[k] = v[-1] if isinstance(v, list) else v
            redirect_url = f"{direct_url.split('?')[0]}?{urlencode(merged)}"

        resp = RedirectResponse(url=redirect_url, status_code=302)
        # 娣诲姞 Referrer-Policy 澶达紝闃叉澶栭儴 CDN 鍥?Referer 鎷掔粷璇锋眰
        resp.headers["Referrer-Policy"] = "no-referrer"
        # 娣诲姞璋冭瘯澶?
        if self.debug:
            for k, v in self._debug_headers(debug_info).items():
                resp.headers[k] = v
        return resp

    # 鈹€鈹€ 閫忔槑浠ｇ悊 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

    async def _proxy_to_stash(self, request: Request, client_ip: str, is_graphql: bool = False) -> Response:
        proxy_path = str(request.url.path)
        if request.url.query:
            proxy_path += "?" + str(request.url.query)
        target_url = self.stash_origin + proxy_path

        forward_headers = {}
        for key, value in request.headers.items():
            if key.lower() not in HOP_BY_HOP_HEADERS:
                forward_headers[key] = value
        forward_headers.pop("host", None)

        try:
            body = await request.body()
        except Exception:
            body = b""

        t_proxy = time.time()

        # GraphQL needs buffered response for URL rewriting
        if is_graphql:
            return await self._proxy_graphql(
                request, target_url, forward_headers, body, client_ip, t_proxy
            )

        # Non-GraphQL: use streaming to avoid memory buffering
        return await self._proxy_stream(
            request, target_url, forward_headers, body, client_ip, t_proxy
        )

    async def _proxy_stream(self, request, target_url, forward_headers,
                             body, client_ip, t_proxy):
        """Stream proxy - streams binary responses, buffers text for URL rewriting"""
        TEXT_TYPES = ("text/", "application/json", "application/javascript",
                      "application/x-javascript", "application/ecmascript",
                      "application/xml", "application/ld+json")
        try:
            req = self.http_client.build_request(
                method=request.method, url=target_url,
                headers=forward_headers, content=body if body else None,
            )
            resp = await self.http_client.send(req, stream=True)
        except httpx.RequestError as e:
            t_elapsed = (time.time() - t_proxy) * 1000
            self._debug_log(f"  = 502 [{t_elapsed:.0f}ms (stream)]", client_ip=client_ip)
            return JSONResponse({"error": f"Proxy failed: {e}"}, status_code=502)

        resp_headers = {}
        content_type = ""
        for key, value in resp.headers.items():
            if key.lower() not in DROP_RESPONSE_HEADERS:
                resp_headers[key] = value
            if key.lower() == "content-type":
                content_type = value.lower()

        t_elapsed = (time.time() - t_proxy) * 1000
        if self.debug:
            resp_headers["X-Stash2Alist-Timing-Ms"] = f"{t_elapsed:.0f}"

        # Text content may contain Stash URLs that need rewriting to avoid CORS errors
        is_text = content_type.startswith(TEXT_TYPES) if content_type else False
        if is_text and self._stash_urls_to_rewrite:
            # Buffer text response, rewrite URLs, then serve
            body_bytes = await resp.aread()
            await resp.aclose()
            self._debug_log(f"  = {resp.status_code} [{t_elapsed:.0f}ms (text)]", client_ip=client_ip)
            try:
                body_str = body_bytes.decode("utf-8", "replace")
                from urllib.parse import urlparse
                stash_parsed = urlparse(self.stash_origin)
                proxy_url = f"{request.url.scheme}://{request.headers.get('host', 'localhost:8000')}"
                proxy_parsed = urlparse(proxy_url)
                proxy_hostport = f"{proxy_parsed.hostname}:{proxy_parsed.port or 80}"
                # 1) Rewrite full Stash URLs
                for stash_url in self._stash_urls_to_rewrite:
                    if stash_url in body_str:
                        body_str = body_str.replace(stash_url, proxy_url)
                # 2) Rewrite "localhost:port" host:port pattern
                localhost_pattern = f"localhost:{stash_parsed.port}" if stash_parsed.port else "localhost"
                if localhost_pattern in body_str:
                    body_str = body_str.replace(localhost_pattern, proxy_hostport)
                # 3) Rewrite individual host/port config values
                if "host: '" in body_str:
                    body_str = body_str.replace("host: 'localhost'", "host: '" + proxy_parsed.hostname + "'")
                    body_str = body_str.replace('host: "localhost"', 'host: "' + proxy_parsed.hostname + '"')
                if stash_parsed.port:
                    port_str = str(stash_parsed.port)
                    body_str = body_str.replace("port: " + port_str + ",", "port: " + str(proxy_parsed.port or 8000) + ",")
                # 4) Sub-filter: 绉婚櫎 ScenePlayer JS 涓殑 crossorigin="anonymous"
                #    浣挎祻瑙堝櫒涓嶄細瀵瑰閮?CDN 鐩撮摼锛堝 115锛夊彂璧?CORS 璇锋眰
                body_str = re.sub(
                    r"\.setAttribute\(\s*[\"']crossorigin[\"']\s*,\s*[\"']anonymous[\"']\s*\)",
                    '.removeAttribute("crossorigin")',
                    body_str,
                )
                body_bytes = body_str.encode("utf-8")
            except Exception:
                pass
            return Response(content=body_bytes, status_code=resp.status_code, headers=resp_headers)
        else:
            self._debug_log(f"  = {resp.status_code} [{t_elapsed:.0f}ms (stream)]", client_ip=client_ip)
            async def _iter_content():
                try:
                    async for chunk in resp.aiter_bytes():
                        yield chunk
                finally:
                    await resp.aclose()
            return StreamingResponse(
                _iter_content(),
                status_code=resp.status_code,
                headers=resp_headers,
            )

    async def _proxy_graphql(self, request, target_url, forward_headers,
                              body, client_ip, t_proxy):
        """GraphQL proxy - buffer response for URL rewriting"""
        # GraphQL request log
        if self.debug and body:
            try:
                body_str = body.decode("utf-8", "replace")
                brief = body_str[:200].replace("\n", " ").replace("\r", "")
                self._debug_log(f"  >> {brief}", client_ip=client_ip)
            except Exception:
                pass

        try:
            resp = await self.http_client.request(
                method=request.method, url=target_url,
                headers=forward_headers, content=body if body else None,
            )
        except httpx.RequestError as e:
            t_elapsed = (time.time() - t_proxy) * 1000
            self._debug_log(f"  = 502 [{t_elapsed:.0f}ms (gql)]", client_ip=client_ip)
            return JSONResponse({"error": f"Proxy failed: {e}"}, status_code=502)

        content = resp.content
        try:
            proxy_url = f"{request.url.scheme}://{request.headers.get("host", "localhost:8000")}"
            from urllib.parse import urlparse
            stash_parsed = urlparse(self.stash_origin)
            proxy_parsed = urlparse(proxy_url)
            proxy_hostport = f"{proxy_parsed.hostname}:{proxy_parsed.port or 80}"
            resp_str = content.decode("utf-8")
            rewritten = False
            # 1) Rewrite full Stash URLs
            for stash_url in self._stash_urls_to_rewrite:
                if stash_url in resp_str:
                    resp_str = resp_str.replace(stash_url, proxy_url)
                    rewritten = True
            # 2) Rewrite "localhost:port" host:port pattern
            localhost_pattern = f"localhost:{stash_parsed.port}" if stash_parsed.port else "localhost"
            if localhost_pattern in resp_str:
                resp_str = resp_str.replace(localhost_pattern, proxy_hostport)
                rewritten = True
            # 3) Rewrite individual host/port config values
            if "host: '" in resp_str or 'host: "' in resp_str:
                resp_str = resp_str.replace("host: 'localhost'", f"host: '{proxy_parsed.hostname}'")
                resp_str = resp_str.replace('host: "localhost"', f'host: "{proxy_parsed.hostname}"')
                rewritten = True
            if stash_parsed.port:
                port_str = str(stash_parsed.port)
                resp_str = resp_str.replace(f"port: {port_str},", f"port: {proxy_parsed.port or 8000},")
            if rewritten:
                content = resp_str.encode("utf-8")
            if self.debug:
                brief = resp_str[:300].replace("\n", " ").replace("\r", "")
                self._debug_log(f"  -- {brief}", client_ip=client_ip)
        except Exception:
            pass

        t_elapsed = (time.time() - t_proxy) * 1000
        self._debug_log(f"  = {resp.status_code} [{t_elapsed:.0f}ms (gql)]", client_ip=client_ip)

        resp_headers = {}
        for key, value in resp.headers.items():
            if key.lower() not in DROP_RESPONSE_HEADERS:
                resp_headers[key] = value
        if self.debug:
            resp_headers["X-Stash2Alist-Timing-Ms"] = f"{t_elapsed:.0f}"

        return Response(content=content, status_code=resp.status_code, headers=resp_headers)
    # 鈹€鈹€ WebSocket 浠ｇ悊 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

    async def handle_websocket(self, websocket: StarletteWebSocket):
        try:
            raw_proto = websocket.headers.get("sec-websocket-protocol", "")
            sp = [p.strip() for p in raw_proto.split(",") if p.strip()]
            await websocket.accept(subprotocol=sp[0] if sp else None)
        except (Exception, asyncio.CancelledError):
            return

        try:
            path = websocket.url.path
            query = str(websocket.url.query) if websocket.url.query else ""
            target_ws_url = self.stash_ws_origin + path + ("?" + query if query else "")
            client_ip = websocket.client.host if websocket.client else "unknown"
        except (Exception, asyncio.CancelledError):
            return

        self._debug_log(f">> WS {path}", client_ip=client_ip)

        try:
            async with websockets.connect(target_ws_url, subprotocols=sp or None, open_timeout=5, close_timeout=3, ping_interval=None) as upstream_ws:
                self._debug_log(f"  鉁?宸茶繛鎺?, client_ip=client_ip)
                close_event = asyncio.Event()

                async def c2s():
                    try:
                        while not close_event.is_set():
                            data = await websocket.receive()
                            t = data.get("type")
                            if t == "websocket.receive":
                                txt = data.get("text")
                                b = data.get("bytes")
                                if txt is not None:
                                    await upstream_ws.send(txt)
                                elif b is not None:
                                    await upstream_ws.send(b)
                            elif t == "websocket.disconnect":
                                break
                    except (Exception, asyncio.CancelledError):
                        pass
                    finally:
                        close_event.set()

                async def s2c():
                    try:
                        while not close_event.is_set():
                            msg = await upstream_ws.recv()
                            if isinstance(msg, str):
                                await websocket.send_text(msg)
                            elif isinstance(msg, bytes):
                                await websocket.send_bytes(msg)
                    except (Exception, asyncio.CancelledError):
                        pass
                    finally:
                        close_event.set()

                done, pending = await asyncio.wait(
                    [asyncio.create_task(c2s()), asyncio.create_task(s2c())],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for t in pending:
                    t.cancel()
                    try:
                        await t
                    except (Exception, asyncio.CancelledError):
                        pass
                try:
                    await websocket.close(code=1000)
                except (Exception, asyncio.CancelledError):
                    pass
        except (Exception, asyncio.CancelledError):
            self._debug_log(f"  鉁?鏂紑", client_ip=client_ip)
        finally:
            try:
                await websocket.close(code=1001)
            except (Exception, asyncio.CancelledError):
                pass

    # 鈹€鈹€ 宸ュ叿鏂规硶 鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€

    def _debug_log(self, message: str, client_ip: str = "", extra: dict = None):
        if not self.debug:
            return
        prefix = f"[{client_ip}] " if client_ip else ""
        if extra:
            for k, v in extra.items():
                logger.debug(f"{prefix}{message}  {k}: {v}")
        else:
            logger.debug(f"{prefix}{message}")

    def _debug_headers(self, info: dict) -> dict:
        if not self.debug:
            return {}
        import urllib.parse
        headers = {}
        for key, value in info.items():
            hk = f"X-Stash2Alist-{key.replace('_', '-').title()}"
            val = str(value)
            try:
                val.encode("latin-1")
            except UnicodeEncodeError:
                val = urllib.parse.quote(val, safe="/ ,:-_.~")
            headers[hk] = val
        headers["X-Stash2Alist-Debug"] = "true"
        return headers

    async def handle_info(self, request: Request) -> JSONResponse:
        pm = [{"local": m["local"], "alist": m["alist"]} for m in self.config.get("path_mappings", [])]
        return JSONResponse({
            "service": "stash2Alist", "version": "0.1.0",
            "debug": self.debug,
            "stash_url": self.config.get("stash", {}).get("url", ""),
            "alist_url": self.config.get("alist", {}).get("url", ""),
            "path_mappings": pm,
            "cache_stash_ttl": self.config.get("cache", {}).get("stash", {}).get("ttl", 3600),
        })

    async def handle_debug(self, request: Request) -> JSONResponse:
        return JSONResponse({
            "debug": self.debug,
            "stash_url": self.stash_origin, "stash_ws_url": self.stash_ws_origin,
            "path_mappings": self.config.get("path_mappings", []),
        })


def create_app(config_path: str, debug: bool = False) -> Starlette:
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    ed = debug or config.get("server", {}).get("debug", False)
    al = Stash2AlistApp(config, debug=ed)

    async def catch_all(r: Request):
        return await al.handle_request(r)
    async def info_endpoint(r: Request):
        return await al.handle_info(r)
    async def debug_endpoint(r: Request):
        return await al.handle_debug(r)
    async def ws_handler(ws: StarletteWebSocket):
        await al.handle_websocket(ws)

    routes = [Route("/info", endpoint=info_endpoint, methods=["GET"])]
    if ed:
        routes.append(Route("/debug", endpoint=debug_endpoint, methods=["GET"]))
    routes.append(WebSocketRoute("/{path:path}", endpoint=ws_handler))
    routes.append(Route("/{path:path}", endpoint=catch_all,
                        methods=["GET", "HEAD", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]))
    return Starlette(debug=False, routes=routes)

