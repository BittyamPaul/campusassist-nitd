import os
import sys
import time
import sqlite3
import subprocess
from pathlib import Path
from werkzeug.security import generate_password_hash
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "campusassist.db"

def reset_clean_db():
    print("[*] Resetting database to clean demo state...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM messages")
    cur.execute("DELETE FROM conversations")
    cur.execute("DELETE FROM unresolved_queries")
    # Clean any previously added demo convocation knowledge
    cur.execute("DELETE FROM knowledge_items WHERE title LIKE '%Convocation%'")
    cur.execute("DELETE FROM sample_queries WHERE query_text LIKE '%convocation%'")
    cur.execute(
        "UPDATE users SET password_hash = ? WHERE username = ?",
        (generate_password_hash("AdminPass123!"), "admin")
    )
    conn.commit()
    conn.close()
    print("[+] Database cleaned successfully.")

def run_test():
    reset_clean_db()
    
    # Start Flask server
    print("[*] Starting Flask test server...")
    server_process = subprocess.Popen(
        [sys.executable, str(BASE_DIR / "run.py")],
        cwd=str(BASE_DIR)
    )
    
    # Wait for server to become responsive
    import urllib.request
    server_ready = False
    for attempt in range(20):
        time.sleep(1)
        try:
            with urllib.request.urlopen("http://127.0.0.1:5000/") as resp:
                if resp.status == 200:
                    server_ready = True
                    print(f"[+] Server ready after {attempt + 1}s!")
                    break
        except Exception:
            pass

    if not server_ready:
        raise RuntimeError("Flask server failed to start within 20s.")
    
    try:
        with sync_playwright() as p:
            chrome_exe = r"C:\Users\bitty\AppData\Local\ms-playwright\chromium-1243\chrome-win64\chrome.exe"
            browser = p.chromium.launch(
                executable_path=chrome_exe,
                headless=True
            )
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080}
            )
            page = context.new_page()
            page.on("dialog", lambda dialog: dialog.accept())

            # Scene 1: Landing
            print("\n--- SCENE 1: Landing & UI ---")
            page.goto("http://127.0.0.1:5000/", wait_until="networkidle")
            page.wait_for_selector(".welcome-screen")
            print("[+] Homepage loaded with welcome screen and branding.")

            # Scene 2: Phrasing Variance & Grounded Response
            print("\n--- SCENE 2: Phrasing Variance ---")
            page.fill("#queryInput", "Can I go home this weekend?")
            page.press("#queryInput", "Enter")
            page.wait_for_selector(".message-bubble.bot .msg-status-tag.verified", timeout=15000)
            print("[+] Verified response received for hostel leave phrasing query.")

            # Test feedback button
            helpful_btn = page.query_selector(".btn-feedback.btn-helpful")
            if helpful_btn:
                helpful_btn.click()
                print("[+] Clicked helpful feedback button.")

            # Follow up question
            time.sleep(1)
            page.fill("#queryInput", "What documents or permissions do I need?")
            page.press("#queryInput", "Enter")
            page.wait_for_function('document.querySelectorAll(".message-bubble.bot").length >= 2', timeout=15000)
            print("[+] Follow-up question answered with context.")

            # In desktop 1920x1080, sidebar is already open and visible on left
            page.wait_for_selector("#conversationList .conversation-item", timeout=5000)
            print("[+] Verified session appears in left sidebar list.")

            # Switch tabs in sidebar to show Explore Topics
            page.click("#tabBtnExplore")
            time.sleep(1)
            print("[+] Switched to Explore Topics tab in sidebar.")
            page.click("#tabBtnConversations")
            time.sleep(0.5)

            # Scene 3: Anti-Hallucination Circuit Breaker
            print("\n--- SCENE 3: Anti-Hallucination Fallback ---")
            page.click("#clearChatBtn")
            page.wait_for_selector(".welcome-screen", timeout=5000)
            time.sleep(1)
            page.fill("#queryInput", "What is the convocation gown deposit?")
            page.press("#queryInput", "Enter")
            page.wait_for_selector(".message-bubble.bot .msg-status-tag.unverified", timeout=15000)
            print("[+] Circuit breaker triggered! Received safe deterministic fallback.")

            # Scene 4: Admin Triage
            print("\n--- SCENE 4: Admin Triage ---")
            page.click('a[href*="/admin/login"]')
            page.wait_for_selector("#username", timeout=5000)
            page.fill("#username", "admin")
            page.fill("#password", "AdminPass123!")
            page.click('button[type="submit"]')
            page.wait_for_selector(".stats-grid", timeout=5000)
            print("[+] Logged into Admin Dashboard.")

            # Go to Unresolved queries
            page.click('a[href*="/admin/unresolved"]')
            page.wait_for_selector("#unresolved-table", timeout=5000)
            print("[+] Opened Unresolved Queries triage queue.")

            # Find row and click resolve
            resolve_btn = page.wait_for_selector('button.btn-open-resolve-modal[data-query*="convocation"]', timeout=5000)
            resolve_btn.click()
            page.wait_for_selector("#resolve-modal", state="visible", timeout=5000)
            print("[+] Opened resolve modal for convocation query.")

            # Fill form
            page.select_option("#resolve-intent-select", "10") # Academic Procedures
            page.fill("#resolve-title-input", "Convocation Gown Security Deposit and Distribution Procedure")
            page.fill("#resolve-summary-input", "Refundable security deposit and collection guidelines for convocation academic regalia.")
            page.fill(
                "#resolve-content-input",
                "1. The security deposit for the convocation gown is ₹1,000, payable at the Institute Cash Counter or online portal.\n"
                "2. Collect the gown and hood from the Student Activity Centre (SAC) by presenting the fee receipt and institute ID.\n"
                "3. Return the gown in good condition within 48 hours following the ceremony to receive a full refund."
            )
            page.fill("#resolve-authority-input", "Office of the Dean (Academic) & Convocation Committee")
            page.fill("#resolve-url-input", "https://nitdgp.ac.in")
            page.fill("#resolve-notes-input", "Verified from official NIT Durgapur convocation circular.")

            # Submit
            page.click('#resolve-new-knowledge-form button[type="submit"]')
            page.wait_for_load_state("networkidle")
            time.sleep(1)
            print("[+] Saved, verified, and indexed new knowledge item!")

            # Scene 5: Live Verification
            print("\n--- SCENE 5: Live Verification After Hot-Reload ---")
            page.click('a[href="/"]')
            page.wait_for_selector("#queryInput", timeout=5000)
            page.fill("#queryInput", "What is the convocation gown deposit?")
            page.press("#queryInput", "Enter")
            page.wait_for_selector(".message-bubble.bot .msg-status-tag.verified", timeout=15000)
            print("[+] Query now resolves with verified authoritative answer!")

            context.close()
            browser.close()
            print("\n[SUCCESS] Entire 5-scene flow executed flawlessly without errors!")

    finally:
        server_process.terminate()
        try:
            server_process.wait(timeout=3)
        except Exception:
            server_process.kill()

if __name__ == "__main__":
    run_test()
