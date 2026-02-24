# 🚆 Monitor Linha 11-Coral (CPTM)

Monitor automático da Linha 11-Coral via site Direto dos Trens.

- Roda no GitHub Actions
- Usa Playwright (browser real)
- Envia alerta no Telegram somente quando o status muda
- Envia 1 mensagem diária confirmando que está ativo
- Evita falso positivo
- Sem spam

---

## 🔎 O que ele monitora

URL monitorada:

https://www.diretodostrens.com.br/?codigo=11

Status reconhecidos:

- Operação normal
- Velocidade reduzida
- Operação parcial
- Circulação suspensa

---

## 🚨 Quando envia alerta

### Envia mensagem quando:

- NORMAL → PROBLEM
- PROBLEM → NORMAL

### Envia também:

1 heartbeat diário:

🟢 Monitor ativo.
Status atual: OPERAÇÃO NORMAL

---

## 📁 Estrutura do projeto

train-monitor/
│
├── monitor.py
├── requirements.txt
├── state.json
└── .github/workflows/monitor.yml

---

## ⚙️ Configuração

### 1️⃣ Criar Bot no Telegram

1. Falar com @BotFather  
2. Criar bot com /newbot  
3. Copiar o BOT_TOKEN  

Adicionar o bot no grupo.

Obter CHAT_ID usando:

https://api.telegram.org/botSEU_TOKEN/getUpdates

---

### 2️⃣ Configurar Secrets no GitHub

Repositório → Settings → Secrets and variables → Actions

Adicionar:

- BOT_TOKEN
- CHAT_ID

---

### 3️⃣ Executar

Ir em:

Actions → Train Monitor Linha 11 → Run workflow

---

## ⏱ Frequência

O monitor roda a cada 10 minutos.

---

## 🧠 Como funciona

1. GitHub Actions roda o workflow
2. Container oficial Playwright já com Chromium
3. Abre navegador headless
4. Extrai status real renderizado
5. Compara com estado anterior
6. Decide se envia alerta
7. Atualiza state.json

---

## 📊 Logs

Nos logs do GitHub você verá:

Status detectado: operação normal
Estado interpretado: NORMAL

Isso confirma que está funcionando mesmo sem alerta.

---

## 🔐 Segurança

- Token e Chat ID ficam em Secrets
- Nenhuma credencial no código
- Projeto pode ser público com segurança

---

## 📌 Observação

Se o site mudar estrutura ou texto dos status,
o parser pode precisar de ajuste.
