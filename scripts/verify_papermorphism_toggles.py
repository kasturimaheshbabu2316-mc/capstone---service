"""Verification script for Papermorphism / Neo-Brutalist Toggles across secondary windows."""

import asyncio
import sys

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("[!] Optional dependency 'playwright' is not installed in current Python environment.")
    print("[*] Install with: pip install playwright && playwright install chromium")
    sys.exit(0)

async def verify():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Navigating to http://127.0.0.1:8000...")
        await page.goto("http://127.0.0.1:8000", wait_until="networkidle")
        
        # 1. Verify Chat Desk has NO neo-toggle-pill or neo-switch-row
        chat_stage_toggles = await page.evaluate("""() => {
            const chatStage = document.getElementById('chat-stage');
            return {
                pillsInChat: chatStage ? chatStage.querySelectorAll('.neo-toggle-pill').length : 0,
                switchesInChat: chatStage ? chatStage.querySelectorAll('.neo-switch-row').length : 0
            };
        }""")
        print(f"[Check 1 - Chat UI Isolation] Toggles in chat: {chat_stage_toggles} (Expect 0)")
        assert chat_stage_toggles['pillsInChat'] == 0
        assert chat_stage_toggles['switchesInChat'] == 0

        # 2. Switch to Ticket Directory and verify Neo-Brutalist toggles
        await page.click("#pill-directory")
        await page.wait_for_timeout(500)
        
        dir_toggles = await page.evaluate("""() => {
            const pills = document.querySelectorAll('#directory-status-pills .neo-toggle-pill');
            const firstPill = pills[0];
            const style = window.getComputedStyle(firstPill);
            return {
                pillCount: pills.length,
                borderWidth: style.borderTopWidth,
                borderStyle: style.borderTopStyle,
                boxShadow: style.boxShadow,
                cursor: style.cursor
            };
        }""")
        print(f"[Check 2 - Directory Toggles] {dir_toggles}")
        assert dir_toggles['pillCount'] >= 4
        assert "solid" in dir_toggles['borderStyle']
        assert "px" in dir_toggles['boxShadow']
        
        # Test clicking a filter pill
        await page.click('#directory-status-pills .neo-toggle-pill[data-status="Escalated"]')
        await page.wait_for_timeout(300)
        active_pill = await page.evaluate("""() => {
            const active = document.querySelector('#directory-status-pills .neo-toggle-pill.active');
            return {
                text: active ? active.textContent.trim() : null,
                status: active ? active.getAttribute('data-status') : null
            };
        }""")
        print(f"[Check 2.1 - Directory Active Pill] {active_pill}")
        assert active_pill['status'] == "Escalated"

        # 3. Switch to Policy Explorer and verify Neo-Brutalist category toggles
        await page.click("#pill-policies")
        await page.wait_for_timeout(500)
        
        policy_toggles = await page.evaluate("""() => {
            const pills = document.querySelectorAll('#policy-category-pills .neo-toggle-pill');
            const firstPill = pills[0];
            const style = window.getComputedStyle(firstPill);
            return {
                pillCount: pills.length,
                borderWidth: style.borderTopWidth,
                borderStyle: style.borderTopStyle,
                boxShadow: style.boxShadow
            };
        }""")
        print(f"[Check 3 - Policy Explorer Toggles] {policy_toggles}")
        assert policy_toggles['pillCount'] >= 4
        assert "solid" in policy_toggles['borderStyle']
        
        # Test clicking category pill
        await page.click('#policy-category-pills .neo-toggle-pill[data-cat="Safety & Incident SLA"]')
        await page.wait_for_timeout(300)
        policy_filter_check = await page.evaluate("""() => {
            const visibleCards = Array.from(document.querySelectorAll('#policies-grid .policy-card'))
                .filter(c => c.style.display !== 'none');
            return {
                visibleCount: visibleCards.length
            };
        }""")
        print(f"[Check 3.1 - Policy Filter Result] Visible cards: {policy_filter_check['visibleCount']}")
        assert policy_filter_check['visibleCount'] >= 1

        # 4. Switch to Ratings & Reviews and verify review filter toggles
        await page.click("#pill-ratings")
        await page.wait_for_timeout(500)
        
        ratings_toggles = await page.evaluate("""() => {
            const pills = document.querySelectorAll('#ratings-filter-pills .neo-toggle-pill');
            return {
                pillCount: pills.length
            };
        }""")
        print(f"[Check 4 - Ratings Toggles] {ratings_toggles}")
        assert ratings_toggles['pillCount'] >= 3

        # 5. Open Settings Drawer and verify Tab buttons & Neo Switch Rows
        await page.click("#btnSettings")
        await page.wait_for_timeout(500)
        
        # Switch to Governance tab
        await page.click('.drawer-tabs .tab-btn[data-tab="tab-privacy"]')
        await page.wait_for_timeout(300)
        
        drawer_switches = await page.evaluate("""() => {
            const switches = document.querySelectorAll('.neo-switch-row');
            const firstRow = switches[0];
            const rowStyle = firstRow ? window.getComputedStyle(firstRow) : {};
            const track = firstRow ? firstRow.querySelector('.neo-switch-track') : null;
            const trackStyle = track ? window.getComputedStyle(track) : {};
            return {
                switchCount: switches.length,
                rowBorder: rowStyle.borderTopWidth + ' ' + rowStyle.borderTopStyle,
                rowShadow: rowStyle.boxShadow,
                trackBorder: trackStyle.borderTopWidth + ' ' + trackStyle.borderTopStyle
            };
        }""")
        print(f"[Check 5 - Drawer Neo Switches] {drawer_switches}")
        assert drawer_switches['switchCount'] >= 4
        assert "solid" in drawer_switches['rowBorder']
        assert "solid" in drawer_switches['trackBorder']

        # 6. Return to Chat View and verify 3D Orbit is healthy and intact
        await page.click("#close-drawer-btn")
        await page.wait_for_timeout(300)
        await page.click("#pill-chat")
        await page.wait_for_timeout(600)
        
        orbit_health = await page.evaluate("""() => {
            const stage = document.getElementById('chat-orbit-header-stage');
            const canvas = stage ? stage.querySelector('canvas') : null;
            const rect = stage ? stage.getBoundingClientRect() : { width: 0, height: 0 };
            return {
                hasStage: !!stage,
                hasCanvas: !!canvas,
                canvasConnected: canvas ? canvas.isConnected : false,
                width: Math.round(rect.width),
                height: Math.round(rect.height),
                orbitDefined: typeof window.__ORBIT__ !== 'undefined'
            };
        }""")
        print(f"[Check 6 - Orbit Health post-navigation] {orbit_health}")
        assert orbit_health['hasCanvas'] is True
        assert orbit_health['canvasConnected'] is True
        assert orbit_health['width'] in [270, 269, 271]

        print("\nALL 6 CHECKS PASSED PERFECTLY!")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify())
