# 验证记录

日期：2026-10-04。本轮对连续操作、正常服务关闭、凭据交接及失败提示重新审查。先阅读并构造最小复现，再修改和回归；审查范围与判断见[REVIEW](REVIEW.md)。此前验证通过Git历史追溯。

## 本轮实际验证

| 检查 | 结果 |
| --- | --- |
| 正常关闭的真实进程复现 | 本机POST声明2MB而仅发送部分字节，旧服务正常退出码0后仍留1个.part；新增真实子进程回归在旧实现失败，修改后等待请求清理，暂存会话目录为空 |
| Key保存的连续操作 | 保存期间修改发言人选项，保存返回422，旧代码丢掉auth_mode错误；新增前端回归先失败，修正后保留错误/Key/新表单值，用户修正后继续检查，没有自动重试 |
| 撤回失败边界 | 合成会话在撤回记录写入时注入OSError，旧回执保留、旧编号OUTCOME_UNKNOWN、BL调用0；占用拒绝提示已纠正，PREPARING/RUNNING/STOPPED/JSON_READY均保留原记录 |
| Python完整回归 | 347项通过，无跳过，79.782秒 |
| Python定向与类型 | 网页启动/并发14项通过；撤回/翻译/启动18项通过；严格mypy --no-incremental检查29个源文件通过 |
| 前端单元与构建 | 50项TypeScript测试通过；vue-tsc和Vite构建通过 |
| Edge回归 | 合成数据完整场景通过，12.06秒，覆盖中英/主题、词表纠错/分页、上下文、Key保存、确认/撤回及刷新恢复 |
| 已排除候选 | python-dotenv 1.2.3对UTF-8及UTF-8 BOM文件均正确替换Key：新值可读、旧值不残留、仅1条赋值、其他设置保留；不改编码逻辑 |
| UML | 10份源稿重新对照当前接口；01A、03按关闭顺序重绘，Mermaid11.12.0官方包摘要、源图对应、文字边界及实际看图通过，其余8图协议未变 |
| 包与文档链接 | 最终说明修改后11项打包测试通过，8.625秒；44文件CRC/固定清单/源码字节核对通过，124个本地Markdown链接有效 |

Skill的首次使用、现有环境、仅换Key、凭据失效、保存撤回、服务已退出及部分导出失败路径已按源码静态推演。仅换Key的交接说明已补齐；静态推演不等于新对话完整使用验收。官方quick_validate仍未运行，已知验证环境缺少PyYAML，不计为通过。

## 复现入口

```powershell
.venv\Scripts\python.exe -B -X utf8 -m unittest discover -s tests -t .
.venv\Scripts\python.exe -B -X utf8 -m mypy --config-file mypy.ini --no-incremental
npm run test:web
npm run build:web
npm run test:browser
```

BL合约使用固定CLI和127.0.0.1模拟服务；浏览器使用合成数据，本轮未设置MEMOFLOW_TEST_HOTWORDS或读取用户真实词表。临时凭据只使用合成值。

## 交付与限制

发布ZIP含44文件、327657字节，SHA-256为`7b41e481560b3b5b7a6ea3f66652dc530ae2f2d37de16298fb02f924f94e0d36`。实现提交`ac8a3cc8ba43f6472be6c30bf5c72dc571fe56bd`已推送dev，同一v0.1.0预览及双语说明已更新。匿名公开下载与本机包逐字节一致，135文件的远端源码树与实现提交一致；远端仍为一个Release、一个标签和一个ZIP附件，master保持`6c83711`。

包仅包含Skill运行资源和按需参考资料；开发文档、UML、测试、环境、凭据与用户数据不进入ZIP。

本轮没有进行真实3.1云端识别、登录授权、原生目录窗口人工操作、Office逐页检查或全新联网安装。正常关闭回归不保证强制终止进程后的清理。用户安装、真实工作目录及README原有本地修改保持原样。
