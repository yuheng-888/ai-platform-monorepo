# Gemini Gateway

这个目录保留了 Gemini 相关的独立代码基线。

## 当前定位

在当前单仓方案里：

- 主站 `apps/main-site` 仍然是对外统一入口
- 这里的 `gemini-gateway` 主要作为 Gemini 功能的独立代码来源和后续整合参考
- 默认 Docker Compose 不会自动启动这个目录对应的服务

## 什么时候需要单独关注这个目录

- 你要继续拆分 Gemini 为独立服务
- 你要回看 Gemini 侧的独立实现
- 你要把主站里 Gemini 相关逻辑和历史实现做差异比对

## 当前建议

如果你的目标是稳定交付整套系统，优先维护：

- `apps/main-site`
- `apps/cliproxyapi`
- `apps/cpa-cleanup`
- `apps/resin`
- `apps/goproxy`

如果后续要恢复 Gemini 独立部署，再单独为这里补：

- 独立 Dockerfile
- 独立启动文档
- 独立环境变量模板
