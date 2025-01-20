# Twitch2HomeLab - README

## Übersicht
**Twitch2HomeLab** ist eine API, die mit FastAPI erstellt wurde und es ermöglicht, Avatare von Twitch-Nutzern mit Überschrift, Benutzernamen und Nachricht auf einem ESC/POS-kompatiblen Drucker auszudrucken. Dieses Projekt wurde speziell für den Wincor Nixdorf TH230 Drucker entwickelt, kann aber mit ähnlichen Geräten angepasst werden.

---

## Voraussetzungen

### Software
1. **Python 3.8+**
2. **Abhängigkeiten**:
    - `fastapi`
    - `pydantic`
    - `python-escpos`
    - `Pillow`
    - `requests`

### Hardware
- **ESC/POS-kompatibler Drucker** (z. B. Wincor Nixdorf TH230)
- **USB-Verbindung zum Drucker**

### Betriebssystem
- Linux (z. B. Ubuntu/Debian) wird empfohlen.
- Stelle sicher, dass du die entsprechenden Berechtigungen hast, um auf USB-Geräte zuzugreifen (siehe `udev`-Konfiguration).

---

## Installation

1. **Projekt klonen**:
    ```bash
    git clone <repository-url>
    cd <repository-folder>
    ```

2. **Virtuelle Umgebung erstellen und aktivieren**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3. **Abhängigkeiten installieren**:
    ```bash
    pip install -r requirements.txt
    ```

4. **API starten**:
    ```bash
    uvicorn escpos_printer_api:app --reload
    ```

---

## Nutzung

### API-Endpunkte

#### 1. **POST /print**
Druckt einen Twitch-Avatar mit einer Überschrift, dem Benutzernamen und einer Nachricht.

- **Payload**:
    ```json
    {
        "image_url": "https://example.com/avatar.png",
        "headline": "Willkommen im Stream!",
        "twitch_username": "CoolStreamer123",
        "message": "Danke, dass du ein Teil der Community bist!"
    }
    ```

- **Erfolgreiche Antwort**:
    ```json
    {
        "status": "success",
        "message": "Überschrift, Avatar, Benutzername und Nachricht gedruckt"
    }
    ```

- **Fehler**:
    - 500: Drucker ist nicht verfügbar.
    - 400: Fehler beim Herunterladen des Bildes.

#### 2. **GET /status**
Überprüft, ob der Drucker online ist.

- **Antwort**:
  - **Online**:
    ```json
    {
        "status": "online",
        "message": "Drucker bereit"
    }
    ```
  - **Offline**:
    ```json
    {
        "status": "offline",
        "message": "Drucker nicht verfügbar"
    }
    ```

---

## Anpassungen

### Druckerkonfiguration
Passen Sie die folgenden Parameter in der Datei `escpos_printer_api.py` an:
- **`VENDOR_ID`**: Vendor-ID des Druckers (z. B. `0x0aa7`).
- **`PRODUCT_ID`**: Product-ID des Druckers (z. B. `0x0304`).
- **`in_ep`** und **`out_ep`**: Endpunkte für den USB-Drucker (siehe `lsusb -v`).

### `udev`-Regeln
Füge `udev`-Regeln hinzu, um den Zugriff auf den Drucker ohne Root-Rechte zu ermöglichen:
1. Erstelle die Datei `/etc/udev/rules.d/99-usb.rules`:
    ```bash
    sudo nano /etc/udev/rules.d/99-usb.rules
    ```
2. Füge folgende Zeile hinzu:
    ```
    SUBSYSTEM=="usb", ATTR{idVendor}=="0aa7", ATTR{idProduct}=="0304", MODE="0666"
    ```
3. Lade die Regeln neu:
    ```bash
    sudo udevadm control --reload-rules
    sudo udevadm trigger
    ```

---

## Hinweise zur Bildverarbeitung

- **Schwarz-Weiß-Invertierung**:
    Die Invertierung von Schwarz und Weiß kann im Code angepasst werden:
    ```python
    image = ImageOps.invert(image.convert("L")).convert("1")
    ```
- **Bildoptionen für den Druck**:
    Die folgenden Parameter im `printer.image`-Aufruf können angepasst werden:
    - `high_density_horizontal` und `high_density_vertical`
    - `impl`: Druckmodus (z. B. `bitImageColumn`).
    - `fragment_height`: Maximale Höhe für das Fragment.

---

## Fehlerbehebung

1. **Fehler „Unable to open USB printer“**:
    - Überprüfe die `VENDOR_ID` und `PRODUCT_ID` mit `lsusb`.
    - Stelle sicher, dass die `udev`-Regeln korrekt sind.

2. **Fehler „Invalid endpoint address“**:
    - Stelle sicher, dass `in_ep` und `out_ep` korrekt konfiguriert sind (siehe `lsusb -v`).

3. **Fehler „Drucker nicht verfügbar“**:
    - Überprüfe die Verbindung und den Status des Druckers.

---

## Weiterentwicklung

- Unterstützung für weitere Druckermodelle.
- Erweiterte Bildverarbeitung (z. B. Größenänderung, Rahmen).
- Weitere API-Endpunkte (z. B. Warteschlange für Druckaufträge).

---

## Lizenz
Dieses Projekt steht unter der MIT-Lizenz. Weitere Informationen in der Datei `LICENSE`.
