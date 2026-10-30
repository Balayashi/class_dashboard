/**
 * ============================================================================
 * GOOGLE APPS SCRIPT: WEBHOOK DE ATUALIZAÇÃO E NOTIFICAÇÃO
 * ============================================================================
 * Como instalar no Google Sheets:
 * 1. Na sua Google Sheet, clique em: Extensões > Apps Script.
 * 2. Apague o código existente e cole este código completo.
 * 3. Altere o EMAIL_DESTINATARIO para o seu endereço de email.
 * 4. Clique em "Implementar" (Deploy) > "Nova implementação" (New deployment).
 * 5. Tipo: "Aplicação Web" (Web app).
 * 6. Executar como: "Eu" (Me).
 * 7. Quem tem acesso: "Qualquer pessoa" (Anyone) -> ESSENCIAL para a TV conseguir comunicar.
 * 8. Clique em "Implementar", autorize as permissões e copie o URL gerado (ex: https://script.google.com/macros/s/.../exec).
 * 9. Cole esse URL no ficheiro app.js na constante CONFIG.APPS_SCRIPT_WEBHOOK_URL.
 * ============================================================================
 */

// Configure aqui o seu email para receber notificações instantâneas
const EMAIL_DESTINATARIO = "o_seu_email@gmail.com";

function doGet(e) {
  return handleRequest(e);
}

function doPost(e) {
  return handleRequest(e);
}

function handleRequest(e) {
  try {
    let params = {};
    
    // Suporte tanto para envio via parâmetros URL (GET/POST) como JSON no body
    if (e.postData && e.postData.contents) {
      try {
        params = JSON.parse(e.postData.contents);
      } catch (err) {
        params = e.parameter || {};
      }
    } else {
      params = e.parameter || {};
    }

    const titulo = params.titulo || "";
    const disciplina = params.disciplina || "";
    const tipo = params.tipo || "Tarefa";
    const acao = params.acao || "concluir"; // "concluir" ou "desfazer"
    const novoEstado = (acao === "concluir") ? "Concluído ✅" : "Pendente ⏳";

    const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    const data = sheet.getDataRange().getValues();
    if (data.length < 1) {
      throw new Error("Folha vazia");
    }

    // Localiza os cabeçalhos
    const headers = data[0].map(h => String(h).trim().toLowerCase());
    let colTitulo = headers.indexOf("titulo");
    if (colTitulo === -1) colTitulo = headers.indexOf("título");
    
    let colEstado = headers.indexOf("estado");
    // Se a coluna "Estado" ainda não existir, cria-a na primeira coluna livre
    if (colEstado === -1) {
      colEstado = headers.length;
      sheet.getRange(1, colEstado + 1).setValue("Estado");
      sheet.getRange(1, colEstado + 2).setValue("Data Conclusão");
    }

    let linhaAtualizada = -1;

    // Procura a linha correspondente ao título da tarefa
    for (let r = 1; r < data.length; r++) {
      const valorLinha = String(data[r][colTitulo] || "").trim().toLowerCase();
      if (valorLinha === titulo.trim().toLowerCase()) {
        linhaAtualizada = r + 1; // Linhas no Sheets são 1-based
        sheet.getRange(linhaAtualizada, colEstado + 1).setValue(novoEstado);
        
        if (acao === "concluir") {
          const timestamp = Utilities.formatDate(new Date(), "Europe/Lisbon", "dd/MM/yyyy HH:mm:ss");
          sheet.getRange(linhaAtualizada, colEstado + 2).setValue(timestamp);
        } else {
          sheet.getRange(linhaAtualizada, colEstado + 2).setValue("");
        }
        break;
      }
    }

    // Dispara a notificação por email para o encarregado de educação com o tipo real (Teste, TPC, etc.)
    if (acao === "concluir" && EMAIL_DESTINATARIO && EMAIL_DESTINATARIO !== "o_seu_email@gmail.com") {
      const assunto = `🎓 Painel Escolar: ${tipo} Concluído! (${disciplina} - ${titulo})`;
      const corpo = `
Olá!

O seu educando acabou de marcar como CONCLUÍDO um ${tipo.toUpperCase()} através do comando da televisão:

📌 Tipo de Evento: ${tipo}
📚 Disciplina: ${disciplina}
📝 Tarefa / Conteúdo: ${titulo}
⏰ Data/Hora: ${new Date().toLocaleString("pt-PT", { timeZone: "Europe/Lisbon" })}

A Google Sheet foi atualizada automaticamente com a data e hora.
Parabéns pelo trabalho realizado! 🎉
      `;
      MailApp.sendEmail(EMAIL_DESTINATARIO, assunto, corpo);
    }

    return ContentService.createTextOutput(JSON.stringify({
      status: "success",
      mensagem: "Folha atualizada e notificação enviada!",
      linha: linhaAtualizada,
      novoEstado: novoEstado
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (erro) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      mensagem: erro.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

