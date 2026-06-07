# SSRN ARN Monitor

纯 Python 的 SSRN `Accounting Research Network (ARN)` 监控器。

它每天抓取 ARN 首页，发现分页 API，拉取目标日期的当日新论文，并将命中 `accounting_top3_faculty_top200_2021_2025.csv` 名单的结果写入 Markdown 日报。

## Requirements

- Python 3.11+
- 服务器能访问 `www.ssrn.com` 和 `api.ssrn.com`

## Usage

```bash
python3 monitor.py
python3 monitor.py --date-et 2026-06-04
python3 monitor.py --page-cap 4
```

- 默认目标日期：当前 `America/New_York` 日期减一天
- `--date-et`：补跑指定美东日期
- `--page-cap`：限制最多抓几页，每页 50 篇

## Output

- Markdown 日报：`reports/YYYY-MM-DD.md`

日报只列命中结果；未命中的论文只在摘要里显示统计数。

## Linux Deployment

默认按 Ubuntu/Debian + `systemd timer` 部署。

1. 把仓库放到固定目录，例如 `/opt/ssrn-arn-monitor`
2. 确认系统 Python 版本满足要求
3. 手动试跑一次：

```bash
cd /opt/ssrn-arn-monitor
python3 monitor.py --date-et 2026-06-04
```

4. 安装 systemd 单元：

```bash
sudo cp deploy/systemd/ssrn-monitor.service /etc/systemd/system/
sudo cp deploy/systemd/ssrn-monitor.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ssrn-monitor.timer
```

5. 修改 `ssrn-monitor.service` 中的 `WorkingDirectory` 和 `ExecStart` 为实际路径

## Schedule Notes

- 程序按美东日期取“昨天”，所以定时任务必须在纽约日结束后再运行。
- 如果服务器时区是 UTC，建议在 `05:10 UTC` 之后运行。
- 当前 timer 示例使用 UTC，避免夏令时/冬令时切换带来的本地时区歧义。

## Testing

```bash
python3 -m unittest discover -s tests
```
