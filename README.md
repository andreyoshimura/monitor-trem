# Monitor CPTM – Linha 11 (Coral) – Telegram + GitHub Actions

Este projeto monitora o **status da Linha 11 (Coral)** usando a **API do app oficial da CPTM** e envia alertas para um **grupo/canal no Telegram** via bot.

## Como funciona
- Consulta JSON em: `https://api.cptm.sp.gov.br/AppCPTM/v1/Linhas/ObterStatus`
- Filtra a linha pelo campo `linhaId == 11`
- Interpreta:
  - **NORMAL** apenas quando `status` for `Operação Normal`
  - **PROBLEM** para qualquer outro status
- Envia alerta **somente quando muda** (NORMAL ↔ PROBLEM)
- Envia 1 **heartbeat diário** para comprovar que está rodando
- Se a API falhar / JSON mudar e não der para extrair status → **não alerta** (evita falso positivo)

## Setup (GitHub)
1. Faça upload destes arquivos no seu repositório.
2. Vá em **Settings → Secrets and variables → Actions → New repository secret** e crie:
   - `BOT_TOKEN` (token do BotFather)
   - `CHAT_ID` (id do grupo/canal/chat, ex: `-1001234567890`)
3. Vá em **Actions** e rode manualmente:
   - `Train Monitor Linha 11` → **Run workflow**

## Frequência
O workflow roda a cada 5 minutos (cron):
- `.github/workflows/monitor.yml` → `*/5 * * * *`

Se quiser menos carga, use `*/10 * * * *` (10 min) ou `*/15 * * * *` (15 min).

## Como validar que está funcionando
No GitHub:
- **Actions → Train Monitor Linha 11 → (última execução) → Run monitor**
- Você deve ver no log:
  - `Status (texto): ...`
  - `Estado interpretado: ...`

No Telegram:
- Você receberá 1 mensagem diária tipo:
  - `🟢 Monitor ativo (Linha 11-Coral). Status atual: Operação Normal`

## Arquivos
- `monitor.py` → script principal
- `state.json` → estado persistido (último status e último heartbeat)
- `.github/workflows/monitor.yml` → GitHub Actions
- `requirements.txt` → dependências

## Observação
O script faz commit/push do `state.json` para persistir estado entre execuções do GitHub Actions.
