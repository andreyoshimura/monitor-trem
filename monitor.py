import requests
import os
import json
import hashlib
from bs4 import BeautifulSoup

URL = "https://www.diretodostrens.com.br/?id=6269987608068096"

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

STATE_FILE = "state.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

PROBLEM_STATUSES = [
    "velocidade reduzida",
    "operação parcial",
    "interrup",
    "paralis",
    "falha",
    "problema",
    "circulação suspensa"
]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    requests.post(url, json=payload, timeout=10)

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

def fetch_page():
    r = requests.get(URL, headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.text

def extract_text(html):
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(" ", strip=True).lower()

def detect_problem(text):
    if "operação normal" in text:
        return False
    return any(keyword in text for keyword in PROBLEM_STATUSES)

def hash_text(text):
    return hashlib.sha256(text.encode()).hexdigest()

def main():
    state = load_state()
    last_status = state["last_status"]
    last_hash = state["last_message_hash"]

    html = fetch_page()
    text = extract_text(html)

    current_hash = hash_text(text)
    has_problem = detect_problem(text)
    current_status = "PROBLEM" if has_problem else "NORMAL"

    if current_status != last_status or current_hash != last_hash:

        if current_status == "PROBLEM":
            send_telegram("⚠️ ALERTA: Problema detectado na Linha 11-Coral.")
        
        elif current_status == "NORMAL" and last_status == "PROBLEM":
            send_telegram("✅ Linha 11-Coral normalizada.")

        state["last_status"] = current_status
        state["last_message_hash"] = current_hash

        save_state(state)
        commit_state()

if __name__ == "__main__":
    main()
