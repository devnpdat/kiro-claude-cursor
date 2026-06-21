# Setup Guide: Hermes Agent + 9Router (macOS)

> Step-by-step từ đầu. Verified trên macOS với Node v20+, Python 3.10+.

---

## Why Install This?

### 9Router — Local AI Proxy

Vấn đề khi không có 9Router:
- Mỗi AI tool (Claude Code, Cursor, Kiro, Hermes) gọi thẳng provider riêng — không biết tổng token/cost là bao nhiêu
- Một provider down = tool đó chết, phải tay đổi config
- Muốn thử model mới = phải vào từng tool config lại

9Router giải quyết bằng cách làm một điểm trung gian duy nhất:

| Lợi ích | Chi tiết |
|---------|---------|
| Centralized monitoring | Dashboard xem token usage, cost ước tính theo ngày/tuần cho TẤT CẢ tools |
| Auto fallback | Provider A down → tự chuyển sang B, C mà không cần tay đổi gì |
| Tận dụng OAuth quota | Claude Code, Cursor, Kiro đều có free quota qua OAuth — 9Router ưu tiên dùng hết trước khi chạm API key trả tiền |
| Đổi model 1 chỗ | Chỉ cần sửa trong 9Router dashboard, tất cả tools cập nhật ngay |
| Tunnel chia sẻ | Expose endpoint ra ngoài để cả team dùng chung một proxy (qua ngrok/Tailscale) |

Thực tế: combo Claude Code + Cursor + Kiro OAuth giảm đáng kể chi phí so với dùng API key thuần túy, nhưng heavy usage vẫn sẽ tốn tiền (OpenRouter làm fallback). Lợi ích chính là biết chính xác mình đang tốn bao nhiêu và tự động tận dụng free quota trước khi chạm API key trả tiền.

---

### Hermes Agent — AI Agent in the Terminal

So sánh với các tool khác:

| | Claude Code | Cursor/Kiro | Hermes |
|---|---|---|---|
| Chạy ở đâu | Terminal | IDE | Terminal + Telegram + bất kỳ đâu |
| Nhớ giữa sessions | Không | Không | Có (persistent memory) |
| Dùng ngoài IDE | Có | Không | Có |
| Provider | Anthropic only (hoặc custom base_url) | Proprietary | 20+ providers, local model |
| Tự học workflow | Không | Không | Có (skills system) |
| Cron / automation | Có (/schedule + extensions) | Hạn chế | Có (built-in cron, webhook) |
| Messaging platforms | Không | Không | Có (Telegram, Discord, Slack...) |

Lợi ích thực tế:

| Lợi ích | Chi tiết |
|---------|---------|
| Dùng được mọi lúc mọi nơi | Chat qua Telegram khi không ở máy, Hermes vẫn chạy task trên máy tính |
| Nhớ context dài hạn | Biết bạn là ai, project đang làm gì — không cần giải thích lại mỗi lần |
| Skills tự học | Khi giải được vấn đề phức tạp, tự lưu lại thành skill để lần sau làm nhanh hơn |
| Không phụ thuộc IDE | Debug, review code, chạy task ngay trong terminal mà không cần mở IDE |
| Tích hợp MCP | Connect với GitLab, Confluence, Playwright... qua MCP server |
| Cron automation | Schedule task chạy định kỳ — VD: mỗi sáng tóm tắt PR mới, alert khi build fail |
| Provider linh hoạt | Trỏ vào 9Router = tận dụng OAuth quota, hoặc đổi model bất kỳ lúc nào |

Combo Hermes + 9Router: Hermes có AI mạnh (qua 9Router routing đến model tốt nhất available), lại có memory + automation — về cơ bản là một AI agent cá nhân chạy 24/7.

---

## Architecture Overview

```
Claude Code ──┐
Cursor        ├──► 9Router (localhost:20128) ──► Claude Code OAuth
Kiro          │         ↓ fallback              ► Cursor OAuth
Hermes ───────┘    dashboard/monitor            ► Kiro OAuth
                                                ► OpenRouter (API key)
```

9Router là local proxy expose OpenAI-compatible API. Tất cả AI tools trỏ vào đây thay vì gọi thẳng provider. Hermes dùng `openai-api` provider với `base_url = http://localhost:20128/v1`.

---

## PART 0 — Prerequisites

### Homebrew (package manager for macOS)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Verify:
```bash
brew --version  # Homebrew 4.x
```

### Node.js (required for 9Router)

Yêu cầu: Node v20 trở lên.

```bash
brew install node
```

Verify:
```bash
node --version  # v20.x hoặc cao hơn
npm --version   # v10.x hoặc cao hơn
```

Nếu đã có Node cũ hơn v20, nâng lên:
```bash
brew upgrade node
```

### Python (required for Hermes)

Yêu cầu: Python 3.10 trở lên.

```bash
brew install python@3.12
```

Verify:
```bash
python3 --version  # Python 3.10.x hoặc cao hơn
```

> Nếu máy đã có Python 3.10+ thì bỏ qua bước này.

---

## PART 1 — Install 9Router

### Step 1: Install via npm

```bash
npm install -g 9router
```

Verify:
```bash
9router --version
which 9router  # /opt/homebrew/bin/9router
```

### Step 2: First run to initialize config

```bash
9router
```

Mở browser vào `http://localhost:20128/dashboard` để vào UI.

### Step 3: Setup providers in the dashboard

Vào **Settings → Providers**, thêm lần lượt:

| Provider | Loại | Ghi chú |
|----------|------|---------|
| Claude Code | OAuth | Login bằng Anthropic account |
| Cursor | OAuth | Login bằng Cursor account |
| Kiro | OAuth | Login bằng AWS Builder ID |
| OpenRouter | API Key | Fallback cuối, pay-per-use — lấy key tại openrouter.ai |

Với OAuth providers: click **Connect** → browser mở → đăng nhập → authorize.

### Step 4: Create a Combo model

Vào **Models → New Model**:

- Name: `Combo-Company`
- Type: **Fallback** (hoặc Round-robin tuỳ ý)
- Thứ tự: Claude Code → Cursor → Kiro → OpenRouter

Lưu lại.

### Step 5: Create an API Key (required if using Tunnel)

Vào **Settings → API Keys → Generate**.
Lưu key lại ngay — không xem lại được sau khi đóng dialog.
Format: `9r-xxxxxxxxxxxx`

### Step 6: Auto-start 9Router on boot (launchd)

Kiểm tra đường dẫn node trước:
```bash
which node   # thường là /opt/homebrew/bin/node
```

Tạo plist (thay đường dẫn node nếu khác):
```bash
cat > ~/Library/LaunchAgents/com.9router.autostart.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.9router.autostart</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/node</string>
        <string>/opt/homebrew/lib/node_modules/9router/cli.js</string>
        <string>--tray</string>
        <string>--skip-update</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>/tmp/9router.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/9router.error.log</string>
</dict>
</plist>
EOF

launchctl load ~/Library/LaunchAgents/com.9router.autostart.plist
```

Verify đang chạy:
```bash
curl http://localhost:20128/v1/models
```

---

## PART 2 — Install Hermes Agent

### Step 1: Install Hermes

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

Sau khi cài xong, mở terminal mới:
```bash
hermes --version
```

### Step 2: Configure Hermes to point to 9Router

Cách nhanh nhất dùng CLI:
```bash
hermes model
```
Chọn **OpenAI API** → nhập:
- Base URL: `http://localhost:20128/v1`
- Model: `Combo-Company` (tên model đã tạo ở Bước 4)
- API Key: key 9Router đã tạo ở Bước 5 (để trống nếu không bật Require API key)

Hoặc edit thẳng config:
```bash
hermes config edit
```

```yaml
# ~/.hermes/config.yaml
model:
  provider: openai-api
  base_url: http://localhost:20128/v1
  default: Combo-Company
```

Thêm API key vào .env:
```bash
echo 'OPENAI_API_KEY=9r-xxxxxxxxxxxx' >> ~/.hermes/.env
```

### Step 3: Test Hermes

```bash
hermes chat -q "hello, mày là ai?"
```

Nếu có response = OK.

### Step 4: Setup Telegram Bot (optional)

1. Mở Telegram → tìm **@BotFather** → gõ `/newbot` → đặt tên → lấy token
2. Tìm **@userinfobot** → gõ `/start` → lấy user ID của mình

```bash
hermes gateway setup
```

Chọn **Telegram** → nhập bot token → nhập user ID.

Thêm vào `~/.hermes/.env`:
```
TELEGRAM_BOT_TOKEN=<token từ BotFather>
TELEGRAM_ALLOWED_USERS=<user_id của mày>
TELEGRAM_HOME_CHANNEL=<user_id của mày>
```

### Step 5: Auto-start Hermes Gateway on boot

```bash
hermes gateway install
```

Lệnh này tự tạo plist tại `~/Library/LaunchAgents/ai.hermes.gateway.plist` và load luôn.

Verify:
```bash
hermes gateway status
```

---

## PART 3 — Configure Other AI Tools to Use 9Router

### Claude Code

```bash
# Thêm vào ~/.zshrc
export ANTHROPIC_BASE_URL="http://localhost:20128/v1"
export ANTHROPIC_API_KEY="9r-xxxxxxxxxxxx"
```

Sau đó: `source ~/.zshrc`

### Cursor

Settings → Models → OpenAI API Key: `9r-xxxxxxxxxxxx`
Base URL: `http://localhost:20128/v1`
Toggle ON model muốn dùng.

### Kiro (AWS)

Settings → AI Provider → Custom → Base URL: `http://localhost:20128/v1`
API Key: `9r-xxxxxxxxxxxx`

---

## PART 4 — Token Refresh When OAuth Expires

9Router lưu OAuth token của các providers. Token có thời hạn (~30 ngày với Kiro/Claude Code).
Khi token hết hạn:

1. Vào `localhost:20128/dashboard` → Providers
2. Click **Reconnect** provider bị lỗi → re-authorize qua browser

---

## PART 5 — Verify Everything Works

```bash
# 1. 9Router đang chạy
curl http://localhost:20128/v1/models | python3 -m json.tool

# 2. Hermes gọi được qua 9Router
hermes chat -q "1+1=?"

# 3. Gateway Telegram online
hermes gateway status

# 4. Check logs nếu có lỗi
tail -f ~/.hermes/logs/gateway.log
tail -f /tmp/9router.log
```

Dashboard monitor token usage: `http://localhost:20128/dashboard`

---

## Common Troubleshooting

| Triệu chứng | Nguyên nhân | Fix |
|-------------|-------------|-----|
| `curl localhost:20128` timeout | 9Router chưa chạy | `9router` hoặc `launchctl start com.9router.autostart` |
| Hermes báo model not found | Tên model sai | Kiểm tra tên đúng trong 9Router dashboard → sửa `config.yaml` |
| Gateway Telegram không nhận tin | plist PATH sai | Kiểm tra `which python3` khớp với plist |
| 9Router OAuth token expired | Token hết hạn ~30 ngày | Reconnect provider trong dashboard |
| Tunnel không enable được | Chưa có API key | Tạo API key trước → bật Require API Key → Enable Tunnel |
| Hermes gateway crash loop | Port conflict hoặc lỗi config | `hermes gateway status` + xem log |
| `npm install -g 9router` lỗi permission | npm global dir không có quyền | `sudo npm install -g 9router` hoặc dùng nvm |
| `hermes` command not found sau cài | Shell chưa reload | Mở terminal mới hoặc `source ~/.zshrc` |

---

## Important Files Summary

```
~/.hermes/config.yaml                              # Hermes config chính
~/.hermes/.env                                     # API keys
~/.hermes/logs/gateway.log                         # Hermes gateway log
~/Library/LaunchAgents/ai.hermes.gateway.plist     # Hermes auto-start
~/Library/LaunchAgents/com.9router.autostart.plist # 9Router auto-start
~/.9router/db/data.sqlite                          # 9Router usage DB
/tmp/9router.log                                   # 9Router log
```
