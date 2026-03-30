# 宝塔部署方案

这份文档的目标不是“给一个思路”，而是把这套系统接入宝塔时需要的关键路径一次写清楚。

## 适用场景

适合：

- 你希望所有服务都在宝塔项目页中可见、可启动、可重启
- 后续要把源码交给别人维护
- 不希望继续依赖手工 `nohup` 启动

不适合：

- 你只想在一台新机器上快速试跑
- 你更倾向纯容器化部署

这种情况建议走 [Docker 部署方案](/Users/luyuyuan/Desktop/yisheng-scrm/asset-manager/ai-platform-monorepo/deploy/docker/README.md)。

## 推荐环境

- Ubuntu 22.04 / 24.04 或 Debian 12
- 宝塔面板最新版
- Miniforge / Conda
- Python `3.12`
- Go `1.22+`
- Node.js `18+`
- nginx

## 推荐仓库目录

推荐把整个单仓放到固定路径，例如：

```bash
/www/wwwroot/ai-platform-monorepo
```

下文都以这个路径举例。

## 服务与端口约定

| 服务 | 目录 | 端口 | 是否建议纳入宝塔 |
| --- | --- | --- | --- |
| 主站 `main-site` | `apps/main-site` | `39001` | 是 |
| CLIProxyAPI | `apps/cliproxyapi` | `8317` | 是 |
| CPA Cleanup | `apps/cpa-cleanup` | `39023` | 是 |
| Resin | `apps/resin` | `39024` | 是 |
| GoProxy | `apps/goproxy` | `7776`-`7780` | 是 |
| Gemini Gateway | `apps/gemini-gateway` | 按需 | 可选 |

## 推荐部署顺序

1. 部署 `Resin`
2. 部署 `GoProxy`
3. 部署 `CLIProxyAPI`
4. 部署 `CPA Cleanup`
5. 部署 `main-site`
6. 最后配置 `nginx` 反代

这样做的原因是主站会依赖前面几个服务的地址和令牌。

## 预处理

### 1. 准备 Python 环境

推荐固定环境名：

```bash
conda create -n any-auto-register python=3.12 -y
conda activate any-auto-register
```

### 2. 安装主站和清理工具依赖

```bash
cd /www/wwwroot/ai-platform-monorepo/apps/main-site
pip install -r requirements.txt

cd /www/wwwroot/ai-platform-monorepo/apps/cpa-cleanup
pip install curl_cffi
```

### 3. 构建主站前端

```bash
cd /www/wwwroot/ai-platform-monorepo/apps/main-site/frontend
npm install
npm run build
```

### 4. 构建 Go 服务

CLIProxyAPI：

```bash
cd /www/wwwroot/ai-platform-monorepo/apps/cliproxyapi
go build -o cli-proxy-api ./cmd/server
```

Resin：

```bash
cd /www/wwwroot/ai-platform-monorepo/apps/resin
go build -o resin ./cmd/resin
```

GoProxy：

```bash
cd /www/wwwroot/ai-platform-monorepo/apps/goproxy
go build -o goproxy .
```

## 宝塔项目启动命令

下面这些命令适合填入宝塔项目管理器的启动命令栏。

### main-site

项目目录：

```bash
/www/wwwroot/ai-platform-monorepo/apps/main-site
```

启动命令：

```bash
env HOST=0.0.0.0 \
PORT=39001 \
APP_CONDA_ENV=any-auto-register \
PYTHONPATH=/www/wwwroot/ai-platform-monorepo/apps/main-site \
/opt/miniforge3/envs/any-auto-register/bin/python main.py
```

### CLIProxyAPI

项目目录：

```bash
/www/wwwroot/ai-platform-monorepo/apps/cliproxyapi
```

启动命令：

```bash
./cli-proxy-api -config ./config.yaml
```

说明：

- `config.yaml` 建议由 `config.example.yaml` 复制后手工维护
- `auths/` 目录需要持久化

### CPA Cleanup

项目目录：

```bash
/www/wwwroot/ai-platform-monorepo/apps/cpa-cleanup
```

启动命令：

```bash
/opt/miniforge3/envs/any-auto-register/bin/python cpa_codex_cleanup_web.py --host 0.0.0.0 --port 39023
```

### Resin

项目目录：

```bash
/www/wwwroot/ai-platform-monorepo/apps/resin
```

启动命令：

```bash
env RESIN_AUTH_VERSION=V1 \
RESIN_ADMIN_TOKEN=change-me-admin-token \
RESIN_PROXY_TOKEN=change-me-proxy-token \
RESIN_LISTEN_ADDRESS=0.0.0.0 \
RESIN_PORT=39024 \
RESIN_STATE_DIR=/www/wwwroot/ai-platform-monorepo/apps/resin/data/state \
RESIN_CACHE_DIR=/www/wwwroot/ai-platform-monorepo/apps/resin/data/cache \
RESIN_LOG_DIR=/www/wwwroot/ai-platform-monorepo/apps/resin/data/log \
./resin
```

### GoProxy

项目目录：

```bash
/www/wwwroot/ai-platform-monorepo/apps/goproxy
```

启动命令：

```bash
./goproxy
```

说明：

- 默认会监听 `7776`、`7777`、`7778`、`7779`、`7780`
- 对公网开放前建议先设置 WebUI 密码

## nginx 入口配置

可直接参考模板：

- [nginx-main-site.conf](/Users/luyuyuan/Desktop/yisheng-scrm/asset-manager/ai-platform-monorepo/deploy/baota/nginx-main-site.conf)

核心逻辑是把 `80/443` 转到主站：

```nginx
proxy_pass http://127.0.0.1:39001;
```

## 上线后的检查清单

主站：

```bash
curl -I http://127.0.0.1:39001/
```

CLIProxyAPI：

```bash
curl -I http://127.0.0.1:8317/
```

CPA Cleanup：

```bash
curl -I http://127.0.0.1:39023/
```

Resin：

```bash
curl -I http://127.0.0.1:39024/
```

GoProxy WebUI：

```bash
curl -I http://127.0.0.1:7778/
```

## 当前线上状态说明

当前线上已经验证过的运行端口与这一份文档保持一致：

- 主站 `39001`
- CLIProxyAPI `8317`
- CPA Cleanup `39023`
- Resin `39024`
- GoProxy `7776`-`7780`

但当前实际服务器里仍存在手工拉起的进程痕迹，所以如果你要做正式交付，建议按这份文档逐个接回宝塔管理。

## 交接建议

- 所有令牌不要写死在仓库里，统一放到宝塔项目环境变量中
- 主站、Resin、CLIProxyAPI 的数据目录要单独备份
- 完成宝塔纳管后，再清理历史 `nohup` / 临时 shell 启动方式
