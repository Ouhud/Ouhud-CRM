import os
import paramiko
from pathlib import Path
from dotenv import load_dotenv

# ✅ 1. .env laden
load_dotenv()

# ✅ 2. SFTP-Parameter auslesen
SFTP_HOST = os.getenv("SFTP_HOST")
SFTP_PORT = int(os.getenv("SFTP_PORT", "22"))
SFTP_USER = os.getenv("SFTP_USER")
SFTP_PASS = os.getenv("SFTP_PASS")
REMOTE_DIR = os.getenv("SFTP_REMOTE_DIR")
LOCAL_DIR  = "app/bank_statements/incoming"

# 📌 Debug: prüfen ob Variablen korrekt geladen wurden
print("DEBUG SFTP_HOST:", SFTP_HOST)
print("DEBUG SFTP_USER:", SFTP_USER)

Path(LOCAL_DIR).mkdir(parents=True, exist_ok=True)

# ✅ 3. Hauptfunktion
def run():
    transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
    transport.connect(username=SFTP_USER, password=SFTP_PASS)
    sftp = paramiko.SFTPClient.from_transport(transport)

    for filename in sftp.listdir(REMOTE_DIR):
        local_path = Path(LOCAL_DIR) / filename
        remote_path = f"{REMOTE_DIR}/{filename}"
        sftp.get(remote_path, str(local_path))
        print(f"⬇️ Datei heruntergeladen: {filename}")

    sftp.close()
    transport.close()


if __name__ == "__main__":
    run()