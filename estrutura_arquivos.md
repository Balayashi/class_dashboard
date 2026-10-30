# 📁 Estrutura de Ficheiros do Projeto LG webOS

## 1. Árvore de Diretórios

Uma aplicação padrão para **LG webOS** é uma aplicação web autocontida empacotada no formato `.ipk`. Abaixo está a organização de ficheiros adotada no projeto:

```
class_dashboard/
├── appinfo.json             # Manifesto de metadados obrigatório do sistema LG webOS
├── index.html               # Estrutura DOM semântica otimizada para 1080p
├── css/
│   └── style.css            # Estilização TV-First (tipografia grande, contraste alto, animações)
├── js/
│   └── app.js               # Lógica de fetch da Google Sheet, parsing CSV e cálculo temporal
├── assets/
│   ├── icon.png             # Ícone oficial da app no menu/launcher da TV (80x80 px)
│   └── largeIcon.png        # Ícone de alta resolução para modelos modernos (130x130 px, opcional)
├── arquitetura_projeto.md   # Documentação: Fluxo de dados e arquitetura
├── estrutura_arquivos.md    # Documentação: Estrutura de ficheiros e empacotamento
└── regras_interface_tv.md   # Documentação: Diretrizes visuais e UX para Smart TV (10-foot UI)
```

---

## 2. Descrição Detalhada dos Componentes

| Ficheiro / Pasta | Função Principal | Requisitos Específicos webOS |
| :--- | :--- | :--- |
| **`appinfo.json`** | Manifesto da aplicação. Informa o sistema operativo webOS sobre a resolução, ponto de entrada e permissões. | **Obrigatório**. Deve conter `id` com notação de domínio inverso (ex: `com.escola.dashboard`), `main: "index.html"`, `type: "web"`. |
| **`index.html`** | Estrutura semântica do ecrã. Define o grid com a área de "ALERTAS URGENTES" e a grelha de "Horário & Calendário Geral". | Não deve depender de iframes bloqueados; deve respeitar safe-zones. |
| **`css/style.css`** | Folha de estilo 100% pensada para visualização a 3 metros (10-foot UI). | Tamanhos de fonte >= 24px, paleta escura (dark mode) para OLED/LCD, efeitos de pulsação e alto contraste. |
| **`js/app.js`** | O "cérebro" da aplicação. Faz o fetch da Google Sheet, calcula a diferença de dias e atualiza o DOM periodicamente. | Vanilla JavaScript (sem compilação necessária, rápida execução e baixo uso de memória no Chromium embebido). |
| **`assets/icon.png`** | Imagem do ícone da aplicação exibida na barra de lançador (Home Launcher) da LG. | Imagem PNG quadrada (80x80 px standard para webOS). |

---

## 3. Especificação do `appinfo.json`

O `appinfo.json` é o coração da integração com o sistema operativo webOS. Cada chave tem um propósito estrito:

```json
{
  "id": "com.escola.dashboard",
  "version": "1.0.0",
  "vendor": "Escola Dashboard",
  "type": "web",
  "main": "index.html",
  "title": "Dashboard Escolar",
  "icon": "assets/icon.png",
  "largeIcon": "assets/icon.png",
  "resolution": "1920x1080",
  "bgColor": "#121214",
  "transparent": false,
  "supportTouchMode": false,
  "network": true
}
```

- **`id`**: Identificador único global no ecossistema webOS.
- **`type: "web"`**: Indica que a aplicação deve ser executada dentro do web runtime (motor Chromium da TV).
- **`main: "index.html"`**: Ponto de arranque logo após o lançamento.
- **`resolution: "1920x1080"`**: Define a resolução nativa Full HD para evitar problemas de escala no motor gráfico.
- **`network: true`**: Declara formalmente a necessidade de ligação de rede (para consultar a Google Sheet).

---

## 4. Ciclo de Empacotamento e Teste (webOS CLI / webOS Studio)

Para instalar a aplicação numa TV LG física ou no simulador webOS:

1. **Empacotar a app (gera o ficheiro `.ipk`):**
   ```bash
   ares-package .
   # Resultado: com.escola.dashboard_1.0.0_all.ipk
   ```

2. **Instalar na TV (previamente configurada em Modo Desenvolvedor):**
   ```bash
   ares-install --device <nome-da-tv> com.escola.dashboard_1.0.0_all.ipk
   ```

3. **Iniciar a aplicação remotamente:**
   ```bash
   ares-launch --device <nome-da-tv> com.escola.dashboard
   ```

4. **Inspecionar e Depurar (Chrome DevTools remoto):**
   ```bash
   ares-inspect --device <nome-da-tv> --app com.escola.dashboard
   ```

