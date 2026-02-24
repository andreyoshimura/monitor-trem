#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitor de status da CPTM (Linha 11 - Coral) via API oficial do app da CPTM.

Fonte de dados (JSON):
  https://api.cptm.sp.gov.br/AppCPTM/v1/Linhas/ObterStatus

Lógica de alerta:
  - Só alerta quando houver mudança de estado (NORMAL <-> PROBLEM)
  - Envia heartbeat diário para comprovar que está rodando
  - Se não conseguir obter/interpretar o status, NÃO alerta (evita falso positivo)

Requisitos (secrets do GitHub):
  - BOT_TOKEN: token do bot Telegram
  - CHAT_ID: id do grupo/canal/chat (ex: -1001234567890)

Observação:
  - Este script faz commit/push do state.json para persistir estado entre execuções do Actions.
"""

import os
import json
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import requests

API_URL = "https://api.cptm.sp.gov.br/AppCPTM/v1/Linhas/ObterStatus"
LINE_ID = 11  # Linha 11 - Coral

STATE_FILE = "state.json"

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")


# -----------------------------
# Telegram
# -----------------------------
def send_telegram(message: str) -> None:
    """Envia mensagem ao Telegram. Se credenciais não existirem, só loga."""
    if not BOT_TOKEN or not CHAT_ID:
        print("[WARN] BOT_TOKEN/CHAT_ID não configurados. Mensagem não enviada.")
        print("[TELEGRAM-MSG]", message)
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(
        url,
        json={"chat_id": CHAT_ID, "text": message},
        timeout=15,
    )
    r.raise_for_status()


# -----------------------------
# State
# -----------------------------
def load_state() -> Dict[str, Any]:
    """Carrega estado persistido."""
    if not os.path.exists(STATE_FILE):
        return {"last_status": "UNKNOWN", "last_heartbeat_date": ""}

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            if not isinstance(data, dict):
                return {"last_status": "UNKNOWN", "last_heartbeat_date": ""}
            data.setdefault("last_status", "UNKNOWN")
            data.setdefault("last_heartbeat_date", "")
            return data
        except json.JSONDecodeError:
            return {"last_status": "UNKNOWN", "last_heartbeat_date": ""}


def save_state(state: Dict[str, Any]) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def commit_state_if_changed() -> None:
    """Commita/pusha state.json no GitHub Actions para persistir estado."""
    # Se não estiver em git, ignore.
    if not os.path.isdir(".git"):
        print("[INFO] Repositório git não encontrado. Não vou commitar state.json.")
        return

    # Verifica se houve mudança
    diff = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if diff.returncode != 0:
        print("[WARN] git status falhou. Não vou commitar.")
        return

    if "state.json" not in diff.stdout:
        print("[INFO] state.json não mudou. Nada a commitar.")
        return

    subprocess.run(["git", "config", "user.name", "github-actions"], check=False)
    subprocess.run(["git", "config", "user.email", "actions@github.com"], check=False)
    subprocess.run(["git", "add", "state.json"], check=False)
    subprocess.run(["git", "commit", "-m", "chore: update state"], check=False)
    subprocess.run(["git", "push"], check=False)


# -----------------------------
# CPTM API
# -----------------------------
def fetch_all_lines_status() -> Optional[Any]:
    """Baixa JSON com status de todas as linhas."""
    try:
        r = requests.get(API_URL, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[ERROR] Falha ao consultar API: {e}")
        return None


def extract_line11_status(payload: Any) -> Optional[Tuple[str, str]]:
    """Extrai (status, descricao) da linha 11 a partir do JSON da API."""
    if not isinstance(payload, list):
        return None

    for item in payload:
        if not isinstance(item, dict):
            continue
        if item.get("linhaId") == LINE_ID:
            status = item.get("status")
            descricao = item.get("descricao") or ""
            if isinstance(status, str) and status.strip():
                return status.strip(), str(descricao).strip()
            return None

    return None


def normalize_status_text(s: str) -> str:
    """Normaliza status para comparação (minúsculo e sem espaços extras)."""
    return " ".join(s.lower().strip().split())


def interpret_state(status_text: str) -> str:
    """Mapeia texto de status para NORMAL/PROBLEM."""
    norm = normalize_status_text(status_text)
    # Considera NORMAL apenas quando a CPTM informar 'Operação Normal'
    # (com ou sem acento, dependendo da origem)
    if norm in {"operação normal", "operacao normal"}:
        return "NORMAL"
    return "PROBLEM"


# -----------------------------
# MAIN
# -----------------------------
def main() -> None:
    state = load_state()
    last_state = state.get("last_status", "UNKNOWN")
    last_heartbeat = state.get("last_heartbeat_date", "")

    payload = fetch_all_lines_status()
    line_status = extract_line11_status(payload)

    if not line_status:
        # Não alerta — evita falso positivo quando API falha ou formato muda
        print("[WARN] Não consegui extrair status da Linha 11 no JSON. Nenhuma ação.")
        return

    status_text, descricao = line_status
    current_state = interpret_state(status_text)

    print(f"Status (texto): {status_text}")
    print(f"Descrição: {descricao}")
    print(f"Estado interpretado: {current_state} (anterior: {last_state})")

    # Mudança de estado -> alerta
    if current_state != last_state:
        if current_state == "PROBLEM":
            msg = f"⚠️ ALERTA: Linha 11-Coral: {status_text}"
            if descricao:
                msg += f" — {descricao}"
            send_telegram(msg)
        else:
            send_telegram("✅ Linha 11-Coral normalizada (Operação Normal).")
        state["last_status"] = current_state

    # Heartbeat diário -> prova de vida sem depender de incidente
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if last_heartbeat != today:
        hb = f"🟢 Monitor ativo (Linha 11-Coral). Status atual: {status_text}"
        if descricao:
            hb += f" — {descricao}"
        send_telegram(hb)
        state["last_heartbeat_date"] = today

    save_state(state)
    commit_state_if_changed()


if __name__ == "__main__":
    main()
