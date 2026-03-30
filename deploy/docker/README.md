# Docker 部署方案

这套方案用于新环境快速复现核心链路，不依赖宝塔。

## 当前 Compose 覆盖的核心服务

- `main-site`
- `cliproxyapi`
- `cpa-cleanup`
- `resin`
- `goproxy`

说明：

- `gemini-gateway` 代码仍保留在仓库中，但当前默认交付以主站为统一入口，所以没有放进第一版根 Compose
- 如果后续你要把 Gemini 独立跑成单独服务，可以再补对应镜像与服务段

## 文件位置

- Compose 文件：[docker-compose.yml](/Users/luyuyuan/Desktop/yisheng-scrm/asset-manager/ai-platform-monorepo/deploy/docker/docker-compose.yml)
- 环境变量模板：[.env.example](/Users/luyuyuan/Desktop/yisheng-scrm/asset-manager/ai-platform-monorepo/deploy/docker/.env.example)

## 快速开始

### 1. 复制环境变量模板

```bash
cd /www/wwwroot/ai-platform-monorepo/deploy/docker
cp .env.example .env
```

### 2. 修改关键变量

至少改这两个：

```bash
RESIN_ADMIN_TOKEN=replace-with-your-admin-token
RESIN_PROXY_TOKEN=replace-with-your-proxy-token
```

如果你要调整端口，也在 `.env` 里改：

```bash
MAIN_SITE_PORT=39001
CLIPROXYAPI_PORT=8317
CPA_CLEANUP_PORT=39023
RESIN_PORT=39024
GOPROXY_STABLE_PORT=7776
GOPROXY_RANDOM_PORT=7777
GOPROXY_WEBUI_PORT=7778
GOPROXY_SOCKS5_RANDOM_PORT=7779
GOPROXY_SOCKS5_STABLE_PORT=7780
```

### 3. 启动服务

```bash
docker compose up -d --build
```

### 4. 查看状态

```bash
docker compose ps
docker compose logs -f main-site
```

## 端口说明

| 服务 | 默认端口 |
| --- | --- |
| 主站 | `39001` |
| CLIProxyAPI | `8317` |
| CPA Cleanup | `39023` |
| Resin | `39024` |
| GoProxy stable HTTP | `7776` |
| GoProxy random HTTP | `7777` |
| GoProxy WebUI | `7778` |
| GoProxy random SOCKS5 | `7779` |
| GoProxy stable SOCKS5 | `7780` |

## 卷说明

Compose 已经预留了命名卷：

- `main_site_data`
- `main_site_logs`
- `cliproxyapi_auths`
- `cliproxyapi_logs`
- `resin_cache`
- `resin_data`
- `resin_logs`

这样做的目的是在容器重建后保留关键状态。

## 适合什么场景

适合：

- 新机器初始化
- 演示环境
- 非宝塔环境
- 想先验证核心链路能不能整体跑起来

不适合：

- 你已经在宝塔里维护了一整套项目管理
- 你需要跟现有宝塔站点完全一致的运维方式

这种情况优先走 [宝塔部署方案](/Users/luyuyuan/Desktop/yisheng-scrm/asset-manager/ai-platform-monorepo/deploy/baota/README.md)。

## 已知限制

- 第一版 Compose 重点覆盖核心服务，不追求把所有历史脚本和辅助工具都容器化
- `main-site` 仍然需要你在应用内补齐配置，例如 Resin、CLIProxyAPI、邮箱服务、验证码服务等
- `gemini-gateway` 目前是保留代码，不是默认 Compose 服务

## 推荐上线前检查

```bash
curl -I http://127.0.0.1:39001/
curl -I http://127.0.0.1:8317/
curl -I http://127.0.0.1:39023/
curl -I http://127.0.0.1:39024/
curl -I http://127.0.0.1:7778/
```
