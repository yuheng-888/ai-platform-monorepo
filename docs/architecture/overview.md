# Architecture Overview

## Core Idea

系统以主站为统一入口，内部再整合账号池、Gemini 子应用、CLIProxyAPI、代理网关和清理工具。

## Main Components

### main-site

负责：

- 账号注册与管理
- 统一 API
- 统一前端入口
- 与 Gemini / CLIProxyAPI / GoProxy / Resin 的整合

### gemini-gateway

负责：

- Gemini 账号管理
- Gemini 注册流程
- Gemini 内部管理前端

### CLIProxyAPI

负责：

- auth 池管理
- 管理面板
- 401 / 无效账号清理

### GoProxy + Resin

负责：

- 动态代理补充
- sticky register/runtime proxy
- 主站和注册链路的代理出口分配

### CPA Cleanup

负责：

- 辅助检测与清理
- 管理接口与控制台

## Deployment Model

推荐两种部署形态：

1. 宝塔托管
2. Docker Compose

无论哪种形态，都应保持：

- 主站作为统一入口
- 对外入口先到 nginx
- 内部服务通过固定端口或内部网络通信
