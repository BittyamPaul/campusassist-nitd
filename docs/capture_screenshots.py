import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "CampusAssist_Presentation_Assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

print(f"[*] Target assets directory: {ASSETS_DIR}")

def capture_all():
    with sync_playwright() as p:
        chrome_exe = r"C:\Users\bitty\AppData\Local\ms-playwright\chromium-1243\chrome-win64\chrome.exe"
        if os.path.exists(chrome_exe):
            browser = p.chromium.launch(executable_path=chrome_exe, headless=True)
        else:
            browser = p.chromium.launch(headless=True)

        context = browser.new_context(
            viewport={"width": 1600, "height": 950},
            device_scale_factor=2,
        )
        page = context.new_page()

        # 1. Main Chat Interface (Slide 4)
        print("[*] Navigating to http://127.0.0.1:5000/ ...")
        page.goto("http://127.0.0.1:5000/", wait_until="networkidle")
        time.sleep(1.5)
        main_chat_path = ASSETS_DIR / "ui_slide04_main_chat.png"
        page.screenshot(path=str(main_chat_path), full_page=False)
        print(f"[+] Saved Slide 4 main interface screenshot: {main_chat_path}")

        # 2. Walkthrough Query & Response (Slide 12)
        print("[*] Dispatching examination query via form submission...")
        page.evaluate("""() => {
            const input = document.getElementById('queryInput');
            const form = document.getElementById('chatForm');
            input.value = "How do I find examination information?";
            input.dispatchEvent(new Event('input', { bubbles: true }));
            form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
        }""")

        # Wait for bot response message
        print("[*] Waiting for bot response (.message-bubble.bot)...")
        page.wait_for_selector(".message-bubble.bot", timeout=25000)
        time.sleep(3)  # Wait for markdown formatting and metadata box to render smoothly

        query_resp_path = ASSETS_DIR / "ui_slide12_query_response.png"
        page.screenshot(path=str(query_resp_path), full_page=False)
        print(f"[+] Saved Slide 12 query-response screenshot: {query_resp_path}")

        # 3. Admin Login & Dashboard (Slide 11)
        print("[*] Navigating to http://127.0.0.1:5000/admin/login ...")
        page.goto("http://127.0.0.1:5000/admin/login", wait_until="networkidle")
        time.sleep(1)

        page.fill("#username", "admin")
        page.fill("#password", "AdminPass123!")
        page.click("button[type='submit']")
        page.wait_for_load_state("networkidle")
        time.sleep(1.5)

        admin_dash_path = ASSETS_DIR / "ui_slide11_admin_dashboard.png"
        page.screenshot(path=str(admin_dash_path), full_page=False)
        print(f"[+] Saved Slide 11 admin dashboard screenshot: {admin_dash_path}")

        # 4. Admin Unresolved Queries (Slide 13)
        try:
            print("[*] Navigating to http://127.0.0.1:5000/admin/unresolved ...")
            page.goto("http://127.0.0.1:5000/admin/unresolved", wait_until="networkidle")
            time.sleep(1.5)
            unresolved_path = ASSETS_DIR / "ui_slide13_admin_unresolved.png"
            page.screenshot(path=str(unresolved_path), full_page=False)
            print(f"[+] Saved Slide 13 unresolved queries screenshot: {unresolved_path}")
        except Exception as e:
            print(f"[!] Unresolved view error: {e}")

        # 5. Admin Knowledge Repository View
        try:
            print("[*] Navigating to http://127.0.0.1:5000/admin/knowledge ...")
            page.goto("http://127.0.0.1:5000/admin/knowledge", wait_until="networkidle")
            time.sleep(1.5)
            knowledge_path = ASSETS_DIR / "ui_admin_knowledge.png"
            page.screenshot(path=str(knowledge_path), full_page=False)
            print(f"[+] Saved admin knowledge repository screenshot: {knowledge_path}")
        except Exception as e:
            print(f"[!] Knowledge view error: {e}")

        context.close()
        browser.close()
        print("[+] All genuine UI screenshots successfully captured!")

if __name__ == "__main__":
    capture_all()

