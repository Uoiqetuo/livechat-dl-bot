
# livechat-dl-bot

使用 yt-dlp 下載 youtube 聊天室 的 Discord 機器人

## 使用方式

1. 申請 Discord Bot 並取得 Token 後填入 .env 檔案的 `DISCORD_TOKEN` 變數。
2. 在 `機器人` 頁面中啟用 `Message Content Intent` 權限。
2. 在 `OAuth2` 頁面的 OAuth2 URL 產生器中選擇 `bot` 範圍，並勾選 `傳送訊息`、`管理訊息` 和 `附加檔案` 權限。
3. 用步驟 2 產生的連結邀請機器人加入你的 Discord 伺服器。
4. 部屬完成後在 Discord 頻道中使用指令 `!dl [youtube影片網址]` 來下載聊天室內容。

## Local Setup

1. Copy `.env.example` to `.env` and fill in `DISCORD_TOKEN`.
2. Install dependencies with `uv sync`.
3. Run the bot with `uv run python -m app.main`.

## Docker Deployment

### Build and run with Docker Compose

1. Copy `.env.example` to `.env` and set `DISCORD_TOKEN`.
2. Start the service with `docker compose up --build`.
3. Downloaded files are stored in `./downloads` on the host and mirrored inside the container at `/app/downloads`.

### Manual Docker build

Build the image:

```bash
docker build -t livechat-dl-bot .
```

Run it with an env file and a downloads mount:

```bash
docker run --rm \
	--env-file .env \
	-v "$PWD/downloads:/app/downloads" \
	livechat-dl-bot
```
