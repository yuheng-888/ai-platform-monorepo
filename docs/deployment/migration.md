# 迁移说明

## 迁移背景

历史部署方式里存在几个典型问题：

- 主站和部分辅助服务通过手工 `nohup` 启动
- 宝塔显示状态和真实运行状态不一致
- 端口约定分散，交接时容易漏服务
- 代码与部署文档不在同一位置

## 迁移目标

迁移完成后应该满足：

- 所有核心代码统一放在一个仓库里
- 至少有一套宝塔部署文档和一套 Docker 部署文档
- 主站、CLIProxyAPI、CPA Cleanup、GoProxy、Resin 的端口固定可追踪
- 别人拿到仓库后，不需要翻聊天记录才能恢复服务

## 推荐迁移顺序

1. 先把单仓拷到新服务器
2. 按 [宝塔部署方案](/Users/luyuyuan/Desktop/yisheng-scrm/asset-manager/ai-platform-monorepo/deploy/baota/README.md) 或 [Docker 部署方案](/Users/luyuyuan/Desktop/yisheng-scrm/asset-manager/ai-platform-monorepo/deploy/docker/README.md) 建立标准入口
3. 先接通 `Resin` 与 `GoProxy`
4. 再接通 `CLIProxyAPI` 与 `CPA Cleanup`
5. 最后接主站 `main-site`
6. 验证所有接口正常后，再清理旧的手工进程

## 当前建议

如果你现在已经有一台在线服务器在跑：

- 不要第一步就粗暴清理旧进程
- 先把对应服务用宝塔或 Docker 起一个标准版本
- 确认新版本监听正常
- 再逐个下线旧进程

## 最容易漏掉的点

- 主站前端需要先构建
- CLIProxyAPI 需要可用的 `config.yaml`
- Resin 需要 `ADMIN_TOKEN` 和 `PROXY_TOKEN`
- GoProxy 的端口组不是单端口
- 主站里还需要补齐邮箱、验证码、代理和外部系统配置
