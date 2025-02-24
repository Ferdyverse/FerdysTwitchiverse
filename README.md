# Ferdy’s Twitchiverse

**Ferdy’s Twitchiverse** is a **FastAPI-based** application that bridges Twitch interactions with your local network setup. It’s a **Twitchy pocket universe** designed for **real-time engagement**, supporting **dynamic overlays, automated printing**, and **custom event handling** to enhance your stream.

---

⚠️ **Work in Progress**
This project is evolving rapidly, and due to the time I’m investing in development, the documentation might be out of date. I will update it once the core features are finalized.

---

## 🚀 Features

- **🖨️ Print System** – Print headlines, messages, and images on a **thermal printer** (ESC/POS).
- **🎬 Dynamic Overlays** – Modify OBS overlays **in real-time** with alerts, animations, and custom events.
- **📡 WebSocket Integration** – Enables **live communication** between Twitch events and the frontend.
- **🔧 Automated Printer Handling** – Automatically reconnects when the printer goes offline.
- **📜 API Documentation** – Interactive API testing via **Swagger UI**.
- **🛠️ Modular & Scalable** – Clean, structured codebase designed for **expandability**.

---

## 📌 Requirements

- **Python** 3.8+
- A **compatible ESC/POS thermal printer**
- Installed libraries: `fastapi`, `uvicorn`, `escpos`, `PIL` (Pillow), `requests`
- **System dependency:**
  Install `libcups2-dev` (required for printer handling)
  _Debian/Ubuntu:_
  ```bash
  sudo apt install libcups2-dev
  ```

---

## 📥 Installation

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/Ferdyverse/FerdysTwitchiverse.git
cd FerdysTwitchiverse
```

### 2️⃣ Install Dependencies

Set up a **virtual environment** and install required packages:

```bash
python -m venv env
source env/bin/activate  # Windows: .\env\Scripts\activate
pip install -r requirements.txt
```

### 3️⃣ Configure the Application

Modify the `config.py` file with your settings:

```python
# config.py
APP_HOST = "0.0.0.0"
APP_PORT = 8000
APP_LOG_LEVEL = "debug"

PRINTER_VENDOR_ID = 0x04b8  # Example: Epson
PRINTER_PRODUCT_ID = 0x0e15
PRINTER_IN_EP = 0x82
PRINTER_OUT_EP = 0x01
PRINTER_PROFILE = "default"
```

---

## ▶ Running the Application

### 🛠 Development Mode (Auto-Reload)

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 🚀 Production Mode

```bash
python main.py
```

---

## Twitch CLI

```
twitch-cli mock-api start

twitch-cli event websocket start -p 8081
```

---

## 🔗 API Endpoints

Once the app is running, open your browser and visit:

📜 **Swagger Docs:**
➡ **`http://localhost:8000/docs`** – Interactive API testing
🛠 **Redoc Docs:**
➡ **`http://localhost:8000/redoc`** – Alternative API reference

---

## 📂 Project Structure

```
.
├── main.py                     # Application entry point
├── modules/
│   ├── twitch_api.py           # Handles Twitch API interactions
│   ├── printer_manager.py      # Manages thermal printer
│   ├── obs_api.py              # OBS WebSocket integration
│   ├── db_manager.py           # Database management
│   ├── schemas.py              # API request/response models
├── templates/
│   └── overlay.html            # HTML for browser-based overlays
├── static/
│   ├── css/                    # Stylesheets
│   ├── js/                     # JavaScript files
├── config.py                   # Configuration settings
├── README.md                   # Project documentation
└── requirements.txt            # Required Python dependencies
```

---

## 🎭 Contributing

Want to improve **Ferdy’s Twitchiverse**? Contributions are **highly welcome!**
You can:
✅ Report issues
✅ Suggest new features
✅ Submit pull requests

---

## 📜 License

**Ferdy’s Twitchiverse** is released under the **MIT License**. See the `LICENSE` file for details.

---

### 🏗️ Third-Party Dependencies

This project uses several third-party libraries, each licensed under its respective terms. Refer to their documentation for additional licensing information.

---

🚀 **Enjoy creating your own Twitchiverse!**
