# Acknowledgements

本项目的整合与二次开发建立在多个优秀开源项目之上。感谢原作者和维护者的工作。

## Referenced Projects

### any-auto-register

- Source: [lxf746/any-auto-register](https://github.com/lxf746/any-auto-register)
- Usage:
  - 当前主站账号注册与管理能力的主要基础来源
  - 我们在其基础上继续整合了任务、代理、统一平台入口等能力

### CLIProxyAPI

- Source: [router-for-me/CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI)
- Usage:
  - 作为内部 auth 池与代理管理服务的一部分
  - 当前系统中用于注册成功后账号写入与管理面板能力

### gemini-business2api

- Source: [yukkcat/gemini-business2api](https://github.com/yukkcat/gemini-business2api)
- Usage:
  - 作为 Gemini 管理与注册链路的基础来源
  - 我们在其基础上做了嵌入、配置适配、多 IP 并发注册等整合

### cpa-codex-cleanup

- Source: [qcmuu/cpa-codex-cleanup](https://github.com/qcmuu/cpa-codex-cleanup)
- Usage:
  - 用于补充 CLIProxyAPI 池清理与可视化控制台能力

### GoProxy

- Source: [isboyjc/GoProxy](https://github.com/isboyjc/GoProxy)
- Usage:
  - 作为动态代理补充源的一部分
  - 当前系统中与 Resin 形成同步链路

### Resin

- Source: [Resinat/Resin](https://github.com/Resinat/Resin)
- Usage:
  - 作为主站与注册链路的代理网关核心
  - 当前系统中承担 sticky proxy / register proxy 的关键职责

## Thanks

感谢以上项目的创建者、维护者与贡献者。

没有这些开源项目作为基础，就不会有当前这一套整合后的平台能力。
