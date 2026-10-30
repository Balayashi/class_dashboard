# 📺 Regras e Diretrizes de Interface para TV (10-Foot UI)

## 1. O Paradigma da "10-Foot UI" (Interface a 3 Metros)

Projetar para uma televisão é fundamentalmente diferente de projetar para desktop ou telemóvel:
- **Distância Crítica:** O utilizador está a 2,5 a 3,5 metros do ecrã (visão global, sem leitura próxima de pormenores).
- **Sem Interação Tátil ou Rato Preciso:** O controlo é feito por comando físico (D-Pad/setas) ou ponteiro giroscópico (LG Magic Remote).
- **Consumo Passivo de Informação:** No caso de um Dashboard Escolar, o ecrã deve funcionar como um painel "glanceable" — a informação mais crítica deve ser absorvida em menos de **3 segundos**.

---

## 2. Tipografia e Escala Visual

Textos pequenos (14px–18px) tornam-se completamente ilegíveis a 3 metros. Em 1080p (1920x1080), as dimensões mínimas recomendadas são:

| Elemento | Tamanho Mínimo | Peso | Objetivo Pedagógico |
| :--- | :--- | :--- | :--- |
| **Relógio / Contagem Decrescente** | 56px – 72px | Bold (700/800) | Referência visual imediata ao olhar para a sala |
| **Títulos de Secção Principal** | 36px – 48px | Semi-Bold (600) | Hierarquização espacial sem ambiguidades |
| **Títulos de Eventos / Disciplinas** | 28px – 34px | Semi-Bold (600) | Identificação clara da matéria escolar |
| **Metadados (Data, Hora, Local)** | 24px – 26px | Medium (500) | Leitura confortável sem esforço ocular |
| **Texto Secundário / Descrições** | 22px – 24px | Regular (400) | Limite inferior absoluto para visualização a 3 metros |

---

## 3. Zonas Seguras de Ecrã (Safe Zones & Overscan)

Muitas televisões LG (especialmente com configurações padrão de fábrica de aspecto de imagem) aplicam **Overscan** analógico/digital, cortando entre 2% a 5% das extremidades da imagem.

- **Regra de Ouro:** Nunca encostar conteúdo interativo ou textual às bordas da janela.
- **Title Safe Margin:** Margem mínima de segurança de **48px a 64px (aprox. 5%)** em toda a periferia (`top`, `bottom`, `left`, `right`).

```
+-----------------------------------------------------------+ 1920px
|  [OVERSCAN DANGER ZONE - 5% / 48px]                       |
|   +---------------------------------------------------+   |
|   |  TITLE & ACTION SAFE ZONE                         |   |
|   |                                                   |   |
|   |  [ ÁREA DE ALERTAS ]     [ CALENDÁRIO GERAL ]     |   |
|   |  (Prioridade Máxima)     (Próximas Semanas)       |   |
|   |                                                   |   |
|   +---------------------------------------------------+   | 1080px
|                                                           |
+-----------------------------------------------------------+
```

---

## 4. Paleta de Cores e Alto Contraste (OLED-Safe & Modo Noturno)

Ecrãs de televisão numa sala de estar ou sala de estudo não devem emitir luz branca excessiva (evita ofuscamento e cansaço visual).

- **Fundo Principal (Dark Background):** `#121214` ou `#0d1117` (Preto/Cinza Profundo). Poupa energia em painéis OLED e foca a atenção nos cartões.
- **Contraste de Texto:** Rácio mínimo de contraste **7:1 (WCAG AAA)**. Texto principal em branco puro (`#FFFFFF`) e texto de apoio em cinza claro (`#CBD5E1`).
- **Zona de Alerta de Proximidade (<= 2 dias):**
  - Fundo do Card de Alerta: Gradiente carmesim agressivo (`#DC2626` a `#991B1B`).
  - Badge de Destaque: Amarelo fluorescente ou branco puro com sombra intensa (`#FEE2E2`).
  - Animação: Pulsação sutil contínua com `@keyframes` usando apenas `transform: scale()` e `opacity` para aceleração por hardware (GPU) sem engasgos no chip da TV.

---

## 5. Divisão Espacial do Dashboard

A disposição dos ecrãs de TV é panorâmica (16:9). A melhor abordagem para um dashboard escolar é a divisão assimétrica em duas colunas:

1. **Coluna Esquerda (35% - 40% da largura) -> ZONA DE ALARME:**
   - Dedicada exclusivamente a **Testes e TPCs com prazo <= 2 dias**.
   - Se houver alertas críticos, esta coluna expande a sua proeminência com contadores em destaque: *"AMANHÃ!"* ou *"EM 2 DIAS!"*.
   - Se não houver alertas urgentes, exibe um estado calmo e reconfortante: *"Sem alertas críticos para os próximos 2 dias"*.

2. **Coluna Direita (60% - 65% da largura) -> HORÁRIO & CALENDÁRIO GERAL:**
   - Lista organizada dos eventos futuros (> 2 dias) e horários de aulas.
   - Cards com visual sóbrio (fundo `#1E293B`, bordas suaves `#334155`), transmitindo organização e previsibilidade.

