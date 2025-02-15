# Ferdy’s Twitchiverse

**Ferdy’s Twitchiverse** is a FastAPI-based application that integrates Twitch interactions with your local network setup. It’s a Twitchy pocket universe that supports printing various types of data (headlines, messages, and images) on a thermal printer using the ESC/POS protocol and managing dynamic overlays.

---

## Features

- **Print Functionality**: Print headlines, messages, and images on a thermal printer.
- **Dynamic Overlays**: Real-time updates to OBS overlays with alerts and custom messages.
- **Dynamic Printer Management**: Automatically reconnects if the printer is offline.
- **WebSocket Integration**: Enables live communication with the frontend.
- **Swagger Documentation**: Explore and test API endpoints with built-in docs.
- **Lightweight and Modular**: Clean architecture for easy maintenance and scalability.

---

## Requirements

- Python 3.8+
- A compatible ESC/POS thermal printer
- Libraries: `fastapi`, `uvicorn`, `escpos`, `PIL` (Pillow), `requests`

---

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/Ferdyverse/FerdysTwitchiverse.git
cd FerdysTwitchiverse
```

### 2. Install Dependencies
Create a virtual environment and install the required libraries:
```bash
python -m venv env
source env/bin/activate  # On Windows: .\env\Scripts\activate
pip install -r requirements.txt
```
**Note:** You need to install the following library on your system: `libcups2-dev`

### 3. Configure the Application
Set up the required configurations in a `config.py` file:
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

## Running the Application

### Development Mode (with Auto-Reload)
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Production Mode
```bash
python main.py
```

---

## API Endpoints

### `/print`
**POST**: Print data on the thermal printer.

- **Request Body**:
  ```json
  {
    "print_elements": [
      { "type": "headline_1", "text": "Welcome to Ferdy’s Twitchiverse!" },
      { "type": "message", "text": "This is a test message." },
      { "type": "image", "url": "http://example.com/image.png" }
    ]
  }
  ```

- **Response**:
  ```json
  {
    "status": "success",
    "message": "Print done!"
  }
  ```

### `/status`
**GET**: Get the current status of the printer.

- **Response**:
  ```json
  {
    "status": "online",
    "printer": {
      "is_online": true,
      "message": "Printer is operational"
    }
  }
  ```

### `/send-to-overlay`
**POST**: Send data to the overlay via WebSocket.

- **Request Body**:
  ```json
  {
    "alert": {
      "type": "subscriber",
      "user": "FerdyverseFan"
    }
  }
  ```

- **Response**:
  ```json
  {
    "status": "success",
    "message": "Data piped to overlay"
  }
  ```

### `/overlay-data`
**GET**: Retrieve the last follower and subscriber from the database.

- **Response**:
  ```json
  {
    "last_follower": "FerdyFan123",
    "last_subscriber": "StreamerPro"
  }
  ```

---

## Directory Structure

```
.
├── main.py                     # Main entry point for the application
├── modules/
│   ├── printer_manager.py      # Handles printer operations
│   ├── schemas.py              # Defines API request/response models
│   ├── db_manager.py           # Database interactions for persistence
├── templates/
│   └── overlay.html            # HTML for the overlay
├── static/
│   ├── css/                    # Stylesheets
│   ├── js/                     # JavaScript files
├── config.py                   # Configuration file
├── README.md                   # Documentation
└── requirements.txt            # Python dependencies
```

---

## Contributing

Feel free to submit issues or pull requests if you’d like to improve or add new features. Contributions are welcome!

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.

### Third-Party Dependencies

The project uses third-party libraries, each governed by their respective licenses. Refer to the libraries' documentation for details.
