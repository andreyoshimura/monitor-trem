import os
import json
import asyncio
import requests
from datetime import datetime
from playwright.async_api import async_playwright

URL = "https://www.diretodostrens.com.br/?codigo=11"
STATE_FILE = "state.json"

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

VALID_STATUSES = [
    "operação normal",
    "velocidade reduzida",
    "operação parcial",
    "circulação suspensa"
]

async def fetch_page_text():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(URL, wait_until="networkidle")
        await page.wait_for_timeout(3000)
        text = await page.inner_text("body")
        await browser.close()
        return text.lower()

def parse_status(text):
    for status in VALID_STATUSES:
        if status in text:
            return status
    return "desconhecido"

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
    last_heartbeat = state["last_heartbeat_date"]

    text = await fetch_page_text()
    detected_status = parse_status(text)

    print(f"Status detectado: {detected_status}")

    if detected_status == "desconhecido":
        print("Status não identificado. Nenhuma ação tomada.")
        return

    if detected_status == "operação normal":
        current_status = "NORMAL"
    else:
        current_status = "PROBLEM"

    print(f"Estado interpretado: {current_status}")

    today = datetime.utcnow().strftime("%Y-%m-%d")

    # Alert on state change
    if current_status != last_status:
        if current_status == "PROBLEM":
            send_telegram(f"⚠️ ALERTA: Linha 11-Coral com status: {detected_status.upper()}")
        else:
            send_telegram("✅ Linha 11-Coral normalizada.")

        state["last_status"] = current_status

    # Daily heartbeat
    if last_heartbeat != today:
        send_telegram(f"🟢 Monitor ativo.
Status atual: {detected_status.upper()}")
        state["last_heartbeat_date"] = today

    save_state(state)
    commit_state()

if __name__ == "__main__":
    asyncio.run(main())
