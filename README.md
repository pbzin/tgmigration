Aqui está o tutorial revisado, focado 100% na importação automática dos canais e
grupos públicos e na limpeza final:

📋 GUIA DE MIGRAÇÃO PÚBLICA DO TELEGRAM (Linux + Python)

FASE 1: Extrair a Lista de Grupos (Conta Antiga)

1.  Abra o Telegram Web K (https://web.telegram.org/k/) na sua conta antiga.
2.  Abra a pasta "Chats Arquivados" e volte (para carregar todo o histórico na
    memória).
3.  Ative o script extrator no Violentmonkey e clique em ⚡ Exportar Banco de
    Dados.
4.  Mova o arquivo baixado para a sua pasta pessoal (/home/user/) e renomeie-o
    para grupos.txt.

FASE 2: Preparar o Ambiente no Linux Mint

1.  Abra o terminal e configure o ambiente com o Telethon:
    sudo apt update && sudo apt install python3 python3-pip python3-venv -y
    python3 -m venv venv
    source venv/bin/activate
    pip install telethon
2.  Obtenha suas credenciais de API:
      - Acesse my.telegram.org e faça login.
      - Vá em API development tools ➔ Crie um app e copie o API_ID e o API_HASH.

FASE 3: Importação Automática (Conta Nova)

1.  Certifique-se de que o grupos.txt e o importador_telethon.py estão na sua
    pasta pessoal com o seu API_ID e API_HASH configurados.
2.  No terminal, inicie a importação:
    ./venv/bin/python3 importador_telethon.py
3.  Digite o número da sua CONTA NOVA e o código de confirmação recebido no app
    do Telegram.
4.  O script cuidará do restante sozinho:
      - Entra em todos os canais e grupos públicos;
      - Faz pausas automáticas de segurança para evitar limites de spam;
      - Se houver FLOOD_WAIT, aguarda a liberação e retoma automaticamente;
      - Grava o progresso no arquivo progresso_migracao.json.

FASE 4: Deslogar e Limpar o Ambiente (Após Concluir)

1.  Apagar a sessão no Linux:
    rm -f *.session
2.  Encerrar a conexão nos servidores do Telegram:
      - No app do Telegram (celular/PC), vá em Configurações ➔ Dispositivos.
      - Localize a sessão criada (ex: MeuMigrador) e clique em Encerrar Sessão.
3.  Desativar o script no navegador:
      - Clique no ícone do Violentmonkey e desative/remova o script extrator.

💡 Comandos de Controle Rápido:

  - Interromper a execução: Pressione Ctrl + C (o progresso fica salvo).
  - Retomar de onde parou: Execute ./venv/bin/python3 importador_telethon.py
    novamente.
