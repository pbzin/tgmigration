import json
import os
import re

ARQUIVO_GRUPOS = "grupos.txt"
ARQUIVO_PROGRESSO = "progresso_migracao.json"
ARQUIVO_SAIDA = "todos_pendentes_e_privados.txt"

def ler_arquivo_completo(caminho):
    if not os.path.exists(caminho):
        print(f"❌ Arquivo '{caminho}' não encontrado!")
        return []

    with open(caminho, "r", encoding="utf-8") as f:
        linhas = [l.strip() for l in f if l.strip()]

    itens = []
    item_atual = {}

    for linha in linhas:
        # Detecta início de um chat por número [X] ou X.
        match_titulo = re.match(r"^(?:\[\d+\]|\d+\.)\s*(.+)$", linha)
        if match_titulo:
            if item_atual and ("titulo" in item_atual or "id" in item_atual):
                itens.append(item_atual)
            item_atual = {"titulo": match_titulo.group(1)}
            continue

        # Captura ID
        match_id = re.search(r"ID:\s*([-\d]+)", linha)
        if match_id:
            item_atual["id"] = match_id.group(1)
            continue

        # Captura Link
        match_link = re.search(r"(?:Link|Identificador):\s*(https?://\S+|@\S+|Privado\S*)", linha)
        if match_link:
            item_atual["link"] = match_link.group(1)
            continue

        # Captura Username
        match_user = re.search(r"Username:\s*(@\S+)", linha)
        if match_user:
            item_atual["username"] = match_user.group(1)
            continue

    if item_atual:
        itens.append(item_atual)

    return itens

def main():
    todos_itens = ler_arquivo_completo(ARQUIVO_GRUPOS)
    
    progresso = {"sucessos": [], "falhas": []}
    if os.path.exists(ARQUIVO_PROGRESSO):
        with open(ARQUIVO_PROGRESSO, "r", encoding="utf-8") as f:
            progresso = json.load(f)

    sucessos_set = set([s.lower() for s in progresso.get("sucessos", [])])
    
    privados_sem_link = []
    publicos_com_link = []

    for item in todos_itens:
        titulo = item.get("titulo", "Sem Nome")
        chat_id = item.get("id", "Sem ID")
        link = item.get("link", "")
        username = item.get("username", "")

        # Identifica se é público (tem username ou t.me/...)
        tem_publico = False
        identificador = ""
        
        if username and username != "null":
            tem_publico = True
            identificador = username.replace("@", "").lower()
        elif "t.me/" in link and "t.me/+" not in link and "joinchat" not in link and "addlist" not in link:
            match = re.search(r"t\.me/([a-zA-Z0-9_]+)", link)
            if match:
                tem_publico = True
                identificador = match.group(1).lower()

        if tem_publico:
            if identificador in sucessos_set:
                item["status"] = "Sucesso"
            else:
                item["status"] = "Pendente/Falha"
            publicos_com_link.append(item)
        else:
            # É PRIVADO (não tem link @ público)
            privados_sem_link.append(item)

    # GERAÇÃO DO RELATÓRIO
    relatorio = []
    relatorio.append("=" * 65)
    relatorio.append("       RELATÓRIO COMPLETO DE GRUPOS PRIVADOS E PENDENTES")
    relatorio.append("=" * 65)
    relatorio.append(f"📊 Total de Itens no Arquivo : {len(todos_itens)}")
    relatorio.append(f"🔒 Grupos Privados (Sem Link): {len(privados_sem_link)}")
    relatorio.append(f"🌐 Grupos/Canais Públicos    : {len(publicos_com_link)}")
    relatorio.append(f"✅ Entradas com Sucesso      : {len(progresso.get('sucessos', []))}")
    relatorio.append(f"❌ Falhas Registradas        : {len(progresso.get('falhas', []))}")
    relatorio.append("=" * 65 + "\n")

    # 1. GRUPOS PRIVADOS
    relatorio.append(f"🔒 1. TODOS OS GRUPOS PRIVADOS ({len(privados_sem_link)} grupos):")
    relatorio.append("   (Estes grupos exigem adicionar a conta nova pela conta antiga)\n")
    for idx, p in enumerate(privados_sem_link, 1):
        relatorio.append(f"   [{idx:03d}] {p.get('titulo')} | ID: {p.get('id', 'N/D')}")

    relatorio.append("\n" + "-" * 65 + "\n")

    # 2. FALHAS / PENDENTES PÚBLICOS
    falhas_lista = [pub for pub in publicos_com_link if pub.get("status") != "Sucesso"]
    relatorio.append(f"❌ 2. PÚBLICOS QUE NÃO FORAM CONCLUÍDOS ({len(falhas_lista)} canais/grupos):")
    relatorio.append("   (Links que expiraram, canais banidos ou restritos)\n")
    for idx, f_item in enumerate(falhas_lista, 1):
        info_link = f_item.get("username") or f_item.get("link") or "Sem link"
        relatorio.append(f"   [{idx:03d}] {f_item.get('titulo')} | {info_link}")

    texto_final = "\n".join(relatorio)

    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f_out:
        f_out.write(texto_final)

    print(texto_final)
    print(f"\n📁 Arquivo salvo com sucesso em: {ARQUIVO_SAIDA}")

if __name__ == "__main__":
    main()
