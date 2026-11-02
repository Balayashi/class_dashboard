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
  // URL da folha de cálculo Google publicada em formato CSV:
  GOOGLE_SHEET_CSV_URL: "https://docs.google.com/spreadsheets/d/e/2PACX-1vTqHKQjJmF7JADwtGIXgQzlG1a1Hw-qT6hf7hnQ96cmRUzDORgksjX0ZsSvWlj9MpCqi0In45JMkL_-/pub?output=csv",

  // URL do Webhook do Google Apps Script (para gravação direta na folha e notificações):
  // Siga o guia no ficheiro 'google_apps_script.js' para obter o seu URL de Webhook.
  APPS_SCRIPT_WEBHOOK_URL: "",

  // Intervalo de sincronização com a Google Sheet (5 minutos = 300.000 ms)
  REFRESH_INTERVAL_MS: 5 * 60 * 1000,

  // Limiar de dias para acionar o alarme de proximidade
  URGENT_THRESHOLD_DAYS: 2
};

// ----------------------------------------------------------------------------
// 2. HORÁRIO OFICIAL DA TURMA 5º G (EB Pedro Jacques de Magalhães)
// ----------------------------------------------------------------------------
const HORARIO_5G = {
  1: [ // Segunda-feira
    { hora: "08:15 - 09:05", disciplina: "HGP", sala: "Sala S08" },
    { hora: "09:15 - 10:05", disciplina: "Inglês", sala: "Sala S08" },
    { hora: "10:20 - 11:10", disciplina: "CD / TIC", sala: "INF01 / INF02" },
    { hora: "11:20 - 12:10", disciplina: "Matemática", sala: "Sala S08" },
    { hora: "13:15 - 15:05", disciplina: "Educação Tecnológica (ET)", sala: "Sala EVT01" },
    { hora: "15:15 - 16:05", disciplina: "Educação Física (EF)", sala: "Pavilhão C1" }
  ],
  2: [ // Terça-feira
    { hora: "08:15 - 10:05", disciplina: "Matemática (2 blocos)", sala: "Sala S08" },
    { hora: "10:20 - 11:10", disciplina: "Português", sala: "Sala S08" },
    { hora: "11:20 - 12:10", disciplina: "Ciências Naturais (CN)", sala: "Sala S08" },
    { hora: "12:15 - 13:05", disciplina: "HGP", sala: "Sala S08" },
    { hora: "15:15 - 16:05", disciplina: "Educação Musical (EM)", sala: "Sala EM01" }
  ],
  3: [ // Quarta-feira
    { hora: "08:15 - 10:05", disciplina: "Educação Visual (EV)", sala: "Sala EVT01" },
    { hora: "10:20 - 11:10", disciplina: "Inglês", sala: "Sala EVT02" },
    { hora: "11:20 - 12:10", disciplina: "Português", sala: "Sala S08" },
    { hora: "12:15 - 13:05", disciplina: "Apoio Estudo (Português)", sala: "Sala S08" },
    { hora: "14:15 - 15:05", disciplina: "DTA (Direção de Turma)", sala: "Sala S08" }
  ],
  4: [ // Quinta-feira
    { hora: "08:15 - 10:05", disciplina: "Educação Física (EF)", sala: "Pavilhão C2" },
    { hora: "10:20 - 11:10", disciplina: "Inglês", sala: "Sala S08" },
    { hora: "11:20 - 12:10", disciplina: "HGP", sala: "Sala S08" },
    { hora: "12:15 - 13:05", disciplina: "Ciências Naturais (CN)", sala: "Sala S08" }
  ],
  5: [ // Sexta-feira
    { hora: "08:15 - 09:05", disciplina: "Matemática", sala: "Sala S08" },
    { hora: "09:15 - 10:05", disciplina: "Ciências Naturais (CN)", sala: "Sala S08" },
    { hora: "10:20 - 12:10", disciplina: "Português (2 blocos)", sala: "Sala S08" },
    { hora: "12:15 - 13:05", disciplina: "Apoio Estudo (Matemática)", sala: "Sala S08" }
  ]
};

// ----------------------------------------------------------------------------
// 3. DADOS PREDEFINIDOS / FALLBACK (COM AS SUAS DISCIPLINAS REAIS)
// ----------------------------------------------------------------------------
function getMockEvents() {
  return [
    {
      tipo: "Teste",
      disciplina: "Matemática",
      titulo: "Exponentes",
      data: "2026-11-01",
      hora: "10:00",
      descricao: "Sem comentarios"
    },
    {
      tipo: "TPC",
      disciplina: "Portugues",
      titulo: "Resumo Cap 5",
      data: "2026-11-09",
      hora: "21:00",
      descricao: "Por fazer"
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

  // Deteção inteligente do delimitador (vírgula ou ponto e vírgula)
  const firstLine = lines[0];
  const delimiter = firstLine.includes(";") && !firstLine.includes(",") ? ";" : ",";

  // Função auxiliar para remover acentos e normalizar cabeçalhos
  const normalizeKey = (key) => {
    return key.trim().toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  };

  const headers = lines[0].split(delimiter).map(normalizeKey);
  const events = [];

  for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;

    // Remove aspas envolventes se existirem
    const values = line.split(delimiter).map(v => v.replace(/^"|"$/g, '').trim());
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
// 6. GESTÃO DE ESTADO LOCAL, TIPOS DE TAREFA E NOTIFICAÇÕES INTELIGENTES
// ----------------------------------------------------------------------------
function getTaskTypeConfig(tipo) {
  const t = (tipo || "Tarefa").trim();
  const lower = t.toLowerCase();

  if (lower.includes("teste")) {
    return {
      type: "Teste",
      doneBadge: "TESTE PREPARADO ✅",
      btnAction: "✅ Marcar Teste Preparado (Pressione OK)",
      btnUndo: "↩️ Reabrir Teste",
      btnTableAction: "✅ Teste Feito",
      toastDone: (disc, tit) => `🎉 Fantástico! Preparação para o Teste de ${disc} (${tit}) concluída com sucesso!`,
      toastUndo: (disc, tit) => `↩️ Teste de ${disc} reaberto para estudo.`
    };
  }
  if (lower.includes("tpc")) {
    return {
      type: "TPC",
      doneBadge: "TPC CONCLUÍDO ✅",
      btnAction: "✅ Marcar TPC Concluído (Pressione OK)",
      btnUndo: "↩️ Reabrir TPC",
      btnTableAction: "✅ TPC Feito",
      toastDone: (disc, tit) => `🎉 Parabéns! TPC de ${disc} (${tit}) concluído com sucesso!`,
      toastUndo: (disc, tit) => `↩️ TPC de ${disc} reaberto.`
    };
  }
  if (lower.includes("trabalho")) {
    return {
      type: "Trabalho",
      doneBadge: "TRABALHO ENTREGUE ✅",
      btnAction: "✅ Marcar Trabalho Entregue (Pressione OK)",
      btnUndo: "↩️ Reabrir Trabalho",
      btnTableAction: "✅ Entregue",
      toastDone: (disc, tit) => `🎉 Excelente! Trabalho de ${disc} (${tit}) marcado como concluído!`,
      toastUndo: (disc, tit) => `↩️ Trabalho de ${disc} reaberto.`
    };
  }
  return {
    type: t,
    doneBadge: "CONCLUÍDO ✅",
    btnAction: `✅ Marcar ${t} Concluído (Pressione OK)`,
    btnUndo: `↩️ Reabrir ${t}`,
    btnTableAction: "✅ Concluir",
    toastDone: (disc, tit) => `🎉 ${t} de ${disc} (${tit}) concluído com sucesso!`,
    toastUndo: (disc, tit) => `↩️ ${t} de ${disc} reaberto.`
  };
}

function isTaskDone(taskId) {
  try {
    const doneList = JSON.parse(localStorage.getItem("escola_tasks_done") || "[]");
    return doneList.includes(taskId);
  } catch (e) {
    return false;
  }
}

function showToast(mensagem) {
  const toast = document.getElementById("tv-toast");
  const msgEl = document.getElementById("toast-message");
  if (msgEl) msgEl.textContent = mensagem;
  if (toast) {
    toast.classList.add("visible");
    setTimeout(() => toast.classList.remove("visible"), 5000);
  }
}

/**
 * Alterna a conclusão da tarefa com distinção clara entre Testes, TPCs e Trabalhos.
 */
async function toggleTaskCompletion(taskId, disciplina, titulo, tipo) {
  let doneList = [];
  try {
    doneList = JSON.parse(localStorage.getItem("escola_tasks_done") || "[]");
  } catch (e) {}

  const config = getTaskTypeConfig(tipo);
  const wasDone = doneList.includes(taskId);
  const nowDone = !wasDone;

  if (nowDone) {
    doneList.push(taskId);
    showToast(config.toastDone(disciplina, titulo));
  } else {
    doneList = doneList.filter(id => id !== taskId);
    showToast(config.toastUndo(disciplina, titulo));
  }

  try {
    localStorage.setItem("escola_tasks_done", JSON.stringify(doneList));
  } catch (e) {}

  // Recarrega o painel visual
  fetchSheetData();

  // Envio para o Webhook do Google Apps Script com o tipo correto
  if (CONFIG.APPS_SCRIPT_WEBHOOK_URL && CONFIG.APPS_SCRIPT_WEBHOOK_URL.trim() !== "") {
    try {
      const url = `${CONFIG.APPS_SCRIPT_WEBHOOK_URL}?acao=${nowDone ? 'concluir' : 'desfazer'}&tipo=${encodeURIComponent(config.type)}&disciplina=${encodeURIComponent(disciplina)}&titulo=${encodeURIComponent(titulo)}`;
      await fetch(url, { mode: 'no-cors' });
      console.log(`[webOS Dashboard] Webhook acionado: ${config.type} atualizado e email enviado.`);
    } catch (err) {
      console.warn("[webOS Dashboard] Falha de comunicação com o Webhook:", err);
    }
  }
}

// ----------------------------------------------------------------------------
// 7. MATRIZ DO HORÁRIO SEMANAL COMPLETO (IDENTICA AO DOCUMENTO ESCOLAR)
// ----------------------------------------------------------------------------
const MATRIZ_SEMANAL_5G = [
  {
    tempo: "08:15 - 09:05",
    aulas: {
      1: { disc: "HGP", sala: "S08", classe: "subj-hgp" },
      2: { disc: "Matemática", sala: "S08", classe: "subj-mat" },
      3: { disc: "Educação Visual (EV)", sala: "EVT01", classe: "subj-ev" },
      4: { disc: "Educação Física (EF)", sala: "C2", classe: "subj-ef" },
      5: { disc: "Matemática", sala: "S08", classe: "subj-mat" }
    }
  },
  {
    tempo: "09:15 - 10:05",
    aulas: {
      1: { disc: "Inglês", sala: "S08", classe: "subj-ing" },
      2: { disc: "Matemática", sala: "S08", classe: "subj-mat" },
      3: { disc: "Educação Visual (EV)", sala: "EVT01", classe: "subj-ev" },
      4: { disc: "Educação Física (EF)", sala: "C2", classe: "subj-ef" },
      5: { disc: "Ciências Naturais (CN)", sala: "S08", classe: "subj-cn" }
    }
  },
  {
    tempo: "10:20 - 11:10",
    aulas: {
      1: { disc: "CD / TIC", sala: "INF01/02", classe: "subj-tic" },
      2: { disc: "Português", sala: "S08", classe: "subj-port" },
      3: { disc: "Inglês", sala: "EVT02", classe: "subj-ing" },
      4: { disc: "Inglês", sala: "S08", classe: "subj-ing" },
      5: { disc: "Português", sala: "S08", classe: "subj-port" }
    }
  },
  {
    tempo: "11:20 - 12:10",
    aulas: {
      1: { disc: "Matemática", sala: "S08", classe: "subj-mat" },
      2: { disc: "Ciências Naturais (CN)", sala: "S08", classe: "subj-cn" },
      3: { disc: "Português", sala: "S08", classe: "subj-port" },
      4: { disc: "HGP", sala: "S08", classe: "subj-hgp" },
      5: { disc: "Português", sala: "S08", classe: "subj-port" }
    }
  },
  {
    tempo: "12:15 - 13:05",
    aulas: {
      1: null,
      2: { disc: "HGP", sala: "S08", classe: "subj-hgp" },
      3: { disc: "Apoio Estudo Port.", sala: "S08", classe: "subj-dta" },
      4: { disc: "Ciências Naturais (CN)", sala: "S08", classe: "subj-cn" },
      5: { disc: "Apoio Estudo Mat.", sala: "S08", classe: "subj-dta" }
    }
  },
  {
    tempo: "13:15 - 14:05",
    aulas: {
      1: { disc: "Ed. Tecnológica (ET)", sala: "EVT01", classe: "subj-et" },
      2: null,
      3: null,
      4: null,
      5: null
    }
  },
  {
    tempo: "14:15 - 15:05",
    aulas: {
      1: { disc: "Ed. Tecnológica (ET)", sala: "EVT01", classe: "subj-et" },
      2: null,
      3: { disc: "DTA (Dir. Turma)", sala: "S08", classe: "subj-dta" },
      4: null,
      5: null
    }
  },
  {
    tempo: "15:15 - 16:05",
    aulas: {
      1: { disc: "Educação Física (EF)", sala: "C1", classe: "subj-ef" },
      2: { disc: "Educação Musical (EM)", sala: "EM01", classe: "subj-em" },
      3: null,
      4: null,
      5: null
    }
  }
];

function renderWeeklyTable() {
  const tbody = document.getElementById("weekly-table-tbody");
  if (!tbody) return;

  const today = new Date().getDay(); // 1 = Seg, 2 = Ter, etc.
  
  // Destacar o cabeçalho do dia de hoje
  document.querySelectorAll(".col-day-th").forEach(th => {
    const day = parseInt(th.getAttribute("data-day"), 10);
    if (day === today) {
      th.classList.add("col-today");
    } else {
      th.classList.remove("col-today");
    }
  });

  tbody.innerHTML = MATRIZ_SEMANAL_5G.map(row => {
    let cellsHtml = "";
    for (let d = 1; d <= 5; d++) {
      const isToday = (d === today);
      const aula = row.aulas[d];
      if (aula) {
        cellsHtml += `
          <td class="${isToday ? 'col-today' : ''}">
            <div class="weekly-cell-box ${aula.classe}" tabindex="0">
              <span class="weekly-subject">${escapeHtml(aula.disc)}</span>
              <span class="weekly-room">${escapeHtml(aula.sala)}</span>
            </div>
          </td>
        `;
      } else {
        cellsHtml += `
          <td class="${isToday ? 'col-today' : ''}">
            <span class="weekly-empty-slot">──</span>
          </td>
        `;
      }
    }

    return `
      <tr>
        <td class="slot-time">${escapeHtml(row.tempo)}</td>
        ${cellsHtml}
      </tr>
    `;
  }).join("");
}

// ----------------------------------------------------------------------------
// 8. RENDERIZAÇÃO DO HORÁRIO DO DIA & NAVEGAÇÃO DE VISTAS
// ----------------------------------------------------------------------------
function renderSchedule(dayIndex) {
  const container = document.getElementById("daily-schedule-container");
  if (!container) return;
  const dayBadge = document.getElementById("schedule-day-label");
  const tabs = document.querySelectorAll(".day-selector-tabs .tab-btn");

  const dayNames = {
    1: "Segunda-feira",
    2: "Terça-feira",
    3: "Quarta-feira",
    4: "Quinta-feira",
    5: "Sexta-feira"
  };

  const classes = HORARIO_5G[dayIndex] || [];

  // Atualiza as abas ativas
  tabs.forEach(btn => {
    if (parseInt(btn.getAttribute("data-day"), 10) === dayIndex) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  const todayDay = new Date().getDay();
  const isActuallyToday = todayDay === dayIndex;
  
  if (dayBadge) {
    dayBadge.textContent = isActuallyToday ? `Hoje (${dayNames[dayIndex]})` : dayNames[dayIndex];
  }

  if (!classes || classes.length === 0) {
    container.innerHTML = `<div class="table-loading">Sem aulas presenciais agendadas para este dia.</div>`;
    return;
  }

  container.innerHTML = classes.map(c => `
    <div class="schedule-pill" tabindex="0">
      <span class="time">${escapeHtml(c.hora)}</span>
      <span class="subject">${escapeHtml(c.disciplina)}</span>
      <span class="room">${escapeHtml(c.sala)}</span>
    </div>
  `).join("");
}

function switchView(viewName) {
  const dashboardView = document.getElementById("view-dashboard");
  const scheduleView = document.getElementById("view-schedule");
  const btnDashboard = document.getElementById("btn-nav-dashboard");
  const btnSchedule = document.getElementById("btn-nav-schedule");

  if (viewName === "schedule") {
    if (dashboardView) dashboardView.style.display = "none";
    if (scheduleView) scheduleView.style.display = "flex";
    if (btnDashboard) btnDashboard.classList.remove("active");
    if (btnSchedule) btnSchedule.classList.add("active");
    renderWeeklyTable();
  } else {
    if (dashboardView) dashboardView.style.display = "grid";
    if (scheduleView) scheduleView.style.display = "none";
    if (btnDashboard) btnDashboard.classList.add("active");
    if (btnSchedule) btnSchedule.classList.remove("active");
  }
}

function initScheduleTabs() {
  const tabs = document.querySelectorAll(".day-selector-tabs .tab-btn");
  tabs.forEach(btn => {
    btn.addEventListener("click", () => {
      const day = parseInt(btn.getAttribute("data-day"), 10);
      renderSchedule(day);
    });
  });

  // Botões de alternância de vista
  const btnNavDash = document.getElementById("btn-nav-dashboard");
  const btnNavSched = document.getElementById("btn-nav-schedule");
  const btnOpenWeekly = document.getElementById("btn-open-weekly");
  const btnBackDash = document.getElementById("btn-back-dashboard");

  if (btnNavDash) btnNavDash.addEventListener("click", () => switchView("dashboard"));
  if (btnNavSched) btnNavSched.addEventListener("click", () => switchView("schedule"));
  if (btnOpenWeekly) btnOpenWeekly.addEventListener("click", () => switchView("schedule"));
  if (btnBackDash) btnBackDash.addEventListener("click", () => switchView("dashboard"));

  // Se for fim de semana (Sábado ou Domingo), projeta automaticamente Segunda-feira!
  const today = new Date().getDay();
  const initialDay = (today >= 1 && today <= 5) ? today : 1;
  renderSchedule(initialDay);
}

// ----------------------------------------------------------------------------
// 8. RENDERIZAÇÃO DOM: ALARMES URGENTES VS. CALENDÁRIO GERAL
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

  // Guarda os eventos urgentes para que o arranque possa aceder após o fetch
  renderDashboard._lastUrgentEvents = urgentEvents;

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
      const taskId = `${event.disciplina}_${event.titulo}`.replace(/[^a-zA-Z0-9]/g, '_').toLowerCase();
      const isDone = isTaskDone(taskId);
      const typeCfg = getTaskTypeConfig(event.tipo);

      let countdownLabel = "";
      if (isDone) {
        countdownLabel = `✅ ${typeCfg.doneBadge}`;
      } else if (event.diffDays === 0) {
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
        <article class="card-urgent ${isDone ? 'task-done' : ''}" id="card-${taskId}" role="alert">
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

          <!-- BOTÃO INTERATIVO ADAPTADO AO TIPO (TESTE VS TPC VS TRABALHO) -->
          <button class="btn-task-action" tabindex="0" onclick="toggleTaskCompletion('${taskId}', '${escapeHtml(event.disciplina)}', '${escapeHtml(event.titulo)}', '${escapeHtml(event.tipo)}')">
            ${isDone ? typeCfg.btnUndo : typeCfg.btnAction}
          </button>
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
      const taskId = `${event.disciplina}_${event.titulo}`.replace(/[^a-zA-Z0-9]/g, '_').toLowerCase();
      const isDone = isTaskDone(taskId);
      const typeCfg = getTaskTypeConfig(event.tipo);
      const typeClass = `tag-${event.tipo.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "")}`;
      const formattedDate = event.parsedDate.toLocaleDateString('pt-PT', {
        day: '2-digit', month: 'short'
      });

      return `
        <tr class="${isDone ? 'row-done' : ''}">
          <td><span class="tag-event ${typeClass}">${escapeHtml(event.tipo)}</span></td>
          <td style="color: #f8fafc; font-weight: 700;">${escapeHtml(event.disciplina)}</td>
          <td>
            <div style="color: #ffffff; font-size: 24px; ${isDone ? 'text-decoration: line-through; opacity: 0.7;' : ''}">${escapeHtml(event.titulo)}</div>
            ${event.descricao ? `<div style="font-size: 20px; color: var(--text-muted);">${escapeHtml(event.descricao)}</div>` : ''}
          </td>
          <td style="color: #38bdf8;">${formattedDate} ${event.hora ? `<br><small style="color: var(--text-muted); font-size: 18px;">${escapeHtml(event.hora)}</small>` : ''}</td>
          <td>
            <span class="tag-days-remaining ${isDone ? 'tag-done' : ''}">${isDone ? 'Feito ✅' : `em ${event.diffDays} dias`}</span>
            <br>
            <button class="btn-task-action" style="font-size: 16px; padding: 4px 10px; margin-top: 6px;" tabindex="0" onclick="toggleTaskCompletion('${taskId}', '${escapeHtml(event.disciplina)}', '${escapeHtml(event.titulo)}', '${escapeHtml(event.tipo)}')">
              ${isDone ? typeCfg.btnUndo : typeCfg.btnTableAction}
            </button>
          </td>
        </tr>
      `;
    }).join("");
  }
}

// ----------------------------------------------------------------------------
// 7. CARREGAMENTO E FETCH DE DADOS
// ----------------------------------------------------------------------------

/**
 * Função de fetch otimizada:
 * - Em webOS e Servidor Local (http://localhost:3000): o fetch direto à Google Sheet funciona em ~200ms.
 * - Em ficheiros locais (file:///): navegadores bloqueiam requisições externas por CORS.
 */
async function fetchSheetData() {
  const syncDot = document.getElementById("sync-status-dot");
  const syncText = document.getElementById("sync-status-text");
  const lastUpdateEl = document.getElementById("last-update-time");
  const sourceLabel = document.getElementById("source-url-label");

  // Se o protocolo for file://, informa o utilizador sobre o bloqueio de segurança dos navegadores
  const isFileProtocol = window.location.protocol === "file:";

  if (!CONFIG.GOOGLE_SHEET_CSV_URL || CONFIG.GOOGLE_SHEET_CSV_URL.trim() === "") {
    renderDashboard(getMockEvents());
    if (sourceLabel) sourceLabel.textContent = "Demonstração Local";
    if (syncText) syncText.textContent = "Modo Demonstração";
    return;
  }

  try {
    if (syncText) syncText.textContent = "A sincronizar...";

    // Adiciona timestamp para evitar cache agressivo no motor Chromium da TV
    const cacheBusterUrl = `${CONFIG.GOOGLE_SHEET_CSV_URL}${CONFIG.GOOGLE_SHEET_CSV_URL.includes('?') ? '&' : '?'}_t=${Date.now()}`;
    
    // Fetch direto com timeout de 6 segundos
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 6000);

    const response = await fetch(cacheBusterUrl, {
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status} ${response.statusText}`);
    }

    const csvText = await response.text();
    
    // Valida se o retorno é CSV válido e não uma página HTML de login
    if (!csvText || csvText.trim().startsWith("<!DOCTYPE") || csvText.trim().startsWith("<html")) {
      throw new Error("Resposta da Google não é CSV válido.");
    }

    const parsedEvents = parseCSV(csvText);

    // Guarda a última versão válida em cache do navegador/TV
    try {
      localStorage.setItem("class_dashboard_last_csv", csvText);
    } catch (e) {}

    renderDashboard(parsedEvents);

    if (syncDot) {
      syncDot.classList.remove("offline");
      syncDot.classList.add("live");
    }
    if (syncText) syncText.textContent = "Sincronizado";
    if (sourceLabel) sourceLabel.textContent = "Google Sheet Ativa (Direta)";
    if (lastUpdateEl) {
      const now = new Date();
      const hh = String(now.getHours()).padStart(2, '0');
      const mm = String(now.getMinutes()).padStart(2, '0');
      const ss = String(now.getSeconds()).padStart(2, '0');
      lastUpdateEl.textContent = `${hh}:${mm}:${ss}`;
    }
  } catch (error) {
    console.warn("[webOS Dashboard] Tentativa de fetch direto falhou:", error.message);

    if (syncDot) {
      syncDot.classList.add("offline");
      syncDot.classList.remove("live");
    }

    // Se estiver a correr via file:// no navegador
    if (isFileProtocol) {
      if (syncText) syncText.textContent = "Modo Local (Abra com iniciar_dashboard.bat)";
      if (sourceLabel) sourceLabel.textContent = "Bloqueio CORS do Chrome (file://)";
    } else {
      if (syncText) syncText.textContent = "Sem Ligação (A usar Cache)";
      if (sourceLabel) sourceLabel.textContent = "Google Sheet (Offline)";
    }

    // Tenta usar a cache local guardada; se não existir, usa as suas disciplinas predefinidas
    let cachedCSV = null;
    try {
      cachedCSV = localStorage.getItem("class_dashboard_last_csv");
    } catch (e) {}

    if (cachedCSV) {
      renderDashboard(parseCSV(cachedCSV));
    } else {
      renderDashboard(getMockEvents());
    }
  }
}

// ----------------------------------------------------------------------------
// 8. ALERTA DE ARRANQUE: Modal visível ao ligar a TV com eventos urgentes
// ----------------------------------------------------------------------------

/**
 * Função central do alerta de arranque.
 * Deve ser chamada APÓS o primeiro renderDashboard() completar.
 * 
 * Estratégia:
 * 1. Tenta usar a API nativa webOS (webOS.service Luna) para um toast do sistema.
 * 2. Em fallback (TV sem webOS ou versão antiga), exibe o modal DOM customizado.
 * 
 * @param {Array} urgentEvents - Array de eventos já enriquecidos com {diffDays, ...}
 */
function showStartupAlertIfNeeded(urgentEvents) {
  // Só mostra o alerta se houver eventos urgentes NÃO concluídos
  const pendingUrgent = urgentEvents.filter(ev => {
    const taskId = `${ev.disciplina}_${ev.titulo}`.replace(/[^a-zA-Z0-9]/g, '_').toLowerCase();
    return !isTaskDone(taskId);
  });

  if (pendingUrgent.length === 0) return; // Sem alertas necessários

  // --- TENTATIVA 1: webOS Luna Service (notificação nativa do sistema) ---
  try {
    if (window.webOS && webOS.service && webOS.service.request) {
      const eventLines = pendingUrgent.map(ev => {
        const dayLabel = ev.diffDays === 0 ? "HOJE" : ev.diffDays === 1 ? "AMANHÃ" : `Em ${ev.diffDays} dias`;
        return `${ev.tipo} de ${ev.disciplina}: ${ev.titulo} (${dayLabel})`;
      }).join("\n");

      webOS.service.request("luna://com.webos.notification", {
        method: "createAlert",
        parameters: {
          message: `⚠️ Tens ${pendingUrgent.length} evento(s) urgente(s)!\n${eventLines}`,
          buttons: [{ label: "Ver Alertas", onclick: "window._closeStartupModal && window._closeStartupModal()" }],
          onSuccess: () => console.log("[webOS Dashboard] Notificação nativa criada com sucesso."),
          onFailure: () => showStartupDOMModal(pendingUrgent)  // Fallback DOM
        }
      });
      // Mesmo com Luna, mostramos o modal DOM para ficar visível no app
      showStartupDOMModal(pendingUrgent);
      return;
    }
  } catch (e) {
    console.warn("[webOS Dashboard] Luna Service não disponível, usando modal DOM:", e.message);
  }

  // --- FALLBACK: Modal DOM personalizado ---
  showStartupDOMModal(pendingUrgent);
}

/**
 * Constrói e exibe o overlay modal de alerta de arranque no DOM.
 * Com auto-fecho após 10 segundos + barra de progresso visual.
 * Qualquer tecla/botão do comando fecha o modal antecipadamente.
 */
function showStartupDOMModal(urgentEvents) {
  const overlay = document.getElementById("startup-overlay");
  const listEl  = document.getElementById("startup-alert-list");
  const countdownEl = document.getElementById("startup-countdown");
  const progressFill = document.getElementById("startup-progress-fill");

  if (!overlay || !listEl) return;

  // --- Preenche a lista de eventos urgentes ---
  listEl.innerHTML = urgentEvents.map(ev => {
    let deadlineClass = "startup-deadline-2days";
    let deadlineLabel = `⏳ Em ${ev.diffDays} dias`;

    if (ev.diffDays === 0) {
      deadlineClass = "startup-deadline-today";
      deadlineLabel = "🚨 HOJE!";
    } else if (ev.diffDays === 1) {
      deadlineClass = "startup-deadline-amanha";
      deadlineLabel = "⚠️ AMANHÃ!";
    }

    return `
      <div class="startup-event-item">
        <span class="startup-event-type">${escapeHtml(ev.tipo)}</span>
        <div class="startup-event-info">
          <span class="startup-event-subject">${escapeHtml(ev.disciplina)}</span>
          <span class="startup-event-title">${escapeHtml(ev.titulo)}</span>
        </div>
        <span class="startup-event-deadline ${deadlineClass}">${deadlineLabel}</span>
      </div>
    `;
  }).join("");

  // --- Mostra o overlay ---
  overlay.style.display = "flex";

  // --- Lógica de auto-fecho com contagem regressiva (10 segundos) ---
  const TOTAL_SECONDS = 10;
  let secondsLeft = TOTAL_SECONDS;
  let isClosed = false;

  // Função interna para fechar o modal (com animação de saída)
  function closeModal() {
    if (isClosed) return;
    isClosed = true;

    clearInterval(countdownInterval);
    clearInterval(progressInterval);

    overlay.classList.add("closing");
    // Aguarda a animação de fade-out (400ms) antes de ocultar
    setTimeout(() => {
      overlay.style.display = "none";
      overlay.classList.remove("closing");
    }, 420);
  }

  // Expõe a função de fecho globalmente para o botão Luna Service
  window._closeStartupModal = closeModal;

  // Atualização do contador visual (1x por segundo)
  const countdownInterval = setInterval(() => {
    secondsLeft--;
    if (countdownEl) countdownEl.textContent = secondsLeft;
    if (secondsLeft <= 0) closeModal();
  }, 1000);

  // Barra de progresso (atualiza a cada 100ms para animação suave)
  let progressTick = 0;
  const totalTicks = TOTAL_SECONDS * 10; // 100 ticks
  const progressInterval = setInterval(() => {
    progressTick++;
    const percent = Math.max(0, 100 - (progressTick / totalTicks) * 100);
    if (progressFill) progressFill.style.width = percent + "%";
    if (progressTick >= totalTicks) clearInterval(progressInterval);
  }, 100);

  // Fecha ao pressionar qualquer tecla do comando/teclado
  function onAnyKey(e) {
    // Ignora apenas as teclas de volume que não são navegação
    if (["VolumeUp", "VolumeDown"].includes(e.key)) return;
    closeModal();
    document.removeEventListener("keydown", onAnyKey);
  }
  document.addEventListener("keydown", onAnyKey);

  // Fecha ao clicar no overlay (para testes no PC com rato)
  overlay.addEventListener("click", function onOverlayClick(e) {
    if (e.target === overlay) {
      closeModal();
      overlay.removeEventListener("click", onOverlayClick);
    }
  });
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
// 9. NAVEGAÇÃO E INICIALIZAÇÃO DA APLICAÇÃO
// ----------------------------------------------------------------------------

// Suporte para rolar a página e alternar abas via comando LG (D-Pad) e teclado
window.addEventListener("keydown", (e) => {
  const scrollDistance = 150;
  if (e.key === "ArrowDown" || e.key === "PageDown") {
    window.scrollBy({ top: scrollDistance, behavior: "smooth" });
  } else if (e.key === "ArrowUp" || e.key === "PageUp") {
    window.scrollBy({ top: -scrollDistance, behavior: "smooth" });
  } else if (e.key === "h" || e.key === "H") {
    // Tecla 'H': Alterna instantaneamente para o Horário Semanal
    const schedView = document.getElementById("view-schedule");
    const isShowing = schedView && schedView.style.display !== "none";
    switchView(isShowing ? "dashboard" : "schedule");
  } else if (e.key === "Escape" || e.key === "Back" || e.key === "GoBack") {
    // Tecla 'Esc' ou 'Back' do comando da TV: Volta ao Painel Principal
    switchView("dashboard");
  }
});

window.addEventListener("DOMContentLoaded", async () => {
  console.log("[LG webOS] Inicializando Dashboard Escolar v1.1.0...");

  // 1. Inicia o relógio em tempo real
  initLiveClock();

  // 2. Inicia o horário escolar da Turma 5º G com abas interativas
  initScheduleTabs();

  // 3. Primeiro fetch de dados dos testes e TPCs
  //    Aguarda a conclusão para depois verificar alertas de arranque
  await fetchSheetData();

  // 4. Mostra o alerta de arranque se existirem eventos urgentes pendentes
  //    (com um pequeno atraso para a TV renderizar o UI primeiro)
  const urgentOnStart = renderDashboard._lastUrgentEvents || [];
  if (urgentOnStart.length > 0) {
    setTimeout(() => showStartupAlertIfNeeded(urgentOnStart), 800);
  }

  // 5. Configura o polling regular de atualização (não mostra alerta nas atualizações subsequentes)
  setInterval(fetchSheetData, CONFIG.REFRESH_INTERVAL_MS);
});

