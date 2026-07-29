# 🤖 404 Bot

A professional Telegram bot built with aiogram 3.x, featuring comprehensive admin panel and user management system.

## ✨ Features

### User Features
- ✅ /start, /help, /ping commands
- 📊 Profile with referral system
- 📝 Feedback system
- 📨 Contact admin
- 🔗 Referral system
- 📢 Auto welcome message
- 🔒 Force subscribe (on/off)
- ⚡ Custom auto reply
- 🛡️ Spam protection
- 🚫 Bad word filter

### Admin Features
- 👑 Admin panel with inline keyboard
- 📊 Total users & today users
- 📢 Broadcast (text, photo, video, document, animation)
- 📈 Broadcast progress & logs
- 🔍 Search user by ID
- 🚫 Ban/Unban users
- 📨 Send message to any user
- 📝 Set welcome message
- ⚙️ Set auto reply
- 🔒 Enable/Disable features
- 💾 Database backup
- 📊 Export users CSV
- 📈 Bot statistics
- ⏱ Uptime monitoring
- 🔄 Restart bot
- 🔧 Maintenance mode

## 🚀 Deployment

### Local Deployment
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create `.env` file with your `BOT_TOKEN` and `OWNER_ID`
4. Run: `python main.py`

### Termux Deployment
```bash
pkg install python
pip install -r requirements.txt
python main.py
