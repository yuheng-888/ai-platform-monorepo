# 故障排查

## 1. 宝塔显示未启动，但服务其实能访问

这通常表示：

- 服务不是由宝塔项目管理器启动的
- 而是被 `nohup`、后台 shell 或临时脚本拉起来了

处理方式：

- 先通过 `ps -ef` 和 `ss -ltnp` 查清真实进程
- 再把该服务按 [宝塔部署方案](/Users/luyuyuan/Desktop/yisheng-scrm/asset-manager/ai-platform-monorepo/deploy/baota/README.md) 接管

## 2. 打开服务器 IP 只看到宝塔默认页

这通常表示：

- `80/443` 的 nginx 入口没有转发到主站 `39001`
- 或者当前访问落到了默认站点

处理方式：

- 检查 nginx 配置是否引用了 [nginx-main-site.conf](/Users/luyuyuan/Desktop/yisheng-scrm/asset-manager/ai-platform-monorepo/deploy/baota/nginx-main-site.conf)
- 确认：

```nginx
proxy_pass http://127.0.0.1:39001;
```

## 3. 主站返回 502 / 503

优先检查：

- `main-site` 进程是否还在
- `39001` 是否正在监听
- 主站日志里是否有导入错误或配置错误

排查命令：

```bash
ps -ef | grep main.py | grep -v grep
ss -ltnp | grep 39001
curl -I http://127.0.0.1:39001/
```

## 4. `/api/config` 返回 401

这不是服务挂了，而是：

- 你没有登录
- 或者请求没带认证上下文

这类接口属于受保护接口，先登录主站再测。

## 5. `/api/gemini/status` 返回 401

同样优先判断为认证问题，而不是网络问题：

- 路由可达
- 但当前会话无权限

## 6. Resin 可访问，但代理不生效

优先检查：

- `RESIN_ADMIN_TOKEN`
- `RESIN_PROXY_TOKEN`
- 平台规则是否正确
- 上游订阅是否真的导入成功

再检查主站中：

- `resin_url`
- `resin_admin_token`
- `resin_proxy_token`

## 7. 自动注册速度慢

优先确认三件事：

- `register_max_concurrency` 是否足够
- Resin 的每 IP 槽位配置是否生效
- 上游节点是否真的足够多

当前默认策略：

- 普通节点每 IP `5` 个槽位
- 白名单节点每 IP `10` 个槽位

## 8. Docker Compose 起不来

优先检查：

- `deploy/docker/.env` 是否存在
- `RESIN_ADMIN_TOKEN`、`RESIN_PROXY_TOKEN` 是否已改
- 各服务端口是否被宿主机占用

排查命令：

```bash
docker compose ps
docker compose logs -f
```
