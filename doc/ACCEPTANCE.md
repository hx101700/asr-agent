# 验证记录

日期：2026-10-04。本轮验证删除ZIP自更新功能后的当前项目。先重新阅读全文及核对调用关系，再运行测试；审查范围见[REVIEW](REVIEW.md)，此前验证可通过Git历史追溯。

## 本轮实际验证

| 检查 | 结果 |
| --- | --- |
| Python完整回归 | 346项通过，无跳过，85.805秒；安装、BL本机合约、规则、会话、媒体、文档和打包用例保留。16项自更新专用测试随功能删除 |
| 定向回归 | 删除功能后先执行打包与架构检查，13项通过，8.851秒；解压入口可运行、工作目录与Skill资源分离 |
| Python类型 | 严格mypy --no-incremental检查29个源码文件通过 |
| 前端单元与构建 | 49项TypeScript测试通过；vue-tsc类型检查和Vite构建通过，5个静态产物与修改前逐文件SHA一致 |
| Edge回归 | 合成录音、词表和真实本机Python服务的完整浏览器回归通过，12.30秒；测试服务和随机工作目录已清理 |
| 独立业务探针 | 合成Excel导入后清理临时副本；热词+上下文预览确认；撤回可恢复确认快照，旧编号STOPPED且BL调用0；新编号生成JSON与三格式，重导仍COMPLETE且BL边界总调用1。BL使用替身，网络调用0 |
| 文档与UML | 保留的10份源稿及10张PNG逐份查看并对照当前接口，未发现需要重绘的图；添加音频协议表述及资源树说明已纠正 |

本轮重新人工核对Skill元数据、三个使用入口及全部参考链接。官方quick_validate未运行，项目与宿主Python缺少PyYAML的既有环境限制保持；不将人工核对记为脚本通过。

## 复现入口

```powershell
.venv\Scripts\python.exe -B -X utf8 -m unittest discover -s tests -t .
.venv\Scripts\python.exe -B -X utf8 -m mypy --config-file mypy.ini --no-incremental
npm run test:web
npm run build:web
npm run test:browser
```

BL合约依赖已准备的固定CLI测试环境，只连接127.0.0.1并使用合成凭据。浏览器默认合成词表；MEMOFLOW_TEST_HOTWORDS可只读使用经授权的真实样表，本轮未设置该选项。

## 交付与限制

发布ZIP含44个文件、327364字节，SHA-256为`a839b2f2aedebf2c6b42a94b8ce812a2a33fbe89340ea8f377c786c36780abab`。CRC、固定清单及源码逐文件字节比对通过，旧本机ZIP已替换；最终文档的124个本地链接均有效。

实现提交`332fbe2099d7bc9c51e6209e00483a9706ae4caf`已推送dev，现有v0.1.0预览及双语说明已同步。匿名公开下载与本机包逐字节一致，135文件的远端源码树与实现提交一致；仍保持一个Release、一个标签和一个ZIP附件，master保持`6c83711`。本轮合成探针和其工作目录已清理。

包仅包含Skill运行资源和按需参考资料，开发文档、UML、测试、环境、凭据与用户数据不进入ZIP。

本轮没有进行真实3.1云端识别、浏览器登录授权、原生目录窗口人工操作、Office逐页检查或全新联网安装。完整新对话的人机使用仍需在目标环境验收。用户已安装Skill、真实工作目录与README原有本地修改保持原样。
