import os
import json
import asyncio
import requests
from playwright.async_api import async_playwright

URL = "https://www.diretodostrens.com.br/?codigo=11"
STATE_FILE = "state.json"

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

NORMAL_STATUS = "operação normal"

async def fetch_status():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(URL, wait_until="networkidle")
        await page.wait_for_timeout(5000)
        content = await page.content()
        await browser.close()
        return content.lower()

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": message
    }, timeout=10)

def load_state():
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def commit_state():
    os.system("git config user.name 'github-actions'")
    os.system("git config user.email 'actions@github.com'")
    os.system("git add state.json")
    os.system("git commit -m 'update state' || exit 0")
    os.system("git push")

async def main():
    state = load_state()
    last_status = state["last_status"]

    text = await fetch_status()

    current_status = "NORMAL" if NORMAL_STATUS in text else "PROBLEM"

    if current_status != last_status:
        if current_status == "PROBLEM":
            send_telegram("⚠️ ALERTA: Linha 11-Coral com problema.")
        else:
            send_telegram("✅ Linha 11-Coral normalizada.")

        state["last_status"] = current_status
        save_state(state)
        commit_state()

if __name__ == "__main__":
    asyncio.run(main())
