#!/bin/sh
# 合并 web/ 模块 → enhanced.js（依赖顺序，仿 build.ps1）
set -e
cd "$(dirname "$0")"
OUT=enhanced.js
FILES="config.js utils.js api.js page-parser.js card-renderer.js pagination.js sorter.js toolbar.js styles.js main.js hanhua.js"

{
  echo '(function () {'
  echo "    'use strict';"
  echo ''
  for f in $FILES; do
    echo "// ===== $f ====="
    # 只删 CRLF（0x0D 不出现在中文 UTF-8 里，安全）；BOM 已从源文件删除
    sed 's/^/    /' "web/$f" | tr -d '\r'
    echo ''
  done
  echo '})();'
} > "$OUT.tmp"
# 幂等：内容没变不覆盖，避免触发 air 死循环
if cmp -s "$OUT.tmp" "$OUT"; then
  rm -f "$OUT.tmp"
  echo "built: $OUT (unchanged, $(wc -c < "$OUT") bytes)"
else
  mv -f "$OUT.tmp" "$OUT"
  echo "built: $OUT (updated, $(wc -c < "$OUT") bytes)"
fi
