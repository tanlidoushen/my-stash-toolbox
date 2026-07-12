# Test Button Plugin 2.0

这是前后端分离版本：`test_button.js` 仅显示界面并调用 Stash 的本机 GraphQL；`test_button_backend.py` 在运行 Stash 的主机/容器内执行迅雷搜索、字幕下载、将字幕写入视频同目录，并仅扫描刚创建的字幕文件。

安装：将此目录整体复制到 Stash 的 `plugins/TestBtn/`，然后在 Stash 的“设置 → 插件”点击“重新加载插件”。不需要 `test_button.env`。

前端不含密码，也不再直接访问迅雷接口或文件系统，因而不会受浏览器 CORS 限制。需要 Stash 0.23+、运行环境可使用 `python`，并支持 `runPluginOperation` GraphQL mutation。Stash 运行环境必须能读取和写入场景视频所在目录。若自动扫描失败，字幕仍已保存，可在 Stash 中手动扫描该目录。
