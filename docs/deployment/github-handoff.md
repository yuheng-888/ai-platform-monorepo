# GitHub 交接说明

这份文档只处理一件事：把当前单仓推到你自己的 GitHub 新仓库。

## 现状

当前目录已经具备单仓结构和部署文档，但如果你要真正完成交付，还需要：

- 把目录初始化成 git 仓库
- 绑定你自己的 GitHub remote
- 推送到新仓库

## 推荐流程

### 1. 初始化仓库

```bash
cd ai-platform-monorepo
git init
git branch -M main
```

### 2. 检查忽略规则

仓库根目录已经有：

- `.gitignore`

推送前确认这些内容不会被带上去：

- `.env`
- `data/`
- `logs/`
- `*.db`
- `node_modules/`
- 本地构建产物

### 3. 提交首个版本

```bash
git add .
git commit -m "chore: initialize unified ai platform monorepo"
```

### 4. 绑定新的 GitHub 仓库

把下面的 URL 换成你自己的新仓库地址：

```bash
git remote add origin https://github.com/your-name/your-new-repo.git
```

### 5. 推送

```bash
git push -u origin main
```

## 推送前建议再检查一次

- 根 README 是否能说明仓库用途
- `deploy/baota` 和 `deploy/docker` 是否都存在
- `docs/credits/ACKNOWLEDGEMENTS.md` 是否保留
- 仓库里没有带入令牌、密码、数据库、日志

## 最后提醒

如果你要公开仓库：

- 不要提交任何真实 token
- 不要提交线上配置里的真实邮箱服务密钥
- 不要提交 Resin、CLIProxyAPI、主站数据库
