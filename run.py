"""
CampusAssist Entry Point.
Runs the development server for local testing.
"""

from app import create_app
from config import Config
from seed_db import seed_database
from pathlib import Path

app = create_app(Config)

if __name__ == "__main__":
    db_file = Path(Config.DB_PATH)
    if not db_file.exists():
        print(f"[*] Database file not found at {db_file}. Running initial seeding...")
        seed_database()

    print("\n" + "=" * 60)
    print(" CampusAssist: AI-Powered Student Assistant for NIT Durgapur")
    print(" Computer Science & Engineering Department")
    print(" Project Owner: Bittyam Paul")
    print("=" * 60)
    print(" Serving at: http://127.0.0.1:5000")
    print("=" * 60 + "\n")
    app.run(host="127.0.0.1", port=5000, debug=Config.DEBUG)
