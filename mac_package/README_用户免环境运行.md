# PQE Dashboard 用户免环境运行说明

## 结论

可以把 Python 解释器、Streamlit、Plotly、Pandas、OpenPyXL 等依赖全部打包进 macOS App。

最终用户拿到的是：

`PQE_Dashboard_macOS_Standalone.zip`

用户只需要：

1. 解压 ZIP。
2. 双击 `PQE Dashboard.app`。
3. 浏览器自动打开 PQE 数据分析页面。

用户不需要：

- 安装 Python
- 安装 Anaconda
- 安装 pip 包
- 打开终端
- 运行 `build_mac_app.sh`
- 自己用 PyInstaller 打包

## 为什么仍然需要 Mac 构建一次

macOS 可执行文件必须在 Mac 系统上构建。Linux 不能直接生成真正可运行的 macOS 二进制 App。

因此推荐流程是：

1. 开发者或 CI 在 Mac 环境构建一次。
2. 得到 `PQE_Dashboard_macOS_Standalone.zip`。
3. 把 ZIP 发给最终用户。
4. 最终用户只双击运行。

## 推荐自动化方式

项目已提供 GitHub Actions 自动打包流程：

`.github/workflows/build-macos-app.yml`

使用方式：

1. 把项目上传到 GitHub 仓库。
2. 进入 GitHub 仓库页面。
3. 打开 `Actions`。
4. 选择 `Build macOS PQE Dashboard`。
5. 点击 `Run workflow`。
6. 等待构建完成。
7. 下载 Artifact：`PQE_Dashboard_macOS_Standalone`。
8. 解压后得到 `PQE_Dashboard_macOS_Standalone.zip`。
9. 把这个 ZIP 发给用户。

## 用户第一次打开的系统提示

如果 macOS 提示：

“无法验证开发者”

处理方法：

1. 右键点击 `PQE Dashboard.app`。
2. 选择“打开”。
3. 在弹窗中再次选择“打开”。

这是因为 App 没有 Apple Developer ID 签名，不是软件功能问题。

## 如果需要完全无提示

需要额外做 Apple 签名和公证：

1. 申请 Apple Developer 账号。
2. 使用 Developer ID Application 证书签名 App。
3. 使用 Apple notarytool 上传公证。
4. stapler 绑定公证结果。

完成后，普通用户双击时不会再出现未知开发者提示。
