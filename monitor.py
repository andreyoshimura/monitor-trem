import os
import json
import asyncio
import requests
from datetime import datetime
from playwright.async_api import async_playwright

STATE_FILE = "state.json"

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

URL = "https://www.diretodostrens.com.br/?codigo=11"


# ----------------------------
# Telegram
# ----------------------------

def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(
        url,
        json={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=10
    )


# ----------------------------
# State
# ----------------------------

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


# ----------------------------
# Playwright (captura JSON real)
# ----------------------------

async def fetch_status_from_api():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        status_value = None

        async def handle_response(response):
            nonlocal status_value

            if "/api/status/codigo/11" in response.url:
                try:
                    data = await response.json()
                    # Ajuste aqui se o campo for diferente
                    status_value = data.get("status")
                except:
                    pass

        page.on("response", handle_response)

        await page.goto(URL, wait_until="networkidle")

        # Aguarda até 10 segundos a API responder
        for _ in range(20):
            if status_value:
                break
            await page.wait_for_timeout(500)

        await browser.close()

        return status_value


# ----------------------------
# MAIN
# ----------------------------

async def main():

    state = load_state()
    last_status = state.get("last_status", "UNKNOWN")
    last_heartbeat = state.get("last_heartbeat_date", "")

    detected_status = await fetch_status_from_api()

    print(f"Status detectado: {detected_status}")

    if not detected_status:
        print("Não foi possível capturar status.")
        return

    if detected_status.lower() == "operação normal":
        current_status = "NORMAL"
    else:
        current_status = "PROBLEM"

    print(f"Estado interpretado: {current_status}")

    today = datetime.utcnow().strftime("%Y-%m-%d")

    # Mudança de estado
    if current_status != last_status:

        if current_status == "PROBLEM":
            send_telegram(
                f"⚠️ ALERTA: Linha 11-Coral com status: {detected_status.upper()}"
            )
        else:
            send_telegram("✅ Linha 11-Coral normalizada.")

        state["last_status"] = current_status

    # Heartbeat diário
    if last_heartbeat != today:
        send_telegram(
            f"🟢 Monitor ativo. Status atual: {detected_status.upper()}"
        )
        state["last_heartbeat_date"] = today

    save_state(state)
    commit_state()


if __name__ == "__main__":
    asyncio.run(main())
