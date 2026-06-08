# SSRN ARN Monitor

纯 Python 的 SSRN `Accounting Research Network (ARN)` 监控器，默认部署在 `GitHub Actions` 上按天运行。

它每天抓取 ARN 首页，发现分页 API，拉取目标日期的当日新论文，并将命中内嵌的 200 位会计学者监控名单的结果写入 Markdown 日报。

## Requirements

- Python 3.11+
- 运行环境能访问 `www.ssrn.com` 和 `api.ssrn.com`

## Usage

```bash
python3 monitor.py
python3 monitor.py --date-et 2026-06-04
python3 monitor.py --page-cap 4
python3 monitor.py --api-url https://api.ssrn.com/content/v1/bindings/204/papers
```

- 默认目标日期：当前 `America/New_York` 日期减一天
- `--date-et`：补跑指定美东日期
- `--page-cap`：限制最多抓几页，每页 50 篇
- `--api-url`：直接指定 ARN API，跳过首页发现

## Output

- Markdown 日报：`reports/YYYY-MM-DD.md`

日报只列命中结果；未命中的论文只在摘要里显示统计数。
如果 SSRN 首页对服务器返回 `403`，程序会自动回退到默认 ARN API，不会因为首页发现失败而退出。
如果连 `api.ssrn.com` 也返回 `403`，通常说明 SSRN 在拦截当前运行环境的出口 IP；这时需要更换运行环境，或给进程配置代理。

## GitHub Actions Deployment

仓库已包含工作流：`.github/workflows/daily-monitor.yml`

默认行为：

- 每天 `05:15 UTC` 自动运行一次
- 也支持在 GitHub Actions 页面手动触发
- 运行前先执行单测
- 成功后把 `reports/*.md` 作为 artifact 上传
- 如果报告有更新，会自动提交回仓库

启用方式：

1. 把代码推到 GitHub 仓库默认分支
2. 在仓库 `Settings -> Actions -> General` 中确认 Actions 已启用，并允许 workflow 读写仓库内容
3. 在 `Actions` 页面找到 `Daily SSRN Monitor` 工作流
4. 可直接点击 `Run workflow` 手动测试一次

## Schedule Notes

- 程序按美东日期取“昨天”，所以定时任务必须在纽约日结束后再运行。
- 当前 workflow 使用 `05:15 UTC`，避免夏令时/冬令时切换带来的本地时区歧义。

## Testing

```bash
python3 -m unittest discover -s tests
```
