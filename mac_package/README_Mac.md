# PQE Dashboard macOS 打开方式

把 `PQE Dashboard.app` 复制到 Mac 后，双击即可打开浏览器页面。

首次运行说明：

1. 如果 macOS 提示来自未知开发者：右键点击 `PQE Dashboard.app`，选择“打开”。
2. 如果系统提示需要 Python：请先安装 Python 3 或 Anaconda。
3. 首次运行会自动安装 `streamlit`、`plotly`、`pandas`、`openpyxl` 到当前用户环境。

注意：这个 `.app` 是 macOS 可双击启动包，不是签名公证的 App Store 应用。若需要完全离线、免 Python 的独立 `.app`，必须在一台 Mac 上用 PyInstaller 打包。Linux 不能直接生成真正的 macOS 二进制可执行文件。
