<!-- Header Section -->
<div align="center">

# 🌌 PROJECT-X
## The Ultimate Multi-Cloud Telegram Leech & Mirror Bot

<p align="center">
    <a href="https://github.com/Sourovislam637/Project-X">
        <kbd>
            <img src="https://i.ibb.co/zTHm92cG/image.jpg" width="600" alt="Project-X Dynamic Banner">
        </kbd>
    </a>
</p>

<!-- GitHub Stat Badges -->
<p align="center">
  <a href="https://github.com/Sourovislam637/Project-X/fork">
    <img alt="Forks" src="https://img.shields.io/github/forks/Sourovislam637/Project-X?style=for-the-badge&logo=git&color=FF6F00&labelColor=1a1a1a">
  </a> 
  <a href="https://github.com/Sourovislam637/Project-X/stargazers">
    <img alt="Stars" src="https://img.shields.io/github/stars/Sourovislam637/Project-X?style=for-the-badge&logo=github&color=FFD700&labelColor=1a1a1a">
  </a>
  <a href="https://github.com/Sourovislam637/Project-X/issues">
    <img alt="Issues" src="https://img.shields.io/github/issues/Sourovislam637/Project-X?style=for-the-badge&logo=github&color=FF4500&labelColor=1a1a1a">
  </a>
  <a href="https://github.com/Sourovislam637/Project-X/blob/main/LICENSE">
    <img alt="License" src="https://img.shields.io/github/license/Sourovislam637/Project-X?style=for-the-badge&logo=open-source-initiative&color=00BFFF&labelColor=1a1a1a">
  </a>
</p>

<!-- Author Badges -->
<p align="center">
  <a href="https://github.com/Sourov-Nobita">
    <img alt="Creator" src="https://img.shields.io/badge/Creator-Sourov__Nobita-8A2BE2?style=for-the-badge&logo=github&labelColor=1a1a1a">
  </a>
  <a href="https://t.me/Sourov_Nobita">
    <img alt="Owner Telegram" src="https://img.shields.io/badge/Contact-Telegram-0088CC?style=for-the-badge&logo=telegram&logoColor=white&labelColor=1a1a1a">
  </a>
</p>

<!-- Channel Badges -->
<p align="center">
  <a href="https://t.me/Rare_Bots_Hub">
    <img alt="Update Channel" src="https://img.shields.io/badge/Powered_By-Rare_Bots_Hub-28A745?style=for-the-badge&logo=telegram&logoColor=white&labelColor=1a1a1a">
  </a>
  <a href="https://t.me/Rare_Leech_Mirror_Hub">
    <img alt="Leech Mirror Channel" src="https://img.shields.io/badge/Official_Group-Leech_Mirror_Hub-FFC107?style=for-the-badge&logo=telegram&logoColor=black&labelColor=1a1a1a">
  </a>
</p>

<br>

> #### ⚡️ *Download Anything. Upload Everywhere. Effortlessly.* 🔥

<a href="https://colab.research.google.com/drive/1ntoqoj3jDq2FtU2-joizh0DO64uoec9q">
  <img src="https://img.shields.io/badge/Deploy%20on-Google%20Colab-F9AB00?style=for-the-badge&logo=googlecolab&logoColor=white" alt="Deploy on Google Colab">
</a>

<br><br>

</div>

---

## 📖 Introduction

**Project-X** is an advanced, high-performance, and feature-rich Telegram Bot built for seamless file downloading, mirroring, and leeching. Designed with optimal async processing, it can handle heavy workloads reliably 24/7. Whether you want to download a massive torrent, fetch a direct link, or mirror a file to your cloud drive—Project-X has got you covered!

---

## ✨ Outstanding Features

Project-X comes packed with an array of premium features designed to give you ultimate control over your file management.

<details>
<summary><b>🛠️ Click to Reveal All Features</b></summary>

### 🌐 The Ultimate Downloader
- **Torrent Support**: Download magnet links, `.torrent` files with ultra-fast speed using qBittorrent / aria2.
- **Direct Links**: Lightning-fast downloading for direct file links.
- **yt-dlp Integration**: Download audio, video, or playlists from YouTube and 1000+ other supported platforms.
- **Mega & GDrive**: Fetch files natively from Mega.nz and Google Drive.

### ☁️ Multi-Cloud Uploader
- **Telegram Cloud**: Leech files directly to Telegram as documents or media (up to 4GB with premium).
- **Google Drive**: Seamlessly mirror files to your personal GDrive or Shared Drives.
- **Rclone Integration**: Upload to hundreds of cloud storages (OneDrive, Dropbox, etc.) natively.
- **DDL Servers**: Push files directly to your preferred Direct Download links servers.

### 🧠 Smart File Processing
- **Metadata Management**: Automatically rename, tag, and organize files based on extensions.
- **Thumbnail Support**: Custom thumbnails for media files uploaded to Telegram.
- **Archive Extractor**: Automatically extract `.zip`, `.rar`, `.tar`, and `.7z` files.
- **Archive Creator**: Compress folders and files on the go before uploading.

### ⚙️ Automation & Reliability
- **Auto-resume**: Resumes interrupted tasks flawlessly.
- **Task Scheduling**: Queue management for heavy traffic, ensuring smooth operations.
- **Auto-Cleanup**: Intelligently cleans up server space after successful uploads.

### 🛡️ Admin & Security Controls
- **Owner Only Mode**: Restrict bot usage strictly to the owner.
- **Authorized Chats**: Whitelist specific groups or users to use the bot.
- **Interactive UI**: Manage everything via dynamic Telegram inline buttons (`/bs`, `/settings`).

</details>

---

## 🛠️ Infrastructure & Requirements

Before you deploy the bot, make sure you have the following ready:

| Requirement | Description | Status |
| :--- | :--- | :---: |
| **Telegram API ID & Hash** | Get it from [my.telegram.org](https://my.telegram.org/) | 🟢 |
| **Telegram Bot Token** | Create a bot via [@BotFather](https://t.me/BotFather) | 🟢 |
| **MongoDB URI** | Required for database & storing settings ([MongoDB Atlas](https://www.mongodb.com/)) | 🟢 |
| **Server/VPS** | Minimum 1GB RAM, Ubuntu 20.04+ recommended | 🟡 |
| **Docker** | For seamless deployment on VPS/Servers | 🟡 |

---

## 🚀 Deployment Guide (VPS / Dedicated Server)

Deploying on a VPS is the most reliable way to run Project-X. We highly recommend using Docker for this.

<details>
<summary><b>💻 Expand for Detailed VPS Setup Guide</b></summary>

### 📌 Step 1: Initial Preparation

**Video Tutorial (Highly Recommended)**  
*Thanks to [Wiszky](https://github.com/vishnoe115) for the detailed walkthrough!*  
[![Watch Video Tutorial](https://img.shields.io/badge/Watch_VPS_Tutorial-FF0000?style=for-the-badge&logo=YouTube&logoColor=white)](https://youtu.be/xzLOLyKYl54)

### 📌 Step 2: Clone the Repository

Log in to your server terminal (SSH) and run:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install git -y
git clone [https://github.com/Sourovislam637/Project-X](https://github.com/Sourovislam637/Project-X) project-x
cd project-x
```

### 📌 Step 3: Configure Environment Variables

You need to set up the `config.env` file.
```bash
cp config_sample.env config.env
nano config.env
```
* **IMPORTANT**: Remove the first line (`_____REMOVE_THIS_LINE_____=True`).
* Fill in all the variables carefully. All values must be inside quotes `""`.
* Press `CTRL + X`, then `Y`, then `ENTER` to save and exit.

### 📌 Step 4: Build & Run via Docker (Recommended)

Make sure Docker and Docker-Compose are installed on your system.

**Method A: Using Docker Compose** (Best for easy management)
```bash
sudo apt install docker-compose -y
# Build and Start the bot in detached mode
sudo docker-compose up -d --build
```
*To stop the bot:*
```bash
sudo docker-compose down
```
*To view live logs:*
```bash
sudo docker-compose logs -f
```

**Method B: Using Standard Docker Commands**
```bash
# Build the image
sudo docker build . -t projectx
# Run the image
sudo docker run -d -p 80:80 -p 8080:8080 projectx
```

> **Note on Ports:** If you need to change the default ports, modify the `BASE_URL_PORT` (default `80`) and `RCLONE_SERVE_PORT` (default `8080`) in your config and `docker-compose.yml`.

</details>

---

## ☁️ Deployment Guide (Heroku CLI)

Deploying to Heroku is a great free/cheap alternative.

<details>
<summary><b>🚀 Expand for Detailed Heroku Setup Guide</b></summary>

### 📌 Step 1: Install Dependencies
You need `git` and `curl` installed on your local machine or Termux (Android).
```bash
git clone [https://github.com/Sourovislam637/Project-X](https://github.com/Sourovislam637/Project-X) project-x
cd project-x
```

### 📌 Step 2: Install Heroku CLI
For Ubuntu/Debian or Termux:
```bash
curl [https://cli-assets.heroku.com/install.sh](https://cli-assets.heroku.com/install.sh) | sh
```

### 📌 Step 3: Login to Heroku
```bash
heroku login -i
```
Enter your Heroku Email and Heroku API Key (found in Heroku account settings) when prompted.

### 📌 Step 4: Create Heroku App
```bash
heroku create --region us --stack container YOUR_APP_NAME
```
*Take note of the URL provided here, you will need it for the `BASE_URL` variable.*

### 📌 Step 5: Setup Configuration
```bash
nano config.env
```
Ensure you have the minimum required variables set:
```env
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
TELEGRAM_API = "YOUR_API_ID_HERE"
TELEGRAM_HASH = "YOUR_API_HASH_HERE"
OWNER_ID = "YOUR_TELEGRAM_ID"
DATABASE_URL = "YOUR_MONGODB_URI"
BASE_URL = "[https://your-app-name.herokuapp.com/](https://your-app-name.herokuapp.com/)"
SET_COMMANDS = "True"
UPSTREAM_REPO = "[https://github.com/Sourovislam637/Project-X](https://github.com/Sourovislam637/Project-X)"
UPSTREAM_BRANCH = "main"
```

### 📌 Step 6: Deploy to Heroku
```bash
git add . -f
git commit -m "Initial Heroku Deployment"
heroku git:remote -a YOUR_APP_NAME
git push heroku main -f
```

### 📌 Step 7: Check Logs
To ensure the bot is running properly:
```bash
heroku logs -a YOUR_APP_NAME --tail
```

</details>

---

## ⚙️ Environment Variables Dictionary

Understanding the configuration file is crucial for bot stability.

<details>
<summary><b>📝 Expand for Full Variable Descriptions</b></summary>

### Mandatory Variables
- `BOT_TOKEN`: Your Telegram Bot Token. Obtain from [@BotFather](https://t.me/BotFather).
- `OWNER_ID`: Your personal Telegram User ID (integer). 
- `TELEGRAM_API`: Your Telegram API ID from [my.telegram.org](https://my.telegram.org).
- `TELEGRAM_HASH`: Your Telegram API Hash from [my.telegram.org](https://my.telegram.org).

### Connection Variables
- `BASE_URL`: 
  - **VPS:** `http://YOUR_IP` (or `http://YOUR_IP:PORT` if not using 80).
  - **Heroku:** `https://appname.herokuapp.com/`.
- `DATABASE_URL`: MongoDB URI connection string. Extremely recommended for storing user sessions, settings, and stats.

### Upstream Variables
- `UPSTREAM_REPO`: `https://github.com/Sourovislam637/Project-X` (This keeps your bot updated).
- `UPSTREAM_BRANCH`: Leave as `main`.

### Optional (But Recommended) Features
- `AUTHORIZED_CHATS`: List of chat IDs (space separated) allowed to use the bot.
- `SUDO_USERS`: List of user IDs that act as admins.
- `IS_PREMIUM_USER`: If the bot session uses a premium account for 4GB upload limits.
- `RSS_DELAY`: Interval for RSS feed checks.

*(Refer to the repository's `config_sample.env` for all advanced variables)*

</details>

---

## 🤝 Community & Support

We believe in open-source collaboration! If you encounter issues, have feature requests, or just want to hang out with other users, connect with us through our official channels.

<div align="center">

| Official Platforms | Links |
| :---: | :--- |
| **🗣️ Updates Channel** | [Join @Rare_Bots_Hub](https://t.me/Rare_Bots_Hub) |
| **📁 Mirror Channel** | [Join @Rare_Leech_Mirror_Hub](https://t.me/Rare_Leech_Mirror_Hub) |
| **💻 Main Repository** | [Project-X on GitHub](https://github.com/Sourovislam637/Project-X) |

</div>

---

## 📜 Legal & Disclaimer

- **Project-X** is an open-source project provided "as is" without warranty of any kind.
- The developers (Sourov Nobita & contributors) are **not responsible** for any misuse of this software. Users are strictly advised to adhere to their respective local laws regarding copyright and data distribution.
- **Do not use this bot to pirate or distribute copyrighted material illegally.**

---
<div align="center">
    <b>Made with ❤️ by <a href="https://github.com/Sourov-Nobita">Sourov Nobita</a></b><br>
    <i>Thank you for choosing Project-X! Don't forget to ⭐ star this repository!</i>
</div>
