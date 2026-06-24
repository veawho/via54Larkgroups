# Setup Guide (中文)

完整的中文使用手册。包含：

1. 建飞书自建应用 (5 步)
2. 保存 App ID/Secret
3. 浏览器 OAuth 登录
4. 拉取聊天
5. 导出 Markdown
6. 命令速查
7. 安全检查清单

请看 [setup_zh.md](setup_zh.md).

## 快速对照表

| 步骤 | 命令 |
|------|------|
| 1. 建 App | https://open.feishu.cn/app |
| 2. 保存凭证 | `feishu-vault config --app-id X --app-secret Y` |
| 3. 登录 | `feishu-vault login` |
| 4. 拉聊天 | `feishu-vault sync` |
| 5. 导出 | `feishu-vault archive` |
| 6. 看状态 | `feishu-vault status` |
| 7. 停止 | `feishu-vault stop` |
| 8. 登出 | `feishu-vault logout` |