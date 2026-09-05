// ==UserScript==
// @name         Telegram Database Exporter (Versão Final)
// @namespace    https://tampermonkey.net/
// @version      3.0
// @description  Lê diretamente o banco de dados interno (IndexedDB) do Telegram Web e exporta todos os grupos para TXT
// @match        https://web.telegram.org/*
// @grant        none
// ==/UserScript==

(function () {
  'use strict';

  function criarBotao() {
    if (document.getElementById('btn-dump-db-tg')) return;

    const btn = document.createElement('button');
    btn.id = 'btn-dump-db-tg';
    btn.innerHTML = '⚡ Exportar Banco de Dados';
    btn.style.cssText = `
      position: fixed;
      bottom: 25px;
      left: 25px;
      z-index: 999999;
      background: #0088cc;
      color: white;
      border: 2px solid #fff;
      padding: 12px 18px;
      border-radius: 8px;
      font-weight: bold;
      font-size: 13px;
      cursor: pointer;
      box-shadow: 0 4px 15px rgba(0,0,0,0.4);
    `;

    btn.onclick = extrairViaIndexedDB;
    document.body.appendChild(btn);
  }

  // Lê os registros de uma tabela no IndexedDB
  function lerStore(db, storeName) {
    return new Promise((resolve) => {
      try {
        if (!db.objectStoreNames.contains(storeName)) {
          resolve([]);
          return;
        }
        const transaction = db.transaction(storeName, 'readonly');
        const store = transaction.objectStore(storeName);
        const request = store.getAll();
        request.onsuccess = () => resolve(request.result || []);
        request.onerror = () => resolve([]);
      } catch (e) {
        resolve([]);
      }
    });
  }

  async function extrairViaIndexedDB() {
    const btn = document.getElementById('btn-dump-db-tg');
    btn.innerText = '⏳ Lendo banco de dados...';

    const bancosDisponiveis = await indexedDB.databases();
    let todosChats = [];

    for (const info of bancosDisponiveis) {
      if (!info.name) continue;

      await new Promise((resolve) => {
        const req = indexedDB.open(info.name);
        req.onsuccess = async (e) => {
          const db = e.target.result;

          // Tabelas comuns onde o Telegram armazena chats
          const stores = ['chats', 'dialogs', 'peers', 'channels'];
          for (const s of stores) {
            const itens = await lerStore(db, s);
            if (itens.length > 0) {
              todosChats = todosChats.concat(itens);
            }
          }
          db.close();
          resolve();
        };
        req.onerror = () => resolve();
      });
    }

    if (todosChats.length === 0) {
      alert('Nenhum dado encontrado no cache local. Recarregue a página com F5 e tente novamente.');
      btn.innerText = '⚡ Exportar Banco de Dados';
      return;
    }

    // Filtrar e Organizar (Elimina duplicatas e conversas 1 a 1 com pessoas)
    const gruposPrivados = [];
    const gruposPublicos = [];
    const canais = [];
    const processados = new Set();

    todosChats.forEach((chat) => {
      if (!chat) return;

      const id = chat.id || chat.peerId || '';
      const titulo = chat.title || chat.name || '';
      const username = chat.username || '';
      const tipo = chat._ || chat.type || '';

      // Ignora usuários individuais e mensagens salvas
      if (tipo === 'user' || (!titulo && !username)) return;

      const chaveUnica = id + titulo;
      if (processados.has(chaveUnica)) return;
      processados.add(chaveUnica);

      const dados = {
        id: id,
        titulo: titulo || 'Sem Título',
        username: username ? `@${username}` : null,
        link: username ? `https://t.me/${username}` : 'Privado (Sem link @ público)'
      };

      // Classificação
      if (chat.broadcast || tipo === 'channel') {
        canais.push(dados);
      } else if (!username) {
        gruposPrivados.push(dados);
      } else {
        gruposPublicos.push(dados);
      }
    });

    // Gerar o Conteúdo Formatado em Texto
    let txt = `====================================================\n`;
    txt += `  RELATÓRIO DE CHATS EXTRAÍDOS DO TELEGRAM\n`;
    txt += `  Data: ${new Date().toLocaleString()}\n`;
    txt += `====================================================\n\n`;

    txt += `🔒 1. GRUPOS PRIVADOS ENCONTRADOS (${gruposPrivados.length}):\n\n`;
    gruposPrivados.forEach((g, i) => {
      txt += `  [${i + 1}] ${g.titulo}\n`;
      txt += `      ID: ${g.id}\n`;
      txt += `      Tipo: Privado\n\n`;
    });

    txt += `\n🌐 2. GRUPOS PÚBLICOS ENCONTRADOS (${gruposPublicos.length}):\n\n`;
    gruposPublicos.forEach((g, i) => {
      txt += `  [${i + 1}] ${g.titulo}\n`;
      txt += `      Link: ${g.link}\n`;
      txt += `      Username: ${g.username}\n\n`;
    });

    txt += `\n📢 3. CANAIS (${canais.length}):\n\n`;
    canais.forEach((c, i) => {
      txt += `  [${i + 1}] ${c.titulo}\n`;
      txt += `      Link: ${c.link}\n\n`;
    });

    // Baixar o arquivo .txt automaticamente
    const blob = new Blob([txt], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `telegram_chats_database_${Date.now()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    btn.innerText = `✅ Baixado (${gruposPublicos.length + canais.length} públicos / ${gruposPrivados.length} privados)`;
    setTimeout(() => {
      btn.innerText = '⚡ Exportar Banco de Dados';
    }, 4000);
  }

  // Inicializa o botão na tela
  const timer = setInterval(() => {
    if (document.body) {
      clearInterval(timer);
      setTimeout(criarBotao, 1000);
    }
  }, 500);
})();// ==UserScript==
// @name        New script telegram.org
// @namespace   Violentmonkey Scripts
// @icon        data:image/png;base64,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
// @version     1.0.0
//
// @match       https://web.telegram.org/a/*
// @grant       none
//
// @author      -
// @description
// ==/UserScript==
