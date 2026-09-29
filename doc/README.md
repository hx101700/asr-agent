# 文档中心

本文档集用于恢复 asr-agent 的需求、技术约束和开发状态。编写方式采用概述、使用限制、操作步骤、参数表和常见问题等技术文档结构；这是项目文档，不是阿里云官方文档。

## 阅读顺序

| 文档 | 内容 | 何时阅读 |
| --- | --- | --- |
| [STATUS.md](STATUS.md) | 当前阶段、已确认决策、下一步和验证情况 | 每次开始工作 |
| [CODE_REVIEW.md](CODE_REVIEW.md) | 995703e审查、整改设计及完成记录 | 追溯整改原因 |
| [S1_VERIFICATION.md](S1_VERIFICATION.md) | S1历史验证与环境能力依据 | 需要追溯基础实现时 |
| [S2_VERIFICATION.md](S2_VERIFICATION.md) | 网页、直接选文件、组合增强、确认及浏览器验证 | 接续S2/S3 |
| [S3_VERIFICATION.md](S3_VERIFICATION.md) | 明确授权的执行入口、一次执行记录、BL合约及限制 | 执行与接续S3/S4 |
| [DEVELOPMENT.md](DEVELOPMENT.md) | 需求、原子能力、架构、界面、数据与阶段计划 | 开发前 |
| [REFERENCES.md](REFERENCES.md) | 官方来源、版本基线、能力限制与证据边界 | 实现接口前 |
| [ERRORS.md](ERRORS.md) | 官方状态/错误与本地错误的区别及解释规则 | 实现和排障 |
| [ACCEPTANCE.md](ACCEPTANCE.md) | 分阶段检查与端到端验收 | 测试和交付 |
| [ISSUES.md](ISSUES.md) | 未决问题、证据、处理状态 | 遇到阻碍 |
| [DEVLOG.md](DEVLOG.md) | 重要进展和决策记录 | 恢复历史背景 |
| [HELP.md](HELP.md) | 面向使用者的操作步骤、限制和故障处理 | 使用前 |

## 文档状态约定

- **已确认**：用户明确决定，或有已读取的官方证据；二者在正文中区分。
- **方案**：项目建议的实现，尚未具备运行证据。
- **待验证**：需要锁定 CLI 版本、探针或真实流程验收，不能当成已完成能力。

S3受影响的官方CLI、Filetrans结果和错误资料已于 **2026-09-29** 复核；各来源日期见REFERENCES。实施阶段重新核对受影响的项目即可，无须反复调研无关能力。
