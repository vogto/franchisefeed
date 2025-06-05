# 🛠️ FranchiseFeed Exporter

Dieses Projekt exportiert Daten aus einer Amazon Redshift-Datenbank in eine CSV-Datei und lädt sie automatisiert per SFTP auf einen externen Server hoch.

---

## 🔧 Setup-Anleitung

### 1. Projektstruktur

```bash
/opt/franchisfeed/
├── franchisefeed.py
├── .env
└── venv/
```

---

### 2. Virtuelle Umgebung erstellen und Abhängigkeiten installieren

```bash
cd /opt/franchisfeed
python3 -m venv venv
source venv/bin/activate
pip install psycopg2-binary pandas paramiko python-dotenv import requests
```

---

### 3. Konfiguration: `.env`-Datei erstellen

```ini
# Redshift-Datenbank
DB_NAME=dwh
DB_USER=xxx
DB_PASSWORD=xxx
DB_HOST=xxx
DB_PORT=5439

# SFTP Zugangsdaten
SFTP_HOST=dedi848.your-server.de
SFTP_PORT=22
SFTP_USER=xxx
SFTP_PASSWORD=xxx
SFTP_REMOTE_DIR=/

# GOOGLE MSG
GOOGLE_CHAT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/AAA.../messages?key=...&token=...
```

---

### 4. Python-Skript: `franchisefeed.py`

Speichere folgendes Skript unter `/opt/franchisfeed/franchisefeed.py` und stelle sicher, dass es ausführbar ist:

```bash
chmod +x /opt/franchisfeed/franchisefeed.py
```

Das Skript:

- Lädt Umgebungsvariablen
- Verbindet sich mit Redshift
- Exportiert das Ergebnis einer SQL-Abfrage als `franchisefeed.csv`
- Lädt die CSV per SFTP hoch

> Der vollständige Code befindet sich in dieser Datei.

---

### 5. Manuell testen

```bash
python /opt/franchisfeed/franchisefeed.py
```

---

## 🧩 Systemd-Service

Um das Skript regelmäßig oder beim Systemstart auszuführen, kann ein `systemd`-Service eingerichtet werden.

### 1. Service-Datei erstellen

```bash
sudo nano /etc/systemd/system/franchisefeed.service
```

#### Inhalt:

```ini
[Unit]
Description=Exportiere Redshift CSV und lade per SFTP hoch
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/franchisfeed/
ExecStart=/opt/franchisfeed/venv/bin/python3 /opt/franchisfeed/franchisefeed.py
EnvironmentFile=/opt/franchisfeed/.env
StandardOutput=append:/var/log/franchisefeed.log
StandardError=append:/var/log/franchisefeed.log

[Install]
WantedBy=multi-user.target
```

---

### 2. Service aktivieren und starten

```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable franchisefeed.service
sudo systemctl start franchisefeed.service
```

---

### 3. Service prüfen

Status anzeigen:

```bash
sudo systemctl status franchisefeed.service
```

Logs live ansehen:

```bash
journalctl -u franchisefeed.service -f
```

---

## 📁 Ausgabe

Die CSV-Datei `franchisefeed.csv` wird lokal generiert und automatisch auf das konfigurierte SFTP-Ziel hochgeladen.

---

## 📝 Hinweise

- Die SQL-Abfrage ist auf Produkte mit `item_purchaser_group = 'B01'` beschränkt.
- Die Datei `franchisefeed.csv` enthält strukturierte Produktdaten inkl. EANs, Maße, Material, Lagerstand etc.
- Die Datei wird mit Semikolon (`;`) als Trennzeichen und doppelten Anführungszeichen (`"`) als Quotechar erstellt.

---

## ✅ Lizenz

Private interne Anwendung für Datenexport aus Redshift. Keine externe Weitergabe.


---

## ⏰ Optional: systemd-Timer (statt Cronjob)

Du kannst einen systemd-Timer verwenden, um den Export regelmäßig auszuführen (z. B. täglich um 03:00 Uhr).

### 1. Timer-Datei erstellen

```bash
sudo nano /etc/systemd/system/franchisefeed.timer
```

#### Inhalt:

```ini
[Unit]
Description=Timer für FranchiseFeed Export

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

---

### 2. Timer aktivieren und starten

```bash
sudo systemctl daemon-reload
sudo systemctl enable franchisefeed.timer
sudo systemctl start franchisefeed.timer
```

---

### 3. Timer prüfen

Liste aktiver Timer anzeigen:

```bash
systemctl list-timers
```

Status eines bestimmten Timers anzeigen:

```bash
systemctl status franchisefeed.timer
```

Logs des Services anzeigen:

```bash
journalctl -u franchisefeed.service
```

---
