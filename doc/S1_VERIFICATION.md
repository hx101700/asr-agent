# S1 本地基础验证记录

记录日期：2026-09-28。本文保留S1历史验证；最新状态以STATUS.md和S2_VERIFICATION.md为准。媒体实现为PyAV，旧独立FFmpeg ZIP安装方案已退役。

## 已实现命令

在项目根目录执行：

| 命令 | 行为 | 本机结果 |
| --- | --- | --- |
| `python scripts/asr.py bootstrap` | 创建项目venv，pip安装锁定Python依赖，npm ci安装BL | 已安装；再次执行成功，不覆盖不匹配的BL |
| `.venv\Scripts\python.exe scripts/asr.py doctor` | 检查BL实际启动、venv与Python库 | 通过，issues为空 |
| `.venv\Scripts\python.exe scripts/asr.py probe-bl` | 公开帮助与固定虚构URL dry-run | 前一轮已通过；本轮仍受合约测试保护 |
| `.venv\Scripts\python.exe scripts/asr.py api-key-status` | 读取指定.env，仅返回配置状态 | 空Key正确返回未配置；不回显Key、不宣称在线验证 |

网页、真实登录、音频上传、云端识别和三种文档导出尚未实现/验收。`bailian_environment()`只构造后续调用所需环境，尚未连接真实识别入口。

## 环境与依赖

- Windows x64，Python3.12.1，Node24.19.0，项目内BL四个相关包均2.1.0。
- Python直接运行依赖：`av==18.1.0`、`python-dotenv==1.2.3`。未安装NumPy、pydub、ffmpeg-python或额外Agent框架。
- PyAV Windows wheel为cp311-abi3-win_amd64，兼容本机CPython3.12，内部附带FFmpeg库，不需要ffmpeg.exe/ffprobe.exe。
- `requirements.txt`固定两份wheel的SHA256；`tools/bailian/package-lock.json`保留55个上游生产依赖及完整性摘要，没有可随意删去的dev-only/optional包。
- 本机旧pip联网下载PyAV曾拿到不完整文件并因摘要不符被拒绝；随后以Node标准网络能力取得同一PyPI官方wheel，校验原摘要后交给pip本地安装。未修改摘要或增加产品内下载器。标准bootstrap的干净机联网安装仍需S5验收。
- `bootstrap`给子进程设置项目内临时目录，禁用用户pip/npm配置继承、缓存或自动重试；现有BL流程仍通过npm复用，命令统一quiet以阻止其自动全局升级。

## 媒体验证

`media.py`用PyAV逐帧解码、AudioResampler转换及FLAC编码，没有Python混音计算。默认处理第一个音轨，与BL首版规则一致；probe返回音轨数量供后续网页提醒，不拼接不同音轨。

已通过：

- 合成WAV立体声→单声道FLAC，采样率与有效样本时长符合检查，源文件哈希不变。
- 左右声道分时有声，两侧都参与输出；标准5.1布局可转换为单声道。
- 合成MP3可解码并转换；单声道输入不产生多余副本。
- 既有输出不覆盖，源路径不能作为转换目标，损坏音频不创建成品。

输出时长按有效解码样本数核验，容差为1个样本。此验证不等于所有模型支持格式、异常时间戳、超长或接近1GB输入均已验收。标准下混不承诺任意声道布局等权参与。

## .env与API Key验证

使用python-dotenv读取显式项目.env，关闭变量展开，不更新全局os.environ。只检查文件/配置可用性及内部空白，不发在线请求。状态中`verified_online`始终为false。

已验证：缺失/空Key提示、成功配置不回显密钥、不使用全局环境Key、控制台模式不读.env、仅API Key模式向BL环境注入Key、多行值拒绝且错误不泄露值。测试全部使用合成字符串；本地.env仍为空。

## BL合约证据

真实BL2.1.0连接127.0.0.1模拟服务，使用合成Key与虚构URL：完整流程能保存JSON；提交401/500与查询500均未重试；任务失败后停止；子任务失败可以退出0并写`[]`；CANCELED/UNKNOWN持续查询至超时且没有重提。普通完整成功路径不返回task_id。

Python HTTP服务只在测试fixture中，不是产品ASR客户端。BL可能查询公开版本信息，因此不称整个进程完全离线。没有真实阿里云ASR请求或用户音频上传。

## 测试与清理

```powershell
.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -t . -v
```

本轮发现35项用例，35项成功，0跳过/失败/错误；逐项记录位于被忽略的`.state/tests-report.json`。

已删除旧`media_setup.py`、`media_worker.py`、`media-lock.json`及专用ZIP安装测试，移除旧命令。清理失败FFmpeg下载、npm缓存、临时wheel和旧字节码等共83,277,373字节；保留正在使用的BL、Python环境、项目资料与数据。

历史：前一版曾因FFmpeg ZIP不完整而拦截安装，当时25项成功、3项跳过。这是旧方案记录，不表示该下载问题已修复；现在通过更换媒体集成方式解除依赖该下载的阻碍。
