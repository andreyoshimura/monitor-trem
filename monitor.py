import os
import json
import asyncio
import requests
import unicodedata
from datetime import datetime
from playwright.async_api import async_playwright

# ----------------------------
# CONFIGURAÇÕES
# ----------------------------

URL = "https://www.diretodostrens.com.br/?codigo=11"
STATE_FILE = "state.json"

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

# Status que consideramos válidos
VALID_STATUSES = [
    "operacao normal",
    "velocidade reduzida",
    "operacao parcial",
    "circulacao suspensa"
]


# ----------------------------
# FUNÇÕES AUXILIARES
# ----------------------------

def normalize(text: str) -> str:
    """
    Normaliza texto:
    - Lowercase
    - Remove acentos
    """
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore").decode("utf-8")
    return text


def send_telegram(message: str):
    """
    Envia mensagem para o Telegram
    """
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(
        url,
        json={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=10
    )


def load_state():
    """
    Carrega estado persistido
    """
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    """
    Salva estado local
    """
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def commit_state():
    """
    Commit do state.json para manter persistência
    """
    os.system("git config user.name 'github-actions'")
    os.system("git config user.email 'actions@github.com'")
    os.system("git add state.json")
    os.system("git commit -m 'update state' || exit 0")
    os.system("git push")


# ----------------------------
# PLAYWRIGHT
# ----------------------------

async def fetch_page_text():
    """
    Abre navegador headless,
    espera renderização JS,
    retorna texto normalizado.
    """

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Carrega página
        await page.goto(URL, wait_until="domcontentloaded")

        # Aguarda JS terminar de renderizar
        await page.wait_for_timeout(5000)

        # Captura texto visível da página
        text = await page.locator("body").inner_text()

        await browser.close()

        return normalize(text)


def parse_status(text: str) -> str:
    """
    Procura status válido dentro do texto da página
    """
    for status in VALID_STATUSES:
        if status in text:
            return status

    return "desconhecido"


# ----------------------------
# MAIN
# ----------------------------

async def main():

    state = load_state()
    last_status = state.get("last_status", "UNKNOWN")
    last_heartbeat = state.get("last_heartbeat_date", "")

    # Busca página
    text = await fetch_page_text()

    # Detecta status
    detected_status = parse_status(text)

    print(f"Status detectado: {detected_status}")

    if detected_status == "desconhecido":
        print("Status não identificado. Nenhuma ação tomada.")
        return

    # Interpretação de estado
    if detected_status == "operacao normal":
        current_status = "NORMAL"
    else:
        current_status = "PROBLEM"

    print(f"Estado interpretado: {current_status}")

    today = datetime.utcnow().strftime("%Y-%m-%d")

    # ----------------------------
    # ALERTA EM MUDANÇA DE ESTADO
    # ----------------------------

    if current_status != last_status:

        if current_status == "PROBLEM":
            send_telegram(
                f"⚠️ ALERTA: Linha 11-Coral com status: {detected_status.upper()}"
            )
        else:
            send_telegram("✅ Linha 11-Coral normalizada.")

        state["last_status"] = current_status

    # ----------------------------
    # HEARTBEAT DIÁRIO
    # ----------------------------

    if last_heartbeat != today:
        send_telegram(
            f"🟢 Monitor ativo. Status atual: {detected_status.upper()}"
        )
        state["last_heartbeat_date"] = today

    # Salva estado
    save_state(state)
    commit_state()


if __name__ == "__main__":
    asyncio.run(main())
