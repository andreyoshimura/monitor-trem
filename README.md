# Monitor CPTM – Linha 11 Coral (Telegram)

Monitora a situação da **Linha 11 (Coral)** no site **Direto dos Trens** e envia alerta no Telegram **somente quando muda para PROBLEMA** (e opcionalmente quando normaliza).

## Como funciona (sem token / sem API privada)
O site carrega os dados via chamadas XHR para um backend (Firebase/App Engine).  
Este projeto usa **Playwright** para abrir a página e **capturar a resposta JSON dessas chamadas**, evitando:
- falso positivo por texto de cookie/ads,
- mudanças de layout do HTML.

## Pré-requisitos
- Um bot do Telegram (token do BotFather)
- O `chat_id` (grupo ou usuário)

## Configurar no GitHub
1. Suba este repositório no GitHub.
2. Vá em **Settings → Secrets and variables → Actions → New repository secret** e crie:
   - `BOT_TOKEN` = token do bot
   - `CHAT_ID` = id do chat (grupo/usuário)

## Rodar manualmente
Actions → **Train Monitor Linha 11** → **Run workflow**

## Agendamento
O workflow roda a cada 5 minutos (ajuste em `.github/workflows/monitor.yml`).

## O que é considerado “problema”
Qualquer `situacao` diferente de **Operação Normal** (com ou sem acento) vira `PROBLEM`.

Estados desconhecidos (sem JSON válido) são ignorados (não alertam).

## Mensagens
- Alerta (mudou NORMAL → PROBLEM)
- Normalizou (mudou PROBLEM → NORMAL)
- Heartbeat (1x/dia): “Monitor ativo …”

## Arquivos principais
- `monitor.py` – captura JSON e envia Telegram
- `state.json` – guarda `last_status` e `last_heartbeat_date`
- `.github/workflows/monitor.yml` – GitHub Actions

## Debug rápido
Se precisar debugar, rode manualmente e abra o log:
Actions → execução → job `monitor` → step `Run monitor`

Você deve ver algo como:
- `JSON capturado: situacao=Operação Normal …`
- `Estado interpretado: NORMAL`

Se aparecer `Nenhum JSON de status foi capturado`, o site pode ter mudado o endpoint (ajustar filtro de URL/JSON).

