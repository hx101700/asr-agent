# UML设计视图

核对日期：2026-10-02。图中名称、调用关系和状态对应当前源码。类图描述实际对象；时序图中的函数模块用生命线表示调用参与者，不表示代码中存在同名服务类。状态图描述回执中的状态字符串。

图稿使用Mermaid 11.12.0渲染；PNG供直接阅读，`.mmd`为可编辑源稿。修改相关调用顺序、文件协议或状态语义时，同步源稿并重新渲染。本页及图稿属于开发文档，不进入用户发行ZIP。

| 视图 | 图像 | 可编辑源稿 |
| --- | --- | --- |
| 01A 对象职责与依赖 | [查看](uml/01-classes.png) | [源码](uml/01-classes.mmd) |
| 01B 共享数据与进程契约 | [查看](uml/01b-data.png) | [源码](uml/01b-data.mmd) |
| 02 安装 | [查看](uml/02-install.png) | [源码](uml/02-install.mmd) |
| 03 本机配置 | [查看](uml/03-configure.png) | [源码](uml/03-configure.mmd) |
| 04 凭据来源与登录 | [查看](uml/04-auth.png) | [源码](uml/04-auth.mmd) |
| 05 转写与交付 | [查看](uml/05-transcribe.png) | [源码](uml/05-transcribe.mmd) |
| 06 重新导出与状态查询 | [查看](uml/06-export.png) | [源码](uml/06-export.mmd) |
| 07 本地状态 | [查看](uml/07-state.png) | [源码](uml/07-state.mmd) |
| 08 记录保存失败 | [查看](uml/08-failure.png) | [源码](uml/08-failure.mmd) |

## 01A 对象职责与依赖

![对象职责与依赖](uml/01-classes.png)

## 01B 共享数据与进程契约

![共享数据与进程契约](uml/01b-data.png)

## 02 安装

![安装时序图](uml/02-install.png)

## 03 本机配置

![本机配置时序图](uml/03-configure.png)

## 04 凭据来源与登录

![凭据来源与登录时序图](uml/04-auth.png)

## 05 转写与交付

![转写与交付时序图](uml/05-transcribe.png)

## 06 重新导出与状态查询

![重新导出与状态查询时序图](uml/06-export.png)

## 07 本地状态

![本地状态图](uml/07-state.png)

## 08 记录保存失败

![记录保存失败时序图](uml/08-failure.png)
