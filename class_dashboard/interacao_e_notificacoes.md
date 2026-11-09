# 🔄 Arquitetura de Interação Bidirecional: webOS TV -> Google Sheets -> Notificações

## 1. Visão Geral do Ciclo Bidirecional

```
  ┌────────────────────────────────────────────────────────┐
  │                   LG webOS Smart TV                    │
  │  1. Aluno navega com D-Pad (Comando da TV)             │
  │  2. Seleciona o TPC e pressiona botão "OK"             │
  │  3. UI atualiza instantaneamente (Pisco verde ✅)       │
  └──────────────────────────┬─────────────────────────────┘
                             │
                             │ HTTP POST / GET (JSON)
                             ▼
  ┌────────────────────────────────────────────────────────┐
  │           Google Apps Script Web App (Webhook)         │
  │  4. Localiza a linha do TPC na Google Sheet            │
  │  5. Atualiza a coluna "Estado" para "Concluído"        │
  │  6. Dispara alerta automático para o Encarregado       │
  └──────────────────────────┬─────────────────────────────┘
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
┌────────────────────────┐       ┌────────────────────────┐
│     Google Sheets      │       │ Notificação no Telemóvel│
│  Coluna Estado = "OK"  │       │  E-mail / Notificação   │
│  Data/Hora Conclusão   │       │  "TPC Concluído! 🎉"    │
└────────────────────────┘       └────────────────────────┘
```

---

## 2. Horário Oficial Integrado (Turma 5º G - EB Pedro Jacques de Magalhães)

Mapeamento completo do horário escolar extraído do documento oficial:

| Tempo | Horário | Segunda-feira | Terça-feira | Quarta-feira | Quinta-feira | Sexta-feira |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **T1** | 08:15 - 09:05 | HGP *(S08)* | Matemática *(S08)* | EV *(EVT01)* | EF *(C2)* | Matemática *(S08)* |
| **T2** | 09:15 - 10:05 | Inglês *(S08)* | Matemática *(S08)* | EV *(EVT01)* | EF *(C2)* | CN *(S08)* |
| **T3** | 10:20 - 11:10 | CD / TIC *(INF01/02)* | Português *(S08)* | Inglês *(EVT02)* | Inglês *(S08)* | Português *(S08)* |
| **T4** | 11:20 - 12:10 | Matemática *(S08)* | CN *(S08)* | Português *(S08)* | HGP *(S08)* | Português *(S08)* |
| **T5** | 12:15 - 13:05 | *Almoço* | HGP *(S08)* | Apoio Estudo Port. *(S08)* | CN *(S08)* | Apoio Estudo Mat. *(S08)* |
| **T6** | 13:15 - 14:05 | ET *(EVT01)* | *Almoço* | *Almoço* | *Almoço* | *Fim das aulas* |
| **T7** | 14:15 - 15:05 | ET *(EVT01)* | *Livre* | DTA *(S08)* | *Livre* | - |
| **T8** | 15:15 - 16:05 | EF *(C1)* | Ed. Musical *(EM01)* | *Fim das aulas* | *Fim das aulas* | - |

> **Comportamento Inteligente no Dashboard:**
> O painel deteta o dia da semana atual (`new Date().getDay()`) e renderiza automaticamente as aulas desse dia. Durante o fim de semana (sábado e domingo), projeta o horário de **Segunda-feira** para permitir a preparação da mochila com antecedência!

