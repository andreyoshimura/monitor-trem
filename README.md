# Monitor CPTM -- Linha 11 (Coral)

Monitor automático do status da **Linha 11‑Coral** utilizando a API
oficial do app da CPTM.

API utilizada: https://api.cptm.sp.gov.br/AppCPTM/v1/Linhas/ObterStatus

------------------------------------------------------------------------

## Como funciona

1.  Consulta a API oficial da CPTM (JSON público).
2.  Filtra `linhaId == 11`.
3.  Interpreta o status:
    -   NORMAL → quando `status` = "Operação Normal"
    -   PROBLEM → qualquer outro status
4.  Envia alerta no Telegram somente quando houver mudança.
5.  Envia 1 heartbeat diário para confirmar que o monitor está ativo.
6.  Persiste estado em `state.json`.

------------------------------------------------------------------------

## Estrutura do projeto

-   monitor.py → Script principal
-   state.json → Estado persistido
-   requirements.txt → Dependências
-   .github/workflows/monitor.yml → GitHub Actions

------------------------------------------------------------------------

## Configuração

### 1️⃣ Criar Secrets no GitHub

Vá em: Settings → Secrets and variables → Actions

Crie:

-   BOT_TOKEN → Token do BotFather
-   CHAT_ID → ID do grupo ou canal (ex: -1001234567890)

------------------------------------------------------------------------

### 2️⃣ Executar manualmente

Actions → Train Monitor Linha 11 → Run workflow

------------------------------------------------------------------------

## Frequência

Por padrão roda a cada 5 minutos:

    */5 * * * *

Você pode alterar em: .github/workflows/monitor.yml

------------------------------------------------------------------------

## Como validar que está funcionando

No GitHub (log do workflow):

Deve aparecer:

    Status (texto): Operação Normal
    Estado interpretado: NORMAL

No Telegram:

Primeira execução envia:

    Monitor ativo (Linha 11-Coral). Status atual: Operação Normal

Depois disso, só envia mensagem se houver mudança de estado.

------------------------------------------------------------------------

## Arquitetura

-   Sem Playwright
-   Sem scraping
-   Sem token privado
-   Sem engenharia reversa
-   Apenas JSON oficial da CPTM

Execução média: \~1 segundo

## Roadmap

Adicionar a contigência de api 
https://ccm.artesp.sp.gov.br/metroferroviario/api/status/

------------------------------------------------------------------------

Gerado em: 2026-02-24 02:32:17 UTC
