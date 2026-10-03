# 验证记录

日期：2026-10-03。本轮验证Windows首次控制台登录和重复授权页面修复。此前网页、独立安装、Skill格式及文档导出验证保存在[上一轮记录](https://github.com/hx101700/memoflow/blob/4a788c1c19c21f8b0004b3c56c88c463c697dc46/doc/ACCEPTANCE.md)，不重复计为本轮执行。

## 故障证据

用户对话“我需要将语音转写，你有工具吗”的原始工具记录显示，19:52:42的首次login使用默认受限权限，19:54:56重试相同命令时增加了`require_escalated`。对照读取当前Windows进程令牌，默认执行的`IsTokenRestricted`为true，正常桌面执行为false。没有获取Chrome内部崩溃转储，这些证据只定位到两次执行条件的差异。

固定BL 2.1.0源码的Windows开页使用`cmd /c start`，完整URL中的`&needapikey=true`被cmd解释；BL随后输出完整URL，由项目旧入口再次打开。原回归只检查后一次打开，未覆盖此前的BL原生调用。本轮通过真实BL与浏览器替身验证整个调用边界。

## 已执行检查

| 检查 | 实际结果 |
| --- | --- |
| 受限命令实际执行 | login在启动BL与浏览器前退出1，提示使用执行工具的正常桌面权限；没有输出WAITING_FOR_LOGIN |
| 固定BL登录合约 | BL原生cmd开页未执行；Python仅取得一个包含needapikey=true的完整URL；测试向BL原生回调发送合成凭据，由BL保存并结束进程 |
| Node适配边界 | 仅拦截固定形态的Windows官方控制台开页，其他execFile调用保留；测试通过 |
| 登录、BL、打包针对性回归 | `unittest tests.test_console_login tests.test_bailian tests.test_package`：47项通过，无跳过 |
| Python完整回归 | `unittest discover -s tests -t .`：318项通过，无跳过，约90秒 |
| Python类型 | mypy严格检查29个源码文件通过 |
| 登录适配编译 | `npm run build:login`通过，使用现有TypeScript生成发行所需CJS资源 |
| 登录UML | Mermaid 11.12.0官方包摘要核对通过；图04已重绘并查看，文字和说明框在画布内，无裁切 |
| 补丁格式 | `git diff --check`通过 |

真实BL合约使用本机回调与合成凭据，没有打开真实浏览器、使用真实录音或调用云端识别。前端未修改，本轮没有重复运行前端构建及浏览器交互回归。

## 桌面验证

在`.runtime/login-desktop-check`新建隔离工作目录，只复制已安装的固定BL包，使用开发环境Python和本轮Skill源码，以正常桌面权限启动一次login。没有复制用户凭据；这不是重新联网安装ZIP的验收。

进程先返回WAITING_FOR_LOGIN，结束时回执为`configured=false`、`console_configured=false`，没有保存凭据。未收到用户对本次窗口数量及红叉异常的确认；实际Chrome表现与人工授权尚未验证通过。未自动重复发起登录，进程结束后已清理该独立目录。

## 复现入口

开发依赖与`.runtime/skill-contract-workspace`中的固定BL/pip准备完毕后：

```powershell
npm run build:login
.venv\Scripts\python.exe -B -X utf8 -m unittest tests.test_console_login tests.test_bailian tests.test_package
.venv\Scripts\python.exe -B -X utf8 -m unittest discover -s tests -t .
.venv\Scripts\python.exe -B -X utf8 -m mypy --config-file mypy.ini
```

真实桌面login须由宿主工具使用正常桌面执行权限。授权完成后读取原进程的最终回执，不另开页面；本机凭据存在仍不等同于云端模型调用验证。

## 发行与限制

同一v0.1.0预览已更新，修复提交为`fc9786c55645ea317230a3fc073009526837150e`。ZIP包含44个Skill文件、285972字节，SHA-256为`26254e9493c4f78f9720dfa26116bde8aa2701b3452fcb5fdba131af4e4e0380`。固定清单、CRC及逐文件源码比对通过；匿名公开下载与本地ZIP逐字节一致。

远端源码树132个文件与本地修复提交一致；仍保留一个Release、一个标签和一个ZIP附件，master保持`6c83711`。附件首次上传在TLS握手阶段失败，第二次成功；确认新附件完整后替换旧附件。新增的登录适配以编译后CJS交付，TypeScript开发源、测试、UML、安装环境、录音、凭据和结果均不入包。

不更改用户原工作目录、用户级Skill安装或README本地修改。master和版本号保持原值；更新安装副本后的完整新对话验收、真实云端识别及Office逐页视觉仍需单独验证。
