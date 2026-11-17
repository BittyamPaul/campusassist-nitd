"""
CampusAssist: Automated 1920x1080 Demo Walkthrough Video Recorder.
Records a 5-scene continuous walkthrough of CampusAssist in action using Playwright,
then converts the raw WebM recording to a crisp H.264 MP4 (campusassist_demo.mp4) using FFmpeg.

Scenes:
1. Landing & Institutional UI
2. Phrasing Variance & Grounded Response (+ Follow-up & Sidebar session)
3. Anti-Hallucination Circuit Breaker (Out-of-Scope Query)
4. Human-in-the-Loop Admin Triage & Knowledge Verification
5. Live Verification After Hot-Reload
"""

import os
import sys
import time
import random
import shutil
import sqlite3
import subprocess
from pathlib import Path
from werkzeug.security import generate_password_hash
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "campusassist.db"
RECORDINGS_DIR = BASE_DIR / "recordings_raw"
FINAL_VIDEO_PATH = BASE_DIR / "campusassist_demo.mp4"

# Locate FFmpeg binary from imageio-ffmpeg
FFMPEG_EXE = BASE_DIR / "venv" / "Lib" / "site-packages" / "imageio_ffmpeg" / "binaries" / "ffmpeg-win-x86_64-v9.0.2.exe"
if not FFMPEG_EXE.exists():
    try:
        import imageio_ffmpeg
        FFMPEG_EXE = Path(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception:
        FFMPEG_EXE = Path("ffmpeg")

def reset_clean_demo_db():
    """Ensure clean database state with zero previous test clutter."""
    print("[*] Preparing clean demo database state...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM messages")
    cur.execute("DELETE FROM conversations")
    cur.execute("DELETE FROM unresolved_queries")
    cur.execute("DELETE FROM knowledge_items WHERE title LIKE '%Convocation%'")
    cur.execute("DELETE FROM sample_queries WHERE query_text LIKE '%convocation%'")
    cur.execute(
        "UPDATE users SET password_hash = ? WHERE username = ?",
        (generate_password_hash("AdminPass123!"), "admin")
    )
    conn.commit()
    conn.close()
    print("[+] Database cleaned successfully (0 conversations, 0 unresolved queries).")

def type_realistically(page, selector: str, text: str, min_delay: int = 40, max_delay: int = 70):
    """Types character-by-character with natural human typing rhythm."""
    page.click(selector)
    time.sleep(0.3)
    for char in text:
        page.type(selector, char, delay=random.randint(min_delay, max_delay))
        if char in (" ", ",", "?"):
            time.sleep(random.uniform(0.04, 0.09))
    time.sleep(0.4)

def inject_visual_cursor(page):
    """Injects a subtle smooth cursor indicator to make demo video easy to follow."""
    cursor_script = """
    (() => {
        if (document.getElementById('demo-cursor-dot')) return;
        const cursor = document.createElement('div');
        cursor.id = 'demo-cursor-dot';
        cursor.style.width = '20px';
        cursor.style.height = '20px';
        cursor.style.borderRadius = '50%';
        cursor.style.backgroundColor = 'rgba(220, 38, 38, 0.85)';
        cursor.style.border = '2px solid #ffffff';
        cursor.style.boxShadow = '0 0 8px rgba(0,0,0,0.4)';
        cursor.style.position = 'fixed';
        cursor.style.pointerEvents = 'none';
        cursor.style.zIndex = '9999999';
        cursor.style.transform = 'translate(-50%, -50%)';
        cursor.style.transition = 'width 0.12s, height 0.12s, background-color 0.15s';
        cursor.style.left = '960px';
        cursor.style.top = '540px';
        document.body.appendChild(cursor);

        document.addEventListener('mousemove', (e) => {
            cursor.style.left = e.clientX + 'px';
            cursor.style.top = e.clientY + 'px';
        });

        document.addEventListener('mousedown', () => {
            cursor.style.width = '14px';
            cursor.style.height = '14px';
            cursor.style.backgroundColor = 'rgba(185, 28, 28, 1)';
        });

        document.addEventListener('mouseup', () => {
            cursor.style.width = '20px';
            cursor.style.height = '20px';
            cursor.style.backgroundColor = 'rgba(220, 38, 38, 0.85)';
        });
    })();
    """
    try:
        page.evaluate(cursor_script)
    except Exception:
        pass

def move_mouse_smoothly(page, target_x: int, target_y: int, steps: int = 15):
    """Smoothly animates mouse cursor across the screen."""
    page.mouse.move(target_x, target_y, steps=steps)
    time.sleep(0.15)

def move_mouse_to_element(page, selector: str, steps: int = 15):
    """Moves mouse smoothly to the center of a selector."""
    try:
        box = page.locator(selector).first.bounding_box()
        if box:
            center_x = box["x"] + box["width"] / 2
            center_y = box["y"] + box["height"] / 2
            move_mouse_smoothly(page, center_x, center_y, steps=steps)
    except Exception:
        pass

def record_walkthrough():
    reset_clean_demo_db()

    # Clean previous raw recordings
    if RECORDINGS_DIR.exists():
        shutil.rmtree(RECORDINGS_DIR, ignore_errors=True)
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

    # Start Flask server
    print("[*] Starting CampusAssist server at http://127.0.0.1:5000 ...")
    server_process = subprocess.Popen(
        [sys.executable, str(BASE_DIR / "run.py")],
        cwd=str(BASE_DIR)
    )

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
        server_process.kill()
        raise RuntimeError("CampusAssist server failed to start.")

    try:
        with sync_playwright() as p:
            chrome_exe = r"C:\Users\bitty\AppData\Local\ms-playwright\chromium-1243\chrome-win64\chrome.exe"
            browser = p.chromium.launch(
                executable_path=chrome_exe,
                headless=True,
                args=["--window-size=1920,1080", "--no-sandbox"]
            )

            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                record_video_dir=str(RECORDINGS_DIR),
                record_video_size={"width": 1920, "height": 1080}
            )

            page = context.new_page()
            page.on("dialog", lambda dialog: dialog.accept())

            # =================================================================
            # SCENE 1: Landing & Institutional UI
            # =================================================================
            print("\n===========================================================")
            print(" SCENE 1: Landing & Institutional UI")
            print("===========================================================")
            page.goto("http://127.0.0.1:5000/", wait_until="networkidle")
            page.wait_for_selector(".welcome-screen", timeout=10000)
            inject_visual_cursor(page)

            # Showcase institutional banner, motto, and brand elements
            move_mouse_smoothly(page, 960, 18, steps=18)
            time.sleep(1.0)
            move_mouse_to_element(page, ".site-navbar .brand-text", steps=15)
            time.sleep(1.0)

            # Showcase starter topic cards
            move_mouse_to_element(page, '.welcome-card[data-query*="leave"]', steps=16)
            time.sleep(0.8)
            move_mouse_to_element(page, '.welcome-card[data-query*="facilities"]', steps=14)
            time.sleep(0.8)
            move_mouse_to_element(page, '.welcome-card[data-query*="examination"]', steps=14)
            time.sleep(1.2)

            # Settle on the input box
            move_mouse_to_element(page, "#queryInput", steps=15)
            time.sleep(1.8)

            # =================================================================
            # SCENE 2: Phrasing Variance & Grounded Response
            # =================================================================
            print("\n===========================================================")
            print(" SCENE 2: Phrasing Variance & Grounded Response")
            print("===========================================================")
            query_1 = "Can I go home this weekend?"
            print(f"[*] Typing natural-language query: '{query_1}'")
            type_realistically(page, "#queryInput", query_1)
            time.sleep(0.6)

            # Click Send button
            move_mouse_to_element(page, "#sendBtn", steps=12)
            page.click("#sendBtn")

            # Wait for assistant response to render
            page.wait_for_selector(".message-bubble.bot .msg-status-tag.verified", timeout=20000)
            time.sleep(1.0)
            inject_visual_cursor(page)

            # Showcase verified badge & response
            move_mouse_to_element(page, ".msg-status-tag.verified", steps=15)
            time.sleep(1.5)

            # Showcase authority contact and portal link
            move_mouse_to_element(page, ".meta-portal-btn", steps=15)
            time.sleep(1.5)

            # Click helpful feedback button
            move_mouse_to_element(page, ".btn-feedback.btn-helpful", steps=12)
            page.click(".btn-feedback.btn-helpful")
            time.sleep(1.2)

            # Natural reading pause
            time.sleep(2.2)

            # Ask short follow-up question
            followup_query = "What documents or permissions do I need?"
            print(f"[*] Asking contextual follow-up: '{followup_query}'")
            move_mouse_to_element(page, "#queryInput", steps=12)
            type_realistically(page, "#queryInput", followup_query)
            time.sleep(0.5)
            page.press("#queryInput", "Enter")

            # Wait for follow-up answer
            page.wait_for_function('document.querySelectorAll(".message-bubble.bot").length >= 2', timeout=20000)
            time.sleep(1.0)
            inject_visual_cursor(page)
            time.sleep(2.5)

            # Showcase session in left sidebar
            move_mouse_to_element(page, "#conversationList .conversation-item", steps=15)
            time.sleep(1.5)

            # Switch to Explore tab in sidebar
            move_mouse_to_element(page, "#tabBtnExplore", steps=12)
            page.click("#tabBtnExplore")
            time.sleep(1.8)

            # Switch back to Chats tab
            move_mouse_to_element(page, "#tabBtnConversations", steps=12)
            page.click("#tabBtnConversations")
            time.sleep(1.2)

            # =================================================================
            # SCENE 3: Anti-Hallucination Circuit Breaker (Out-of-Scope Query)
            # =================================================================
            print("\n===========================================================")
            print(" SCENE 3: Anti-Hallucination Circuit Breaker")
            print("===========================================================")
            # Start New Conversation
            move_mouse_to_element(page, "#clearChatBtn", steps=14)
            page.click("#clearChatBtn")
            page.wait_for_selector(".welcome-screen", timeout=8000)
            time.sleep(1.5)
            inject_visual_cursor(page)

            # Ask unindexed convocation question
            unindexed_query = "What is the convocation gown deposit?"
            print(f"[*] Asking unindexed query: '{unindexed_query}'")
            move_mouse_to_element(page, "#queryInput", steps=12)
            type_realistically(page, "#queryInput", unindexed_query)
            time.sleep(0.5)
            page.press("#queryInput", "Enter")

            # Wait for safe deterministic fallback
            page.wait_for_selector(".message-bubble.bot .msg-status-tag.unverified", timeout=20000)
            time.sleep(1.0)
            inject_visual_cursor(page)

            # Highlight the unverified fallback badge and safe notice
            move_mouse_to_element(page, ".msg-status-tag.unverified", steps=15)
            time.sleep(1.5)
            move_mouse_to_element(page, ".message-bubble.bot .msg-body", steps=15)

            # Generous pause confirming zero hallucinated policies/fees
            print("[+] Verified safe deterministic fallback message rendered.")
            time.sleep(2.8)

            # =================================================================
            # SCENE 4: Human-in-the-Loop Admin Triage
            # =================================================================
            print("\n===========================================================")
            print(" SCENE 4: Human-in-the-Loop Admin Triage")
            print("===========================================================")
            # Click Staff Login
            move_mouse_to_element(page, 'a[href*="/admin/login"]', steps=15)
            page.click('a[href*="/admin/login"]')
            page.wait_for_selector("#username", timeout=8000)
            inject_visual_cursor(page)
            time.sleep(1.2)

            # Fill credentials
            move_mouse_to_element(page, "#username", steps=12)
            type_realistically(page, "#username", "admin", min_delay=50, max_delay=90)
            time.sleep(0.3)
            move_mouse_to_element(page, "#password", steps=12)
            type_realistically(page, "#password", "AdminPass123!", min_delay=50, max_delay=90)
            time.sleep(0.5)

            move_mouse_to_element(page, 'button[type="submit"]', steps=12)
            page.click('button[type="submit"]')
            page.wait_for_selector(".stats-grid", timeout=10000)
            inject_visual_cursor(page)
            print("[+] Logged into Admin Dashboard.")

            # Tour overview metrics
            move_mouse_smoothly(page, 320, 260, steps=15)
            time.sleep(1.0)
            move_mouse_smoothly(page, 620, 260, steps=14)
            time.sleep(1.0)
            move_mouse_smoothly(page, 920, 260, steps=14)
            time.sleep(1.5)

            # Open Unresolved Queries triage tab
            move_mouse_to_element(page, 'a[href*="/admin/unresolved"]', steps=15)
            page.click('a[href*="/admin/unresolved"]')
            page.wait_for_selector("#unresolved-table", timeout=10000)
            inject_visual_cursor(page)
            time.sleep(1.5)

            # Hover over the logged convocation query row
            resolve_btn = page.wait_for_selector('button.btn-open-resolve-modal[data-query*="convocation"]', timeout=8000)
            move_mouse_to_element(page, 'button.btn-open-resolve-modal[data-query*="convocation"]', steps=14)
            time.sleep(1.2)

            # Open Resolve Modal
            resolve_btn.click()
            page.wait_for_selector("#resolve-modal", state="visible", timeout=8000)
            inject_visual_cursor(page)
            time.sleep(1.2)

            # Fill in verified knowledge
            print("[*] Authoring verified knowledge entry for convocation...")
            page.select_option("#resolve-intent-select", "10") # Academic Procedures
            time.sleep(0.6)

            move_mouse_to_element(page, "#resolve-title-input", steps=10)
            type_realistically(page, "#resolve-title-input", "Convocation Gown Security Deposit and Distribution Procedure", min_delay=20, max_delay=35)
            time.sleep(0.4)

            move_mouse_to_element(page, "#resolve-summary-input", steps=10)
            type_realistically(page, "#resolve-summary-input", "Refundable security deposit and collection guidelines for convocation academic regalia.", min_delay=20, max_delay=35)
            time.sleep(0.4)

            move_mouse_to_element(page, "#resolve-content-input", steps=10)
            detailed_convocation_text = (
                "1. The security deposit for the convocation gown is ₹1,000, payable at the Institute Cash Counter or designated online portal.\n"
                "2. Collect the gown and hood from the Student Activity Centre (SAC) by presenting the fee receipt and institute ID.\n"
                "3. Return the gown in good condition within 48 hours following the ceremony to receive a full refund."
            )
            type_realistically(page, "#resolve-content-input", detailed_convocation_text, min_delay=12, max_delay=24)
            time.sleep(0.4)

            move_mouse_to_element(page, "#resolve-authority-input", steps=10)
            type_realistically(page, "#resolve-authority-input", "Office of the Dean (Academic) & Convocation Committee", min_delay=20, max_delay=35)
            time.sleep(0.4)

            move_mouse_to_element(page, "#resolve-url-input", steps=10)
            type_realistically(page, "#resolve-url-input", "https://nitdgp.ac.in", min_delay=25, max_delay=45)
            time.sleep(0.4)

            move_mouse_to_element(page, "#resolve-notes-input", steps=10)
            type_realistically(page, "#resolve-notes-input", "Verified from official NIT Durgapur convocation circular.", min_delay=20, max_delay=35)
            time.sleep(1.0)

            # Submit and hot-reload index
            move_mouse_to_element(page, '#resolve-new-knowledge-form button[type="submit"]', steps=12)
            page.click('#resolve-new-knowledge-form button[type="submit"]')
            page.wait_for_load_state("networkidle")
            time.sleep(2.0)
            inject_visual_cursor(page)
            print("[+] Query resolved and indexed into semantic vector store!")

            # =================================================================
            # SCENE 5: Live Verification After Hot-Reload
            # =================================================================
            print("\n===========================================================")
            print(" SCENE 5: Live Verification After Hot-Reload")
            print("===========================================================")
            # Return to Student Assistant
            move_mouse_to_element(page, 'nav a[href="/"]', steps=15)
            page.click('nav a[href="/"]')
            page.wait_for_selector("#queryInput", timeout=10000)
            inject_visual_cursor(page)
            time.sleep(1.5)

            # Re-ask the exact same convocation question
            print(f"[*] Re-asking query: '{unindexed_query}'")
            move_mouse_to_element(page, "#queryInput", steps=12)
            type_realistically(page, "#queryInput", unindexed_query)
            time.sleep(0.6)
            page.press("#queryInput", "Enter")

            # Wait for verified response
            page.wait_for_selector(".message-bubble.bot .msg-status-tag.verified", timeout=20000)
            time.sleep(1.0)
            inject_visual_cursor(page)

            # Showcase the new authoritative verified badge
            move_mouse_to_element(page, ".msg-status-tag.verified", steps=15)
            time.sleep(1.5)

            # Showcase the ₹1,000 deposit procedure and authority link
            move_mouse_to_element(page, ".knowledge-meta-box", steps=15)
            time.sleep(1.5)
            move_mouse_to_element(page, ".meta-portal-btn", steps=12)

            # Final lingering pause to let viewers appreciate the verified resolution
            print("[+] Successfully verified newly indexed convocation answer in live chat!")
            time.sleep(3.5)

            # Close context to finalize video writing
            print("[*] Finalizing Playwright video capture...")
            context.close()
            browser.close()

    finally:
        server_process.terminate()
        try:
            server_process.wait(timeout=3)
        except Exception:
            server_process.kill()

    # Find the recorded WebM file
    webm_files = list(RECORDINGS_DIR.glob("*.webm"))
    if not webm_files:
        raise FileNotFoundError(f"No WebM video was found in {RECORDINGS_DIR}")

    raw_webm = webm_files[0]
    print(f"[+] Raw video recorded: {raw_webm} ({raw_webm.stat().st_size:,} bytes)")

    # Convert to clean H.264 MP4 using FFmpeg
    print(f"[*] Converting {raw_webm.name} to crisp H.264 MP4: {FINAL_VIDEO_PATH} ...")
    ffmpeg_cmd = [
        str(FFMPEG_EXE),
        "-y",
        "-i", str(raw_webm),
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-movflags", "+faststart",
        str(FINAL_VIDEO_PATH)
    ]

    res = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("[!] FFmpeg conversion error:\n", res.stderr)
        raise RuntimeError("FFmpeg conversion failed.")

    print(f"\n[+] SUCCESS! Master walkthrough demo video created:")
    print(f"    File: {FINAL_VIDEO_PATH}")
    print(f"    Size: {FINAL_VIDEO_PATH.stat().st_size:,} bytes")

if __name__ == "__main__":
    record_walkthrough()

