/**
 * ============================================================================
 * DASHBOARD ESCOLAR - MOTOR PRINCIPAL JAVASCRIPT (LG webOS)
 * ============================================================================
 * Responsável por:
 * 1. Manter o relógio e a data em tempo real (1080p Kiosk display).
 * 2. Efetuar o fetch da Google Sheet (CSV público) ou recorrer a dados de fallback.
 * 3. Calcular a diferença exata de dias usando Date nativo.
 * 4. Categorizar e injetar eventos na zona de "ALERTAS URGENTES" (<= 2 dias)
 *    com estilização agressiva ou no "CALENDÁRIO GERAL" (> 2 dias).
 * ============================================================================
 */

// ----------------------------------------------------------------------------
// 1. CONFIGURAÇÕES GLOBAIS
// ----------------------------------------------------------------------------
const CONFIG = {
  // Substitua pelo URL da sua folha de cálculo Google publicada em formato CSV:
  // Ficheiro > Partilhar > Publicar na Web > Escolher folha > Formato: Valores separados por vírgulas (.csv)
  GOOGLE_SHEET_CSV_URL: "", 
  
  // Intervalo de sincronização com a Google Sheet (5 minutos = 300.000 ms)
  REFRESH_INTERVAL_MS: 5 * 60 * 1000,
  
  // Limiar de dias para acionar o alarme de proximidade
  URGENT_THRESHOLD_DAYS: 2
};

// ----------------------------------------------------------------------------
// 2. DADOS DE FALLBACK (DEMONSTRAÇÃO AUTOMÁTICA FORA DA REDE OU ANTES DO URL)
// ----------------------------------------------------------------------------
function getMockEvents() {
  const now = new Date();
  const formatDate = (daysAhead) => {
    const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() + daysAhead);
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  };

  return [
    {
      tipo: "Teste",
      disciplina: "Matemática",
      titulo: "Geometria Analítica e Vetores",
      data: formatDate(0), // HOJE (Alerta Máximo)
      hora: "10:30",
      descricao: "Calculadora gráfica e régua obrigatórias. Sala 12."
    },
    {
      tipo: "TPC",
      disciplina: "Português",
      titulo: "Ensaio sobre Os Lusíadas (Canto IV)",
      data: formatDate(1), // AMANHÃ (Alerta Crítico)
      hora: "23:59",
      descricao: "Submissão no Classroom até à meia-noite (máx. 500 palavras)."
    },
    {
      tipo: "Teste",
      disciplina: "Físico-Química",
      titulo: "Termodinâmica e Ondas Sonoras",
      data: formatDate(2), // EM 2 DIAS (Alerta Proximidade)
      hora: "08:30",
      descricao: "Formulário oficial fornecido pelo professor."
    },
    {
      tipo: "Trabalho",
      disciplina: "História",
      titulo: "Apresentação: Revolução Industrial",
      data: formatDate(5), // 5 dias (Calendário Geral)
      hora: "14:00",
      descricao: "Apresentação em grupo com slides (15 minutos)."
    },
    {
      tipo: "TPC",
      disciplina: "Inglês",
      titulo: "Reading Comprehension Unit 4",
      data: formatDate(8), // 8 dias (Calendário Geral)
      hora: "09:00",
      descricao: "Exercícios 1 a 6 do Manual de Atividades (Pág. 54)."
    },
    {
      tipo: "Teste",
      disciplina: "Biologia",
      titulo: "Mitose, Meiose e Ciclo Celular",
      data: formatDate(12), // 12 dias (Calendário Geral)
      hora: "11:30",
      descricao: "Capítulos 3 e 4 do livro didático."
    }
  ];
}

// ----------------------------------------------------------------------------
// 3. RELÓGIO E DATA EM TEMPO REAL (OTIMIZADO PARA TV)
// ----------------------------------------------------------------------------
function initLiveClock() {
  const clockEl = document.getElementById("live-clock");
  const dateEl = document.getElementById("live-date");

  function update() {
    const now = new Date();

    // Horas com formato tabular (HH:MM:SS)
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    if (clockEl) {
      clockEl.textContent = `${hours}:${minutes}:${seconds}`;
    }

    // Data por extenso em Português
    if (dateEl) {
      const options = { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' };
      const formattedDate = now.toLocaleDateString('pt-PT', options);
      dateEl.textContent = formattedDate;
    }
  }

  update();
  setInterval(update, 1000);
}

// ----------------------------------------------------------------------------
// 4. PARSER E NORMALIZADOR DE DATAS (JS NATIVO)
// ----------------------------------------------------------------------------
/**
 * Converte strings nos formatos "YYYY-MM-DD" ou "DD/MM/YYYY" para objeto Date
 * zera as horas para cálculo de diferença baseado em dias civis puros.
 */
function parseEventDate(dateStr) {
  if (!dateStr) return null;
  const cleanStr = dateStr.trim();

  let year, month, day;

  if (cleanStr.includes("-")) {
    // Formato ISO: YYYY-MM-DD
    const parts = cleanStr.split("-");
    year = parseInt(parts[0], 10);
    month = parseInt(parts[1], 10) - 1; // Mês 0-indexado em JS
    day = parseInt(parts[2], 10);
  } else if (cleanStr.includes("/")) {
    // Formato Europeu: DD/MM/YYYY
    const parts = cleanStr.split("/");
    day = parseInt(parts[0], 10);
    month = parseInt(parts[1], 10) - 1;
    year = parseInt(parts[2], 10);
  } else {
    const d = new Date(cleanStr);
    return isNaN(d.getTime()) ? null : new Date(d.getFullYear(), d.getMonth(), d.getDate());
  }

  const result = new Date(year, month, day);
  return isNaN(result.getTime()) ? null : result;
}

/**
 * Calcula a diferença em dias civis entre o dia de hoje e a data do evento.
 */
function calculateDaysDifference(eventDate) {
  const now = new Date();
  // Normaliza o dia atual para 00:00:00.000 (meia-noite local)
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  
  // Normaliza a data do evento para meia-noite
  const target = new Date(eventDate.getFullYear(), eventDate.getMonth(), eventDate.getDate());

  const diffMs = target.getTime() - today.getTime();
  const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));
  return diffDays;
}

// ----------------------------------------------------------------------------
// 5. PARSER CSV DE BAIXO IMPACTO (SEM DEPENDÊNCIAS EXTERNAS)
// ----------------------------------------------------------------------------
function parseCSV(csvText) {
  const lines = csvText.trim().split(/\r?\n/);
  if (lines.length < 2) return [];

  // Cabeçalhos na primeira linha
  const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
  const events = [];

  for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;

    // Tratamento simples para valores separados por vírgula
    const values = line.split(',').map(v => v.replace(/^"|"$/g, '').trim());
    const obj = {};

    headers.forEach((header, index) => {
      obj[header] = values[index] || "";
    });

    // Mapeamento tolerante a variações comuns de cabeçalhos
    events.push({
      tipo: obj.tipo || obj.type || "Aviso",
      disciplina: obj.disciplina || obj.materia || obj.subject || "Geral",
      titulo: obj.titulo || obj.nome || obj.title || "Sem título",
      data: obj.data || obj.date || "",
      hora: obj.hora || obj.time || "",
      descricao: obj.descricao || obj.description || obj.detalhes || ""
    });
  }

  return events;
}

// ----------------------------------------------------------------------------
// 6. RENDERIZAÇÃO DOM: ALARMES URGENTES VS. CALENDÁRIO GERAL
// ----------------------------------------------------------------------------
function renderDashboard(events) {
  const urgentContainer = document.getElementById("urgent-cards-container");
  const urgentBadgeCount = document.getElementById("urgent-badge-count");
  const generalTbody = document.getElementById("general-events-tbody");
  const generalBadgeCount = document.getElementById("general-badge-count");

  // Arrays de separação
  const urgentEvents = [];
  const generalEvents = [];

  events.forEach(event => {
    const parsedDate = parseEventDate(event.data);
    if (!parsedDate) return;

    const diffDays = calculateDaysDifference(parsedDate);
    const enrichedEvent = { ...event, parsedDate, diffDays };

    // Regra Pedagógica de Proximidade:
    // Eventos futuros com 2 dias ou menos (e que não estejam expirados há mais de 1 dia)
    if (diffDays >= 0 && diffDays <= CONFIG.URGENT_THRESHOLD_DAYS) {
      urgentEvents.push(enrichedEvent);
    } else if (diffDays > CONFIG.URGENT_THRESHOLD_DAYS) {
      generalEvents.push(enrichedEvent);
    }
  });

  // Ordena os eventos por proximidade temporal (mais próximos primeiro)
  urgentEvents.sort((a, b) => a.diffDays - b.diffDays);
  generalEvents.sort((a, b) => a.diffDays - b.diffDays);

  // --------------------------------------------------------------------------
  // A) RENDERIZAÇÃO DA ZONA DE ALERTAS URGENTES (<= 2 DIAS)
  // --------------------------------------------------------------------------
  urgentBadgeCount.textContent = urgentEvents.length;

  if (urgentEvents.length === 0) {
    urgentContainer.innerHTML = `
      <div class="empty-alert-box">
        <div class="empty-alert-icon">🎉</div>
        <div class="empty-alert-text">Sem Testes ou TPCs Críticos!</div>
        <div class="empty-alert-sub">Nenhum evento urgente agendado para os próximos 2 dias. Bom trabalho!</div>
      </div>
    `;
  } else {
    urgentContainer.innerHTML = urgentEvents.map(event => {
      // Texto de destaque agressivo
      let countdownLabel = "";
      if (event.diffDays === 0) {
        countdownLabel = "🚨 HOJE!";
      } else if (event.diffDays === 1) {
        countdownLabel = "⚠️ AMANHÃ!";
      } else {
        countdownLabel = `⏳ EM ${event.diffDays} DIAS`;
      }

      const formattedDateStr = event.parsedDate.toLocaleDateString('pt-PT', {
        day: '2-digit', month: 'long'
      });

      return `
        <article class="card-urgent" role="alert">
          <div class="card-urgent-top">
            <span class="card-urgent-type">${escapeHtml(event.tipo)}</span>
            <span class="card-urgent-countdown">${countdownLabel}</span>
          </div>
          
          <div class="card-urgent-subject">${escapeHtml(event.disciplina)}</div>
          <h3 class="card-urgent-title">${escapeHtml(event.titulo)}</h3>
          
          ${event.descricao ? `<p class="card-urgent-desc">📝 ${escapeHtml(event.descricao)}</p>` : ''}
          
          <div class="card-urgent-date">
            📅 Data: ${formattedDateStr} ${event.hora ? `às ${escapeHtml(event.hora)}` : ''}
          </div>
        </article>
      `;
    }).join("");
  }

  // --------------------------------------------------------------------------
  // B) RENDERIZAÇÃO DO CALENDÁRIO GERAL (> 2 DIAS)
  // --------------------------------------------------------------------------
  generalBadgeCount.textContent = `${generalEvents.length} eventos`;

  if (generalEvents.length === 0) {
    generalTbody.innerHTML = `
      <tr>
        <td colspan="5" style="text-align:center; padding: 30px; color: var(--text-muted);">
          Nenhum evento futuro registado além dos próximos 2 dias.
        </td>
      </tr>
    `;
  } else {
    generalTbody.innerHTML = generalEvents.map(event => {
      const typeClass = `tag-${event.tipo.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "")}`;
      const formattedDate = event.parsedDate.toLocaleDateString('pt-PT', {
        day: '2-digit', month: 'short'
      });

      return `
        <tr>
          <td><span class="tag-event ${typeClass}">${escapeHtml(event.tipo)}</span></td>
          <td style="color: #f8fafc; font-weight: 700;">${escapeHtml(event.disciplina)}</td>
          <td>
            <div style="color: #ffffff; font-size: 24px;">${escapeHtml(event.titulo)}</div>
            ${event.descricao ? `<div style="font-size: 20px; color: var(--text-muted);">${escapeHtml(event.descricao)}</div>` : ''}
          </td>
          <td style="color: #38bdf8;">${formattedDate} ${event.hora ? `<br><small style="color: var(--text-muted); font-size: 18px;">${escapeHtml(event.hora)}</small>` : ''}</td>
          <td><span class="tag-days-remaining">em ${event.diffDays} dias</span></td>
        </tr>
      `;
    }).join("");
  }
}

// ----------------------------------------------------------------------------
// 7. CARREGAMENTO E FETCH DE DADOS
// ----------------------------------------------------------------------------
async function fetchSheetData() {
  const syncDot = document.getElementById("sync-status-dot");
  const syncText = document.getElementById("sync-status-text");
  const lastUpdateEl = document.getElementById("last-update-time");
  const sourceLabel = document.getElementById("source-url-label");

  // Se não foi configurado um URL real da folha, utiliza os dados Mock nativos
  if (!CONFIG.GOOGLE_SHEET_CSV_URL || CONFIG.GOOGLE_SHEET_CSV_URL.trim() === "") {
    console.info("[webOS Dashboard] Modo Demonstração: Usando dados locais de exemplo.");
    renderDashboard(getMockEvents());
    
    if (sourceLabel) sourceLabel.textContent = "Demonstração Local (Insira o URL no app.js)";
    if (syncDot) syncDot.classList.remove("offline");
    if (syncText) syncText.textContent = "Modo Demonstração";
    if (lastUpdateEl) {
      const now = new Date();
      lastUpdateEl.textContent = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    }
    return;
  }

  try {
    if (syncText) syncText.textContent = "A atualizar...";
    // Adiciona timestamp para impedir cache HTTP agressivo no Chromium webOS
    const cacheBusterUrl = `${CONFIG.GOOGLE_SHEET_CSV_URL}${CONFIG.GOOGLE_SHEET_CSV_URL.includes('?') ? '&' : '?'}_t=${Date.now()}`;
    
    const response = await fetch(cacheBusterUrl);
    if (!response.ok) {
      throw new Error(`Erro HTTP: ${response.status} ${response.statusText}`);
    }

    const csvText = await response.text();
    const parsedEvents = parseCSV(csvText);

    renderDashboard(parsedEvents);

    // Atualiza indicadores de sucesso
    if (syncDot) syncDot.classList.remove("offline");
    if (syncText) syncText.textContent = "Sincronizado";
    if (sourceLabel) sourceLabel.textContent = "Google Sheet Ativa";
    if (lastUpdateEl) {
      const now = new Date();
      lastUpdateEl.textContent = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    }
  } catch (error) {
    console.error("[webOS Dashboard] Falha no fetch da Google Sheet:", error);
    if (syncDot) syncDot.classList.add("offline");
    if (syncText) syncText.textContent = "Erro de Ligação (Usando Cache)";
    
    // Se falhar e não houver dados, carrega os mocks para a TV nunca ficar vazia
    renderDashboard(getMockEvents());
  }
}

// ----------------------------------------------------------------------------
// 8. UTILITÁRIOS DE SEGURANÇA
// ----------------------------------------------------------------------------
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ----------------------------------------------------------------------------
// 9. INICIALIZAÇÃO DA APLICAÇÃO
// ----------------------------------------------------------------------------
window.addEventListener("DOMContentLoaded", () => {
  console.log("[LG webOS] Inicializando Dashboard Escolar...");
  
  // 1. Inicia o relógio
  initLiveClock();

  // 2. Primeiro fetch de dados
  fetchSheetData();

  // 3. Configura o polling regular de atualização
  setInterval(fetchSheetData, CONFIG.REFRESH_INTERVAL_MS);
});

