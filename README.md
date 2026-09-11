# SB.SB 烧饼论坛 GitHub Actions 自动签到

目标站点：`https://sb.sb/`

> 这是针对 **sb.sb 烧饼论坛** 的版本，不是 linux.sb。

## 工作流程

当前 sb.sb 自动签到逻辑为：

1. 使用浏览器 Cookie 请求 `https://sb.sb/signin/`
2. 检查页面是否显示“今日已签到”或签到按钮是否已禁用
3. 未签到时读取页面中的 `_csrf`
4. `POST https://sb.sb/signin/`
5. 再检查返回页面 / 重新请求签到页，确认签到成功
6. 可选 Telegram 通知

脚本不会打印 Cookie。

## GitHub Secrets

进入：

`Repository -> Settings -> Secrets and variables -> Actions -> New repository secret`

必须创建：

```text
SB_COOKIE
```

值为你登录 sb.sb 后浏览器请求中的完整 Cookie。

可选：

```text
TG_BOT_TOKEN
TG_CHAT_ID
```

用于 Telegram 推送签到成功 / 失败。

## 获取 Cookie

在 Chrome / Edge 中：

1. 登录 `https://sb.sb/`
2. F12 -> Network
3. 刷新页面
4. 点任意一个发往 `sb.sb` 的请求
5. Headers -> Request Headers
6. 找 `Cookie:`
7. 复制 `Cookie:` 后面的完整内容

不要把 Cookie 发到聊天、Issues、公开仓库或日志中。

## 手动测试

进入：

`Actions -> SB.SB Daily Check-in -> Run workflow`

成功示例：

```text
[INFO] Before: status=pending
[INFO] POST /signin/: HTTP 200
✅ 烧饼论坛（sb.sb）签到成功
```

当天已经签到：

```text
[INFO] Before: status=signed
✅ 烧饼论坛（sb.sb）今日已经签到，无需重复签到
```

## 自动签到时间

sb.sb 论坛规则说明签到日期按 UTC 计算，UTC+8 每天 08:00 更新。

本项目默认：

```yaml
- cron: '17 0 * * *'
```

即：

- UTC：每天 00:17
- 北京时间：每天 08:17

故意错开整点几分钟，减少 GitHub Actions 调度拥堵。

## 403 / 验证

本脚本不会绕过验证码、Cloudflare 或其他站点保护。

如果 GitHub Actions 返回 403：
- 先重新抓 Cookie；
- 如果浏览器正常、Actions 一直 403，可能是站点对 GitHub Runner 出口或会话环境有限制；
- 这时建议改为自己的 VPS / 青龙面板执行。

## 安全建议

- 建议使用 Private 仓库
- Cookie 仅放 GitHub Actions Secrets
- 不要把 Cookie 写进 `main.py` / YAML
- Cookie 泄露后请退出站点会话并重新登录
