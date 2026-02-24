#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitor CPTM Linha 11 (Direto dos Trens) -> Telegram

Estratégia:
- Abre a página com Playwright
- Intercepta respostas XHR JSON do backend (direto-dos-trens.rj.appspot.com)
- Extrai "situacao" / "descricao" da Linha 11
- Só alerta quando muda de NORMAL <-> PROBLEM
- Heartbeat 1x/dia ("Monitor ativo")
"""

import asyncio
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional

import requests
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# ----------------------------
# Config
# ----------------------------
LINE_CODE = "11"  # Linha 11 Coral
PAGE_URL = f"https://www.diretodostrens.com.br/?codigo={LINE_CODE}"
STATE_FILE = "state.json"

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")

# "Operação Normal" pode vir com/sem acento ou variações de caixa
NORMAL_ALIASES = {
    "operacao normal",
    "operação normal",
    "operacao_normal",
    "operação_normal",
    "normal",
}

# Captura respostas JSON do backend do site
BACKEND_HOST_RE = re.compile(r"^https://direto-dos-trens\.rj\.appspot\.com/")

# ----------------------------
# Telegram
# ----------------------------
def send_telegram(message: str) -> None:
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram não configurado (BOT_TOKEN/CHAT_ID ausentes). Mensagem seria:")
        print(message)
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resp = requests.post(
        url,
        json={"chat_id": CHAT_ID, "text": message},
        timeout=15,
    )
    if resp.status_code >= 300:
        raise RuntimeError(f"Falha ao enviar Telegram: {resp.status_code} {resp.text}")


# ----------------------------
# State
# ----------------------------
def load_state() -> Dict[str, Any]:
    if not os.path.exists(STATE_FILE):
        return {"last_status": "UNKNOWN", "last_heartbeat_date": ""}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # Se corromper, não derruba o monitor
        return {"last_status": "UNKNOWN", "last_heartbeat_date": ""}


def save_state(state: Dict[str, Any]) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ----------------------------
# Parsing / interpretação
# ----------------------------
def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip()).lower()


def interpret_state(situacao: str) -> str:
    """
    Retorna "NORMAL" ou "PROBLEM".
    Se situacao for vazia, retorna "UNKNOWN".
    """
    if not situacao:
        return "UNKNOWN"
    n = normalize(situacao)
    if n in NORMAL_ALIASES:
        return "NORMAL"
    # Se vier algo como "Operação Normal - com restrições", ainda é "problema".
    if "operacao normal" in n or "operação normal" in n:
        # normal "puro" já foi pego acima; aqui pegamos variações que geralmente indicam alteração
        return "PROBLEM"
    return "PROBLEM"


# ----------------------------
# Coleta via Playwright (XHR JSON)
# ----------------------------
async def fetch_status_json(timeout_ms: int = 20000) -> Optional[Dict[str, Any]]:
    """
    Abre a página e tenta capturar um JSON de status vindo do backend.
    Retorna um dict com chaves relevantes quando achar.
    """

    captured: Dict[str, Any] = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            locale="pt-BR",
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        )
        page = await context.new_page()

        # Handler de resposta
        async def on_response(response):
            nonlocal captured
            url = response.url
            if not BACKEND_HOST_RE.match(url):
                return

            # Só interessa XHR/fetch com JSON
            try:
                ct = (response.headers.get("content-type") or "").lower()
            except Exception:
                ct = ""

            if "application/json" not in ct:
                return

            try:
                data = await response.json()
            except Exception:
                return

            # Esperamos algo contendo "situacao" e "linha" ou algo próximo
            # (o backend pode devolver listas/objetos diferentes)
            candidate = extract_candidate_status(data)
            if candidate:
                captured = candidate

        page.on("response", on_response)

        try:
            await page.goto(PAGE_URL, wait_until="domcontentloaded", timeout=timeout_ms)
            # Aguarda até capturar algo
            start = datetime.utcnow()
            while not captured:
                await asyncio.sleep(0.25)
                elapsed = (datetime.utcnow() - start).total_seconds() * 1000
                if elapsed > timeout_ms:
                    break
        except PlaywrightTimeoutError:
            pass
        finally:
            await context.close()
            await browser.close()

    return captured or None


def extract_candidate_status(data: Any) -> Optional[Dict[str, Any]]:
    """
    Tenta achar um objeto com campos típicos:
    - situacao (string)
    - descricao (string)
    - linha (string/number)
    Pode estar aninhado, em lista, etc.
    """

    def is_candidate(obj: Dict[str, Any]) -> bool:
        # Campos mais comuns que já vimos/esperamos
        if not isinstance(obj, dict):
            return False
        situacao = obj.get("situacao") or obj.get("situacaoAtual") or obj.get("status")
        linha = obj.get("linha") or obj.get("codigo") or obj.get("line") or obj.get("idLinha")
        # Aceita se tiver situacao e alguma indicação de linha
        if isinstance(situacao, str) and situacao.strip():
            if linha is None:
                # Sem linha explícita, ainda pode ser o endpoint específico da linha
                return True
            # Linha pode vir como "11" ou 11
            if str(linha).strip() == LINE_CODE:
                return True
        return False

    def pick(obj: Dict[str, Any]) -> Dict[str, Any]:
        situacao = obj.get("situacao") or obj.get("situacaoAtual") or obj.get("status") or ""
        descricao = obj.get("descricao") or obj.get("mensagem") or obj.get("detail") or ""
        linha = obj.get("linha") or obj.get("codigo") or obj.get("line") or obj.get("idLinha") or LINE_CODE
        return {"linha": str(linha), "situacao": str(situacao), "descricao": str(descricao)}

    # BFS/DFS na estrutura para achar o primeiro candidato "bom"
    stack = [data]
    seen = 0
    while stack and seen < 5000:
        seen += 1
        cur = stack.pop()
        if isinstance(cur, dict):
            if is_candidate(cur):
                return pick(cur)
            # Explora valores
            for v in cur.values():
                if isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(cur, list):
            for it in cur:
                if isinstance(it, (dict, list)):
                    stack.append(it)

    return None


# ----------------------------
# Main
# ----------------------------
async def main() -> None:
    state = load_state()
    last_status = state.get("last_status", "UNKNOWN")
    last_heartbeat = state.get("last_heartbeat_date", "")

    status_json = await fetch_status_json()
    if not status_json:
        print("Nenhum JSON de status foi capturado. Nenhuma ação tomada.")
        return

    situacao = status_json.get("situacao", "")
    descricao = status_json.get("descricao", "")
    print(f"JSON capturado: linha={status_json.get('linha')} situacao={situacao} descricao={descricao}")

    current_status = interpret_state(situacao)
    print(f"Estado interpretado: {current_status}")

    today = datetime.utcnow().strftime("%Y-%m-%d")

    # Alertar apenas em mudança de estado
    if current_status != "UNKNOWN" and current_status != last_status:
        if current_status == "PROBLEM":
            send_telegram(
                f"⚠️ ALERTA – Linha {LINE_CODE} com problema\n"
                f"Situação: {situacao}\n"
                f"Descrição: {descricao or '-'}\n"
                f"Fonte: {PAGE_URL}"
            )
        elif current_status == "NORMAL":
            send_telegram(
                f"✅ Linha {LINE_CODE} normalizada\n"
                f"Situação: {situacao}\n"
                f"Fonte: {PAGE_URL}"
            )
        state["last_status"] = current_status

    # Heartbeat diário (para provar que está rodando)
    if last_heartbeat != today:
        send_telegram(f"🟢 Monitor ativo – Linha {LINE_CODE} – Situação: {situacao or 'N/A'}")
        state["last_heartbeat_date"] = today

    save_state(state)


if __name__ == "__main__":
    asyncio.run(main())
