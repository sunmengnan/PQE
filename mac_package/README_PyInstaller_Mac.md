# Mac 上用 PyInstaller 打包 PQE Dashboard

本文档面向开发/交付人员，用于在 Mac 机器上生成用户可直接双击运行的 `PQE Dashboard.app`。

## 结论

可以让用户直接运行。推荐交付物是：

- `PQE Dashboard.app`：用户双击打开。
- 或 `PQE_Dashboard_macOS_Standalone.zip`：压缩包，用户解压后双击 App。

注意：真正的 macOS 可执行程序必须在 Mac 上打包。Linux 只能生成启动脚本型 `.app`，不能生成真正的 macOS 二进制。

## 打包前准备

Mac 上需要先安装：

1. Python 3.9+ 或 Anaconda。
2. 网络连接，用于首次安装依赖。

## 打包步骤

1. 把整个项目文件夹复制到 Mac。
2. 打开项目中的 `mac_package` 文件夹。
3. 双击或运行 `build_mac_app.sh`。
4. 等待打包完成。
5. 打包结果在：
   - `mac_package/release/PQE Dashboard.app`
   - `mac_package/release/PQE_Dashboard_macOS_Standalone.zip`

## 如果 Mac 不允许双击脚本

可以右键 `build_mac_app.sh`，选择“打开”。

如果仍然不能打开，可在“系统设置 → 隐私与安全性”中允许该脚本运行。

## 交付给最终用户

把下面这个文件发给用户：

- `mac_package/release/PQE_Dashboard_macOS_Standalone.zip`

用户操作：

1. 解压 ZIP。
2. 双击 `PQE Dashboard.app`。
3. 浏览器会自动打开 PQE 分析页面。

## 常见问题

### 为什么必须在 Mac 上打包？

macOS App 包含 Mac 专用启动器和二进制文件。PyInstaller 不支持在 Linux 上直接交叉编译真正的 macOS `.app`。

### 用户还需要安装 Python 吗？

如果交付的是 PyInstaller 打包后的 `release/PQE Dashboard.app`，用户通常不需要安装 Python。

如果交付的是当前 Linux 生成的启动脚本型 `.app`，则 Mac 用户仍需要 Python 环境。

### App 第一次打开提示“无法验证开发者”怎么办？

因为该 App 没有 Apple Developer ID 签名。处理方式：

1. 右键点击 `PQE Dashboard.app`。
2. 选择“打开”。
3. 在弹窗中再次选择“打开”。

如果需要完全消除该提示，需要使用 Apple Developer ID 对 App 进行签名和公证。
