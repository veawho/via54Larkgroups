# feishu-vault 部署与使用手册

> 一个**本地**的飞书聊天归档工具 — 全部数据存你电脑，**不上传任何服务器**。
> 工具源码：`C:\Users\via54\Tools\feishu-vault\`
> 数据位置：`C:\Users\via54\AppData\Local\hermes\feishu_vault\`

---

## 0. 这是什么 & 为什么用它

| 维度 | feishu-vault | 飞书官方导出 | 第三方 SaaS |
|------|-------------|------------|------------|
| 数据位置 | **你电脑本地** | 飞书云端导出 zip | 第三方服务器 |
| 是否要钱 | 免费 | 免费（仅文本） | 通常要钱 |
| 文件附件 | 可选下载 | 不支持 | 通常支持 |
| 自动每天同步 | ✅ 默认 OFF，可手开 | ❌ 手动 | 通常默认开 |
| 自动停止开关 | ✅ `stop` 5s 内停 | 不适用 | 通常要后台设置 |
| OAuth scope | **最小**（3 个只读） | 完整账号 | 通常要更多 |

**护栏（已硬编码进代码）**：
- ✅ 默认 OFF，所有同步都要手动触发
- ✅ OAuth scope 锁定 3 个只读（`im:message:readonly` 等），**不能发消息**
- ✅ Token 24h 过期，过期强制重新登录
- ✅ 文件附件默认只下载元数据，**文件本体 opt-in**
- ✅ 一键停止：`feishu-vault stop`
- ✅ 审计日志：每次同步写一行 JSON 到 `audit.log`

---

## 1. 建飞书自建应用（5 步，约 10 分钟）

### Step 1.1: 登录飞书开放平台

打开 https://open.feishu.cn/app

用你的飞书账号登录（跟你日常用的飞书同一个）。

---

### Step 1.2: 创建企业自建应用

1. 点 **"创建企业自建应用"**
2. 填写：
   - **应用名称**：`feishu-vault`（或任意你喜欢的名字）
   - **应用描述**：本地聊天归档工具
   - **应用图标**：跳过
3. 点 **"确定创建"**

---

### Step 1.3: 勾选权限（必须只勾这 3 个）

进入新创建的应用 → 左边菜单 **"权限管理"** → **"API 权限"**。

搜索并勾选以下 3 个权限（**只勾这 3 个，不要勾别的**）：

| 权限 | 作用 |
|------|------|
| `im:message:readonly` | 读取用户能看的所有消息（核心） |
| `im:message.group_at_msg:readonly` | 读取 @ 提醒消息 |
| `contact:user.base:readonly` | 读取用户基本信息（用于显示发送者名字） |

**特别警告**：
- ❌ **不要勾** `im:message:send` 或任何 `write` scope（那会让工具能**替你发消息**）
- ❌ **不要勾** `im:message` 完整的（只勾 `readonly` 版本）
- ❌ **不要勾** `contact:user` 完整（只勾 `:base:readonly`）

---

### Step 1.4: 添加"消息与群组"权限范围

权限管理页 → **"权限管理"** → **"数据权限"** 或 **"权限范围"**：

1. 选 **"消息与群组"**
2. 设置可访问范围为 **"全部员工"** 或 **"指定部门"**（看你们公司治理）
3. 保存

---

### Step 1.5: 创建版本并发布

1. 左边菜单 **"版本管理与发布"** → **"创建版本"**
2. 填写版本号（如 `1.0.0`）+ 备注
3. 点 **"保存并发布"**
4. 如果是企业自建应用，会让你**管理员审批**（如果你是管理员就立刻通过）

发布成功后，应用才能被 OAuth 调用。

---

### Step 1.6: 拿 App ID 和 App Secret

1. 左边菜单 **"基础信息"** → **"凭证与基础信息"**
2. 复制：
   - **App ID**（格式：`cli_xxxxxxxxxxxxxxxx`）
   - **App Secret**（格式：32 字符字符串）
3. **不要贴到聊天**，等下用 PowerShell 直接写到 config 文件

---

## 2. 保存 App ID/Secret 到 feishu-vault

打开 PowerShell（**单行命令一条一条执行**，按你之前的偏好）：

### 2.1: 写入 App ID

```powershell
"C:\Users\via54\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" "C:\Users\via54\Tools\feishu-vault\feishu_vault.py" config --app-id "cli_你的AppID" --app-secret "你的AppSecret"
```

把 `cli_你的AppID` 和 `你的AppSecret` 替换成第 1.6 步拿到的值。

执行后会看到：
```
[feishu-vault] Saved app_id + app_secret to C:\Users\via54\AppData\Local\hermes\feishu_vault\config.json
[feishu-vault] NOTE: file contains secret. Do not commit to git.
```

---

## 3. 浏览器登录拿 user_access_token

```powershell
"C:\Users\via54\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" "C:\Users\via54\Tools\feishu-vault\feishu_vault.py" login
```

或者用 .bat wrapper（更简单）：

```powershell
C:\Users\via54\Tools\feishu-vault\scripts\feishu-vault.bat login
```

执行后：
1. 自动打开浏览器，跳到飞书 OAuth 页面
2. 飞书会显示授权页，**看清楚勾选的是不是你设的 3 个只读 scope**
3. 同意授权
4. 浏览器自动跳回 localhost 回调（成功页：*"feishu-vault: login successful"*）
5. Token 自动保存到 `token.json`，**24h 有效**

如果浏览器没自动打开，会显示：
```
[feishu-vault] Opening browser for Feishu login...
[feishu-vault] If browser does not open, visit:
    https://open.feishu.cn/oauth2/authen/v2/index?app_id=...
```

复制 URL 自己打开。

---

## 4. 拉取今天的聊天

```powershell
C:\Users\via54\Tools\feishu-vault\scripts\feishu-vault.bat sync
```

默认只拉**元数据**（文本 + 发送者 + 时间 + 文件名），**不下载文件本体**。

要下载文件本体：

```powershell
C:\Users\via54\Tools\feishu-vault\scripts\feishu-vault.bat sync --include-attachments
```

⚠️ 加 `--include-attachments` 会**真的下载所有图片/视频/文件到本地**，可能占很多空间。命令会先给你 5 秒反悔时间。

执行后会显示：
```
[feishu-vault] Syncing last 24h...
[feishu-vault] Found 23 chats
[feishu-vault] Done: {"messages_fetched": 142, "chats_scanned": 23, "errors": 0, "bytes_text": 18432}
```

---

## 5. 导出 markdown

```powershell
C:\Users\via54\Tools\feishu-vault\scripts\feishu-vault.bat archive
```

默认导出今天（CST 时区）。

指定日期：

```powershell
C:\Users\via54\Tools\feishu-vault\scripts\feishu-vault.bat archive --date 2026-06-23
```

输出位置：`C:\Users\via54\AppData\Local\hermes\feishu_vault\archive\YYYY-MM-DD\YYYY-MM-DD.md`

附件（如有下载）：`...archive\attachments\<message_id>\<file_name>`

---

## 6. 搜索归档

```powershell
C:\Users\via54\Tools\feishu-vault\scripts\feishu-vault.bat search --keyword "辉哥别墅"
```

列出所有 .md 文件里包含关键词的路径。

---

## 7. 看状态

```powershell
C:\Users\via54\Tools\feishu-vault\scripts\feishu-vault.bat status
```

输出：
```
=== feishu-vault status ===
Data root: C:\Users\via54\AppData\Local\hermes\feishu_vault
Config file: present
Token: present, expires in 23h 45m
Scopes: im:message:readonly im:message.group_at_msg:readonly contact:user.base:readonly
Auto-sync: OFF (default)
DB: 142 messages, 23 chats, 0 attachments
```

---

## 8. 启用每天自动同步（可选）

默认 **OFF**。要每天凌晨自动同步一次（24h 间隔）：

```powershell
C:\Users\via54\Tools\feishu-vault\scripts\feishu-vault.bat --enable-auto-sync
```

这会在数据目录创建 `auto_sync.enabled` flag 文件。**token 过期后自动 sync 会停**（需要重新 login）。

> ⚠️ 自动 sync 需要登录后的 token 24h 持续有效。**每天都要重新 login**（OAuth 不让长期 token），所以"自动 sync"实际是**手动 login + 后台 24h 跑一次**。

---

## 9. 一键停止

```powershell
C:\Users\via54\Tools\feishu-vault\scripts\feishu-vault.bat stop
```

5 秒内停掉所有后台 sync，删除 `auto_sync.enabled` flag。

---

## 10. 登出（清除 token）

```powershell
C:\Users\via54\Tools\feishu-vault\scripts\feishu-vault.bat logout
```

删除 `token.json`。下次 sync 需要重新 login。

---

## 常见问题

### Q1: Token 报错 "scope not allowed"

原因：飞书返回了**你没申请**的 scope（不在 3 个只读列表里）。

修复：去飞书 App 权限管理，确认只勾了那 3 个 readonly scope，重新发布版本，然后重新 login。

### Q2: Sync 报 "API key not valid"

原因：token 过期（24h 后）。

修复：跑 `login` 重新拿 token。

### Q3: 想看历史日期的归档

跑 `archive --date YYYY-MM-DD`，但**只能导出已经 sync 过的那天**（sync 窗口是最近 24h）。

要导**30 天前**的聊天：
- 需要先把窗口调成 30 天（**当前代码是硬编码 24h，需要改源码**）
- 或者每天开自动 sync 跑 30 天

### Q4: 数据会不会外泄？

**不会**。代码审计：
- ✅ 所有数据写入 `~/AppData/Local/hermes/feishu_vault/`
- ✅ 没有 `requests.post()` 到任何第三方服务器
- ✅ 所有网络请求的目标**只有** `open.feishu.cn`（飞书官方）
- ✅ 附件下载直接走飞书 temp URL，文件落到本地

想验证：grep 整个项目有没有非 `open.feishu.cn` 的 URL：

```powershell
findstr /S /R "https" "C:\Users\via54\Tools\feishu-vault\"
```

应该只有 `open.feishu.cn` / `passport.feishu.cn` 相关。

### Q5: 想彻底删除所有数据

```powershell
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\hermes\feishu_vault"
```

---

## 命令速查

| 命令 | 作用 |
|------|------|
| `feishu-vault config --app-id X --app-secret Y` | 保存飞书 App 凭证 |
| `feishu-vault login` | 浏览器 OAuth 登录 |
| `feishu-vault logout` | 清除 token |
| `feishu-vault status` | 看当前状态 |
| `feishu-vault sync` | 拉最近 24h 聊天 |
| `feishu-vault sync --include-attachments` | 拉聊天 + 下载附件 |
| `feishu-vault archive` | 导出今天的 markdown |
| `feishu-vault archive --date 2026-06-23` | 导出指定日期 |
| `feishu-vault search --keyword X` | 搜归档 |
| `feishu-vault --enable-auto-sync` | 开每天自动同步 |
| `feishu-vault stop` | 一键停止所有后台同步 |

---

## 安全检查清单

部署完成后**自检 5 件事**：

- [ ] App 权限页只勾了 3 个 readonly scope
- [ ] `config.json` 里没把 App Secret 贴到 git/聊天
- [ ] `token.json` 24h 后失效（过期时间 = issued + 86400）
- [ ] `status` 输出 Scopes 字段**只显示** 3 个 readonly
- [ ] 整个项目里没有 `https://` 指向**非** `feishu.cn` 的 URL

---

## 完

工具已就绪，按上面 1 → 11 步操作即可。
遇到问题贴 `status` 输出 + 错误信息，我帮你 debug。