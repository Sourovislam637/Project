<div align="center">

<!-- Logo and Title -->
<img src="https://i.ibb.co/zTHm92cG/image.jpg" width="600" alt="Project-X Dynamic Banner" style="border-radius: 15px; box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.5);">

# 🚀 PROJECT-X
### *The Ultimate Multi-Cloud Telegram Leech & Mirror Engine*

<!-- Dynamic Badges -->
<p align="center">
  <a href="https://github.com/Sourovislam637/Project-X/stargazers">
    <img alt="Stars" src="https://img.shields.io/github/stars/Sourovislam637/Project-X?style=for-the-badge&logo=github&color=FFD700&labelColor=2a2a2a">
  </a>
  <a href="https://github.com/Sourovislam637/Project-X/fork">
    <img alt="Forks" src="https://img.shields.io/github/forks/Sourovislam637/Project-X?style=for-the-badge&logo=git&color=FF6F00&labelColor=2a2a2a">
  </a>
  <a href="https://github.com/Sourovislam637/Project-X/issues">
    <img alt="Issues" src="https://img.shields.io/github/issues/Sourovislam637/Project-X?style=for-the-badge&logo=github&color=FF4500&labelColor=2a2a2a">
  </a>
</p>

<!-- Quick Action Buttons -->
<p align="center">
  <a href="https://t.me/Rare_Bots_Hub">
    <img alt="Update Channel" src="https://img.shields.io/badge/Official_Updates-Rare_Bots_Hub-0088CC?style=for-the-badge&logo=telegram&logoColor=white&labelColor=1a1a1a">
  </a>
  <a href="https://t.me/Rare_Leech_Mirror_Hub">
    <img alt="Leech Mirror Channel" src="https://img.shields.io/badge/Official_Group-Leech_Mirror_Hub-0A3D62?style=for-the-badge&logo=telegram&logoColor=white&labelColor=1a1a1a">
  </a>
</p>

<!-- Deploy Button -->
<p align="center">
  <a href="https://colab.research.google.com/drive/1ntoqoj3jDq2FtU2-joizh0DO64uoec9q">
    <img src="https://img.shields.io/badge/Deploy%20Now%20on-Google%20Colab-F9AB00?style=for-the-badge&logo=googlecolab&logoColor=white&labelColor=1a1a1a" alt="Deploy on Google Colab">
  </a>
</p>

> #### ⚡️ *Download Anything. Upload Everywhere. Seamlessly Automated.* 🔥

</div>

<br>

---

## 🌟 Introduction

**Project-X** is an advanced, high-performance Telegram Bot built to revolutionize file management. Whether it's heavy torrents, direct links, or cloud drives, Project-X handles everything with optimal async processing, ensuring 24/7 stability and lightning-fast speed.

---

## ✨ Features at a Glance

<details>
<summary><b>🛠️ Click Here to Reveal All Powerful Features</b></summary>
<br>

**🌐 The Ultimate Downloader**
- **Torrent Support**: Download magnet links and `.torrent` files with blazing fast speed (qBittorrent / aria2).
- **Direct Links**: Lightning-fast downloading for direct file links.
- **yt-dlp Integration**: Download audio, video, or playlists from YouTube and 1000+ other supported platforms.
- **Mega & GDrive**: Fetch files natively from Mega.nz and Google Drive.

**☁️ Multi-Cloud Uploader**
- **Telegram Cloud**: Leech files directly to Telegram as documents or media (up to 4GB with premium).
- **Google Drive**: Seamlessly mirror files to your personal GDrive or Shared Drives.
- **Rclone Integration**: Upload to hundreds of cloud storages (OneDrive, Dropbox, etc.) natively.
- **DDL Servers**: Push files directly to your preferred Direct Download links servers.

**🧠 Smart File Processing**
- **Metadata Management**: Automatically rename, tag, and organize files based on extensions.
- **Thumbnail Support**: Custom thumbnails for media files uploaded to Telegram.
- **Archive Extraction & Creation**: Extract `.zip`, `.rar`, `.tar`, and `.7z` files, or compress folders on the go.

**⚙️ Automation & Security**
- **Auto-resume & Auto-Cleanup**: Intelligent resuming of interrupted tasks and server space management.
- **Owner Only & Whitelisting**: Strict access control via interactive UI (`/bs`, `/settings`).

</details>

---

## 🛠️ Infrastructure & Requirements

Before deployment, ensure you have the following prerequisites ready:

| Requirement | Description | Status |
| :--- | :--- | :---: |
| **API ID & Hash** | Obtain from [my.telegram.org](https://my.telegram.org/) | 🟢 |
| **Bot Token** | Create a bot via [@BotFather](https://t.me/BotFather) | 🟢 |
| **MongoDB URI** | Database for settings ([MongoDB Atlas](https://www.mongodb.com/)) | 🟢 |
| **Server/VPS** | Minimum 1GB RAM, Ubuntu 20.04+ recommended | 🟡 |
| **Docker** | For seamless deployment on VPS/Servers | 🟡 |

---

## 🚀 VPS Deployment (Docker Recommended)

<details>
<summary><b>💻 Expand for Detailed VPS Setup Guide</b></summary>
<br>

**1. Clone the Repository:**
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install git docker-compose -y
git clone [https://github.com/Sourovislam637/Project-X](https://github.com/Sourovislam637/Project-X) project-x && cd project-x
```

**2. Setup Environment Variables:**
```bash
cp config_sample.env config.env
nano config.env
```
*(Remove the first line `_____REMOVE_THIS_LINE_____=True` and fill in your details)*

**3. Build & Run (Docker Compose):**
```bash
sudo docker-compose up -d --build
```
*(To stop: `sudo docker-compose down` | To check logs: `sudo docker-compose logs -f`)*

**Video Tutorial (Highly Recommended):**  
[![Watch Video Tutorial](https://img.shields.io/badge/Watch_VPS_Tutorial-FF0000?style=for-the-badge&logo=YouTube&logoColor=white)](https://youtu.be/xzLOLyKYl54)

</details>

---

## ☁️ Heroku Deployment

<details>
<summary><b>🚀 Expand for Detailed Heroku Setup Guide</b></summary>
<br>

**1. Install Dependencies & Clone:**
```bash
curl [https://cli-assets.heroku.com/install.sh](https://cli-assets.heroku.com/install.sh) | sh
git clone [https://github.com/Sourovislam637/Project-X](https://github.com/Sourovislam637/Project-X) project-x && cd project-x
```

**2. Login & Create App:**
```bash
heroku login -i
heroku create --region us --stack container YOUR_APP_NAME
```

**3. Configure Variables:**
```bash
nano config.env
```
*(Fill in `BOT_TOKEN`, `TELEGRAM_API`, `TELEGRAM_HASH`, `OWNER_ID`, `DATABASE_URL`, and `BASE_URL`)*

**4. Deploy:**
```bash
git add . -f
git commit -m "Heroku Setup"
heroku git:remote -a YOUR_APP_NAME
git push heroku main -f
```
*(Check logs: `heroku logs -a YOUR_APP_NAME --tail`)*

</details>

---

## ⚙️ Core Environment Variables

<details>
<summary><b>📝 Expand for Variable Descriptions</b></summary>
<br>

- `BOT_TOKEN`: Your Telegram Bot Token from @BotFather.
- `OWNER_ID`: Your Telegram User ID.
- `TELEGRAM_API` & `TELEGRAM_HASH`: Credentials from my.telegram.org.
- `BASE_URL`: The URL where the bot is hosted (e.g., Heroku App URL or VPS IP).
- `DATABASE_URL`: MongoDB connection string.
- `UPSTREAM_REPO`: `https://github.com/Sourovislam637/Project-X`
- `UPSTREAM_BRANCH`: `main`

*(Refer to `config_sample.env` for advanced options like `AUTHORIZED_CHATS` and `SUDO_USERS`)*

</details>

---

## 👨‍💻 Credits & Connections

A massive thanks to everyone who helped shape this project! 

<div align="center">

### 👑 Project Creator & Owner
<a href="https://t.me/Sourov_Nobita">
  <img alt="Owner Telegram" src="https://img.shields.io/badge/Sourov_Nobita-Telegram-0088CC?style=for-the-badge&logo=telegram&logoColor=white&labelColor=1a1a1a">
</a>
<a href="https://github.com/Sourov-Nobita">
  <img alt="Owner GitHub" src="https://img.shields.io/badge/Sourov__Nobita-GitHub-181717?style=for-the-badge&logo=github&logoColor=white&labelColor=1a1a1a">
</a>

<br><br>

### 🔗 Official Source Code
<a href="https://github.com/Sourovislam637/Project-X">
  <img alt="Source Repo" src="https://img.shields.io/badge/Repository-Project--X-8A2BE2?style=for-the-badge&logo=github&logoColor=white&labelColor=1a1a1a">
</a>

</div>

---
<div align="center">
    <b>Crafted with ❤️ by <a href="https://github.com/Sourov-Nobita">Sourov Nobita</a></b><br>
    <i>If this project helped you, please consider giving it a ⭐ Star!</i>
</div>
