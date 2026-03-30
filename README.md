# AI Platform Monorepo

统一的账号注册、账号池、代理网关与清理工具单仓。

这个仓库的目标很直接：把当前线上实际在跑的主站、CLIProxyAPI、CPA Cleanup、GoProxy、Resin，以及 Gemini 相关代码整理到一个可交接、可复现、可继续维护的目录里，避免后续再出现“功能能跑，但部署方式说不清”的状态。

## 这份仓库解决什么问题

- 把原本分散的代码和部署方式收回到一个仓库
- 提供两套交付路径：
  - 宝塔托管部署
  - Docker Compose 部署
- 把当前默认端口、启动方式、反向代理规则、迁移注意事项写进文档
- 明确哪些能力已经并入主站，哪些目录保留为独立服务或参考实现
- 为后续上传到你自己的 GitHub 新仓库做好结构准备

## 当前包含的核心模块

| 目录 | 作用 | 默认端口 |
| --- | --- | --- |
| `apps/main-site` | 当前主站，统一前端、注册任务、账号池、外部服务整合 | `39001` |
| `apps/gemini-gateway` | Gemini 相关独立代码基线，当前仓库保留为参考与后续整合来源 | 按需独立部署 |
| `apps/cliproxyapi` | CLIProxyAPI，负责 auth 池与兼容 OpenAI/Gemini/Claude/Codex 的代理接口 | `8317` |
| `apps/cpa-cleanup` | 账号清理工具与 Web 控制台 | `39023` |
| `apps/resin` | Sticky 代理网关，负责注册和运行阶段的出口 IP 调度 | `39024` |
| `apps/goproxy` | 动态代理池，补充上游代理来源 | `7776`-`7780` |

## 目录结构

```text
apps/
  main-site/
  gemini-gateway/
  cliproxyapi/
  cpa-cleanup/
  goproxy/
  resin/
deploy/
  baota/
  docker/
docs/
  architecture/
  credits/
  deployment/
```

## 推荐阅读顺序

1. [架构概览](/Users/luyuyuan/Desktop/yisheng-scrm/asset-manager/ai-platform-monorepo/docs/architecture/overview.md)
2. [宝塔部署方案](/Users/luyuyuan/Desktop/yisheng-scrm/asset-manager/ai-platform-monorepo/deploy/baota/README.md)
3. [Docker 部署方案](/Users/luyuyuan/Desktop/yisheng-scrm/asset-manager/ai-platform-monorepo/deploy/docker/README.md)
4. [迁移说明](/Users/luyuyuan/Desktop/yisheng-scrm/asset-manager/ai-platform-monorepo/docs/deployment/migration.md)
5. [故障排查](/Users/luyuyuan/Desktop/yisheng-scrm/asset-manager/ai-platform-monorepo/docs/deployment/troubleshooting.md)
6. [GitHub 交接说明](/Users/luyuyuan/Desktop/yisheng-scrm/asset-manager/ai-platform-monorepo/docs/deployment/github-handoff.md)
7. [引用与致谢](/Users/luyuyuan/Desktop/yisheng-scrm/asset-manager/ai-platform-monorepo/docs/credits/ACKNOWLEDGEMENTS.md)

## 当前交付状态

已经完成：

- 单仓目录已经建立
- 主站和相关依赖代码已经归档到 `apps/`
- 宝塔部署目录和 Docker 部署目录已经建立
- 当前主站运行所需的 Resin 槽位调度逻辑已补到主站代码
- 宝塔与 Docker 的第一版交接文档已经写入仓库

尚未完成：

- 还没有推到你自己的 GitHub 新仓库
- 宝塔线上仍有部分服务是手工拉起的，文档已经给出了标准化接管路径
- `apps/gemini-gateway` 目前保留为独立代码基线，不是默认 Docker Compose 的必启服务

## 默认端口约定

| 服务 | 默认端口 | 说明 |
| --- | --- | --- |
| 主站 `main-site` | `39001` | 外部主入口，经 nginx 反代 |
| CLIProxyAPI | `8317` | 内部 auth 池与管理能力 |
| CPA Cleanup | `39023` | 清理面板 |
| Resin | `39024` | 注册和运行代理网关 |
| GoProxy stable HTTP | `7776` | 低延迟固定出口 |
| GoProxy random HTTP | `7777` | 随机出口 |
| GoProxy WebUI | `7778` | 代理池管理界面 |
| GoProxy random SOCKS5 | `7779` | 随机 SOCKS5 |
| GoProxy stable SOCKS5 | `7780` | 低延迟 SOCKS5 |
| Local Solver | `8889` | 仅主站内部依赖，不建议直接暴露公网 |

## 建议的交付方式

如果你的目标是“后续别人也能接手”：

- 首选把 Python 和 Go 服务全部纳入宝塔项目管理
- `nginx` 只保留反向代理职责
- 不再依赖 `nohup` 和临时 shell 命令

如果你的目标是“新机器快速复现”：

- 使用 `deploy/docker` 下的 Compose 方案
- 先跑核心链路：`main-site + cliproxyapi + cpa-cleanup + resin + goproxy`

## GitHub 上传前最后还差什么

仓库结构和文档可以继续完善，但真正上传到 GitHub 还差最后一个外部信息：

- 你新的 GitHub 仓库地址

拿到地址后，就可以直接按 [GitHub 交接说明](/Users/luyuyuan/Desktop/yisheng-scrm/asset-manager/ai-platform-monorepo/docs/deployment/github-handoff.md) 推送。
