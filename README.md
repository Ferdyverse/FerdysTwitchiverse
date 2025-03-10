# **Ferdy’s Twitchiverse**

**Ferdy’s Twitchiverse** is a **FastAPI-based** application that **integrates Twitch interactions** with a **real-time overlay system** and **custom event automation**. The system allows **dynamic overlays, interactive chat features, scheduled events, CouchDB-powered data storage, and full control over Twitch-based interactions**.

---

⚠️ **Work in Progress**
This project is evolving rapidly. Some documentation might be out of date until the core features are finalized.

---

## 🚀 **Features**

- **📡 WebSocket Integration** – Real-time communication between Twitch events, overlays, and the admin panel.
- **🎬 Dynamic Overlays** – Customizable overlays for OBS/Web, supporting alerts, animations, and interactive elements.
- **📜 Chat System** – Displays **Twitch chat messages** in the admin panel, including emoji support and moderation tools.
- **🛠️ CouchDB Storage** – Uses **CouchDB** for fast, document-based data storage (viewers, events, to-dos, buttons, sequences).
- **🕹️ Admin Panel** – Web-based dashboard for controlling overlays, executing sequences, and managing events.
- **🔧 Automated Event Handling** – Supports **custom sequences** triggered by chat, events, or scheduled jobs.
- **📅 Scheduled Messages** – Custom message pools and automatic scheduled event handling.
- **🖱️ Interactive Elements** – Supports **clickable objects** for interactive stream events.
- **📊 OBS WebSocket API** – Allows control over **OBS sources, scenes, and visibility** directly from the admin panel.

---

## 📌 **Requirements**

- **Python 3.10+**
- **Docker** (recommended for running CouchDB)
- Installed libraries: `fastapi`, `uvicorn`, `couchdb`, `asyncio`, `htmx`, `websockets`
- **CouchDB** (Required for data storage)

---

## 📥 **Installation**

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

### 3️⃣ Start CouchDB (Recommended via Docker)

```bash
docker run -d --name couchdb -p 5984:5984 -e COUCHDB_USER=admin -e COUCHDB_PASSWORD=password couchdb
```

Or install CouchDB manually and access the **Fauxton Interface** via:
🔗 `http://127.0.0.1:5984/_utils/`

---

## ▶ **Running the Application**

### 🛠 **Development Mode (Auto-Reload)**

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 🚀 **Production Mode**

```bash
python main.py
```

---

## **Twitch API Configuration**
To use Twitch-based features, you need to set up OAuth authentication.

1. Register your application in the **Twitch Developer Console**:
   🔗 [https://dev.twitch.tv/console](https://dev.twitch.tv/console)
2. Get your **Client ID** and **Client Secret**.
3. Configure `config.py` and create a `.env`-file:

```python
# .env
COUCHDB_USER=admin
COUCHDB_PASSWORD=password

TWITCH_CLIENT_ID=1
TWITCH_CLIENT_SECRET=1

SPOTIFY_CLIENT_ID=1
SPOTIFY_CLIENT_SECRET=1
```

4. Run **Twitch CLI** to simulate events:

```bash
twitch-cli mock-api start
twitch-cli event websocket start -p 8081
```

---

## 🔗 **API Endpoints**

Once the app is running, open your browser and visit:

📜 **Swagger Docs:**
➡ **`http://localhost:8000/docs`** – Interactive API testing

🛠 **Redoc Docs:**
➡ **`http://localhost:8000/redoc`** – Alternative API reference

---

## 📂 **Project Structure**

```
.
├── main.py                     # Application entry point
├── modules/
│   ├── twitch_api.py           # Handles Twitch API interactions
│   ├── websocket_handler.py    # Manages WebSocket connections
│   ├── obs_api.py              # OBS WebSocket integration
│   ├── couchdb_client.py       # Handles CouchDB interactions
│   ├── sequence_runner.py      # Executes event sequences
│   ├── event_queue_processor.py# Manages event queue
├── database/
│   ├── crud/                   # CRUD operations for CouchDB
│   ├── session.py              # Database connection setup
├── templates/
│   ├── overlay.html            # Main overlay HTML
│   ├── admin_panel.html        # Admin panel UI
│   └── includes/               # Partial HTML templates
├── static/
│   ├── css/                    # Stylesheets
│   ├── js/                     # JavaScript files
├── config.py                   # Configuration settings
├── README.md                   # Project documentation
└── requirements.txt            # Required Python dependencies
```

---

## **🛠 Key Features in Detail**

### 🎬 **Overlay System**
- Web-based overlay using WebSockets.
- Supports **alerts, animations, and OBS scene switching**.
- Can be controlled via the **admin panel** or Twitch chat commands.

### 🛠️ **Admin Panel**
- HTMX-based admin panel for:
  - Sending events to the overlay.
  - Managing custom sequences.
  - Triggering Twitch interactions.

### 📜 **Database & Storage (CouchDB)**
- Stores:
  - Viewer data
  - Chat history
  - Scheduled messages
  - Overlay configurations
  - Admin buttons & controls
  - Event logs

### 📡 **WebSocket-Based Communication**
- **Real-time chat events** (e.g., when a viewer sends a message).
- **Click event handling** for stream interactions.
- **Twitch event notifications** (e.g., new followers, raids, etc.).

### 📅 **Scheduled Events**
- Supports **interval-based events, cron jobs, and Twitch-triggered sequences**.
- Uses **CouchDB for persistence**.

### 🔧 **OBS WebSocket Control**
- Directly interacts with **OBS WebSocket API**.
- Can **switch scenes, enable/disable sources, and trigger animations**.

---

## 🎭 **Contributing**

Want to improve **Ferdy’s Twitchiverse**? Contributions are **highly welcome!**
✅ Report issues
✅ Suggest new features
✅ Submit pull requests

---

## 📜 **License**

**Ferdy’s Twitchiverse** is released under the **MIT License**. See the `LICENSE` file for details.

---

### 🏗 **Third-Party Dependencies**
This project uses several third-party libraries, each licensed under its respective terms. Refer to their documentation for additional licensing information.

---

🚀 **Enjoy creating your own Twitchiverse!**
