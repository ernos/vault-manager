import sqlite3
import json
from resources import DATA_DIR
from models import Vault

DB_FILE = DATA_DIR / "vaults.db"

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS vaults (
            name TEXT PRIMARY KEY,
            container_path TEXT NOT NULL,
            mapper TEXT NOT NULL,
            mount_point TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            mounted INTEGER NOT NULL,
            last_backup TEXT,
            backup_destination TEXT,
            generation_count INTEGER NOT NULL,
            recovery_key_file TEXT,
            backups TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            message TEXT NOT NULL,
            event_type TEXT NOT NULL,
            associated_vault TEXT,
            severity TEXT NOT NULL
        )''')
        self.conn.commit()

    def log_activity(self, message, event_type, associated_vault, severity):
        from datetime import datetime
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO activity_log (timestamp, message, event_type, associated_vault, severity) VALUES (?, ?, ?, ?, ?)",
                       (datetime.now().isoformat(), message, event_type, associated_vault, severity))
        self.conn.commit()

    def get_activity_logs(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT timestamp, message, event_type, associated_vault, severity FROM activity_log ORDER BY timestamp DESC")
        return cursor.fetchall()

    def add_vault(self, v: Vault):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO vaults VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (v.name, v.container, v.mapper, v.mount_point, v.size_bytes, int(v.mounted),
                        v.last_backup, v.backup_destination, v.generation_count, v.recovery_key_file, json.dumps(v.backups)))
        self.conn.commit()

    def get_vault(self, name: str) -> Vault:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM vaults WHERE name = ?", (name,))
        row = cursor.fetchone()
        if not row: return None
        return self._row_to_vault(row)

    def all_vaults(self) -> list[Vault]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM vaults")
        return [self._row_to_vault(row) for row in cursor.fetchall()]

    def update_vault(self, v: Vault):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE vaults SET container_path=?, mapper=?, mount_point=?, size_bytes=?, mounted=?, last_backup=?, backup_destination=?, generation_count=?, recovery_key_file=?, backups=? WHERE name=?",
                       (v.container, v.mapper, v.mount_point, v.size_bytes, int(v.mounted),
                        v.last_backup, v.backup_destination, v.generation_count, v.recovery_key_file, json.dumps(v.backups), v.name))
        self.conn.commit()

    def _row_to_vault(self, row) -> Vault:
        return Vault(row[0], row[1], row[2], row[3], row[4], bool(row[5]), row[6], row[7], row[8], row[9], json.loads(row[10]))
