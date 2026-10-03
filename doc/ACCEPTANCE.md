# 验证记录

日期：2026-10-04。本轮针对完整代码、文档和UML复核后的修正。先阅读全文并独立复现，再执行现有及新增回归；阅读范围与设计判断见[REVIEW](REVIEW.md)。前一轮热词重复、3.1模型及用户IPO样表验证可在[对应提交记录](https://github.com/hx101700/memoflow/blob/1ee6ac5053a9db5306f4efbba4d10b136bfed139/doc/ACCEPTANCE.md)查看，不作为本轮重新执行的结果。

## 本轮实际验证

| 检查 | 结果 |
| --- | --- |
| Python完整回归 | 362项通过，无跳过，82.211秒；覆盖安装、BL本机合约、规则、会话、媒体、文档、更新及打包 |
| Python类型 | 严格mypy --no-incremental检查30个源码文件通过 |
| 前端单元与构建 | 49项TypeScript测试通过；vue-tsc类型检查及Vite构建通过 |
| 实际Edge回归 | 使用合成录音、词表和本机Python服务通过；覆盖表格纠错、保存、刷新、撤回响应中断后重试及刷新恢复、重新确认和手填；约11.74秒 |
| 临时文件冲突 | 控制两个真实Excel导出交错执行，旧代码会出现一个PARTIAL及FileNotFoundError；修正后两次和最终交付均COMPLETE。JSON记录并发写入及替换失败清理回归通过 |
| 页面独立复现 | 61行词表第二页删行后保持第二页；390px窗口的多行错误与下方提示不重叠；撤回响应丢失后刷新恢复60行热词、音频及上下文；模拟RUNNING后页面不再声称尚未上传 |
| 更新器 | 16项专项通过，包含两次改名间中断恢复、候选目录已接管时保留现状、回滚受阻保留备份，以及Python锁变化而BL锁缺失时提前停止 |
| 文档与UML | 全部11份UML源稿与接口核对；重绘01A、01C、03、09，使用Mermaid11.12.0官方包并核对dist.integrity，源稿/图像对应检查、文字边界检查和实际看图通过 |
| Skill格式与指令 | 按当前OpenAI文档、本机skill-creator及官方安装脚本人工核对入口、元数据、资源与更新边界。官方quick_validate在项目与宿主Python环境均因缺少PyYAML未能运行，不计为通过 |
| 发行包 | 文档更新后11项打包测试通过；46文件的CRC、固定清单与源码逐文件字节比对通过 |

修正后的独立浏览器探针确认：上下文错误区域底部约453.8px，下方提示从474.8px开始；页面刷新通过GET读取已有恢复数据，不额外发送撤回请求。API Key模式仍沿原接口读取凭据。

更新边界另用重新封装包验证：删除非入口的运行模块后，更新器仍可能接受该包。标准构建清单会阻止缺文件的官方包生成；更新说明明确限定本项目标准发行ZIP，不宣称更新器能验证任意改包的可运行性。

## 复现入口

```powershell
.venv\Scripts\python.exe -B -X utf8 -m unittest discover -s tests -t .
.venv\Scripts\python.exe -B -X utf8 -m mypy --config-file mypy.ini --no-incremental
npm run test:web
npm run build:web
npm run test:browser
```

BL合约依赖已准备的固定CLI测试环境，只连接127.0.0.1并使用合成凭据。浏览器默认合成词表；MEMOFLOW_TEST_HOTWORDS可指定经授权的真实样表，本轮没有使用该选项。

## 交付与限制

本机ZIP含46个文件、333052字节，SHA-256为`05aa242f89e809051ae1aa95525c5f3bf22351dc3102509b754666e412a7a25c`。旧本机ZIP已替换，远端发布待核对。包仅包含Skill运行资源和按需参考资料；开发文档、UML、测试、环境、凭据与用户数据不进入ZIP。

本轮没有进行真实3.1云端识别、浏览器登录授权、原生目录窗口人工操作、Office逐页检查或全新联网安装。完整新对话的人机使用仍需在目标环境验收。用户已安装Skill、真实工作目录与README原有本地修改保持原样。
