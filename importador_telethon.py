import asyncio
import json
import os
import re
import tempfile
from telethon import TelegramClient, functions, errors

# ============================================================
# CONFIGURAÇÕES DA SUA CONTA E TEMPOS
# ============================================================
API_ID = 000000
API_HASH = "00000"

ARQUIVO_GRUPOS = "grupos.txt"
ARQUIVO_PROGRESSO = "progresso_migracao.json"

# Configurações de Pausa e Lote:
INTERVALO_SEGUNDOS = 15     # Intervalo normal entre cada grupo (segundos)
GRUPOS_POR_LOTE = 10        # A cada quantos grupos fazer a pausa grande
PAUSA_LOTE_MINUTOS = 20     # Quantos minutos esperar na pausa grande

MODO_TESTE = False


# ============================================================
# GERENCIAMENTO DE PROGRESSO SEGURO
# ============================================================
def carregar_progresso():
    if not os.path.exists(ARQUIVO_PROGRESSO):
        return {"processados": [], "sucessos": [], "falhas": []}

    try:
        with open(ARQUIVO_PROGRESSO, "r", encoding="utf-8") as f:
            dados = json.load(f)
        dados.setdefault("processados", [])
        dados.setdefault("sucessos", [])
        dados.setdefault("falhas", [])
        return dados
    except Exception:
        return {"processados": [], "sucessos": [], "falhas": []}


def salvar_progresso(progresso):
    diretorio = os.path.dirname(os.path.abspath(ARQUIVO_PROGRESSO))
    fd, temporario = tempfile.mkstemp(dir=diretorio, prefix="progresso_", suffix=".tmp")

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(progresso, f, indent=4, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporario, ARQUIVO_PROGRESSO)
    except Exception:
        try:
            os.remove(temporario)
        except OSError:
            pass
        raise


def adicionar_unico(lista, valor):
    if valor not in lista:
        lista.append(valor)


# ============================================================
# EXTRAÇÃO DOS LINKS
# ============================================================
def extrair_alvos_do_arquivo(caminho):
    if not os.path.exists(caminho):
        print(f"❌ Arquivo '{caminho}' não encontrado!")
        return []

    alvos = []
    with open(caminho, "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue

            match_privado = re.search(r"(?:https?://)?t\.me/(?:\+|joinchat/)([A-Za-z0-9_-]+)", linha)
            if match_privado:
                alvos.append({"tipo": "privado", "hash": match_privado.group(1)})
                continue

            match_publico = re.search(r"(?:https?://)?t\.me/([A-Za-z0-9_]+)", linha)
            if match_publico:
                username = match_publico.group(1)
                if username.lower() not in {"joinchat", "addlist"}:
                    alvos.append({"tipo": "publico", "username": username})
                    continue

            match_username = re.search(r"@([A-Za-z0-9_]+)", linha)
            if match_username:
                alvos.append({"tipo": "publico", "username": match_username.group(1)})

    vistos = set()
    unicos = []
    for alvo in alvos:
        identificador = alvo.get("username") or alvo.get("hash")
        chave = (alvo["tipo"], identificador.lower())
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(alvo)

    return unicos


async def entrar_no_alvo(client, item):
    if item["tipo"] == "publico":
        await client(functions.channels.JoinChannelRequest(channel=item["username"]))
        return "sucesso"
    elif item["tipo"] == "privado":
        await client(functions.messages.ImportChatInviteRequest(hash=item["hash"]))
        return "sucesso"
    return "desconhecido"


# ============================================================
# FLUXO PRINCIPAL
# ============================================================
async def main():
    print("🚀 Inicializando cliente Telethon...")

    client = TelegramClient("sessao_migracao", API_ID, API_HASH)
    await client.start()

    me = await client.get_me()
    print(f"✅ Conectado como: {me.first_name} (@{me.username or me.phone})")

    todos_alvos = extrair_alvos_do_arquivo(ARQUIVO_GRUPOS)
    if not todos_alvos:
        print("❌ Nenhum canal/grupo válido encontrado.")
        await client.disconnect()
        return

    progresso = carregar_progresso()
    processados = set(progresso["processados"])

    alvos_pendentes = [
        item for item in todos_alvos
        if (item.get("username") or item.get("hash")) not in processados
    ]

    print("\n" + "=" * 45)
    print("📊 STATUS DA MIGRAÇÃO")
    print("=" * 45)
    print(f"Total de alvos no arquivo : {len(todos_alvos)}")
    print(f"Já processados            : {len(processados)}")
    print(f"Restantes para entrar     : {len(alvos_pendentes)}")
    print(f"Configuração do lote      : Pausa de {PAUSA_LOTE_MINUTOS}min a cada {GRUPOS_POR_LOTE} grupos")
    print("=" * 45 + "\n")

    if not alvos_pendentes:
        print("🎉 Todos os grupos do arquivo já foram processados!")
        await client.disconnect()
        return

    sucessos_nesta_sessao = 0

    for numero, item in enumerate(alvos_pendentes, 1):
        identificador = item.get("username") or item.get("hash")
        print(f"[{numero}/{len(alvos_pendentes)}] Processando: {identificador} ({item['tipo']})...")

        while True:
            try:
                await entrar_no_alvo(client, item)
                print(f"   ✅ Entrada realizada com sucesso!")
                adicionar_unico(progresso["sucessos"], identificador)
                adicionar_unico(progresso["processados"], identificador)
                salvar_progresso(progresso)
                sucessos_nesta_sessao += 1
                break

            except errors.UserAlreadyParticipantError:
                print("   ℹ️ Você já faz parte deste chat.")
                adicionar_unico(progresso["sucessos"], identificador)
                adicionar_unico(progresso["processados"], identificador)
                salvar_progresso(progresso)
                break

            except errors.FloodWaitError as e:
                print(f"\n⏳ [FLOOD_WAIT]: Telegram exigiu pausa de {e.seconds}s.")
                salvar_progresso(progresso)
                await asyncio.sleep(e.seconds)
                print("▶️ Tempo de espera concluído. Retomando...")
                continue

            except errors.ChannelsTooMuchError:
                print("\n❌ [LIMITE ATINGIDO]: Limite de canais da conta atingido!")
                salvar_progresso(progresso)
                await client.disconnect()
                return

            except errors.InviteRequestSentError:
                print("   📩 Solicitação enviada aos administradores.")
                adicionar_unico(progresso["sucessos"], identificador)
                adicionar_unico(progresso["processados"], identificador)
                salvar_progresso(progresso)
                break

            except errors.InviteHashExpiredError:
                print("   ⚠️ Link de convite expirado.")
                progresso["falhas"].append({"id": identificador, "motivo": "convite_expirado"})
                adicionar_unico(progresso["processados"], identificador)
                salvar_progresso(progresso)
                break

            except errors.ChannelPrivateError:
                print("   ⚠️ Canal privado ou banido.")
                progresso["falhas"].append({"id": identificador, "motivo": "canal_privado"})
                adicionar_unico(progresso["processados"], identificador)
                salvar_progresso(progresso)
                break

            except Exception as ex:
                print(f"   ❌ Erro ({type(ex).__name__}): {ex}")
                progresso["falhas"].append({"id": identificador, "motivo": str(ex)})
                adicionar_unico(progresso["processados"], identificador)
                salvar_progresso(progresso)
                break

        # VERIFICAÇÃO DO LOTE GRANDE
        if sucessos_nesta_sessao > 0 and sucessos_nesta_sessao % GRUPOS_POR_LOTE == 0 and numero < len(alvos_pendentes):
            total_segundos = PAUSA_LOTE_MINUTOS * 60
            print("\n" + "-" * 50)
            print(f"☕ Lote de {GRUPOS_POR_LOTE} grupos concluído com sucesso!")
            print(f"⏳ Pausando por {PAUSA_LOTE_MINUTOS} minutos para proteger a conta...")
            print("-" * 50)

            for restante in range(total_segundos, 0, -1):
                minutos_rest = restante // 60
                segundos_rest = restante % 60
                print(f"   Tempo restante de pausa: {minutos_rest:02d}:{segundos_rest:02d}...", end="\r")
                await asyncio.sleep(1)
            print("\n▶️ Pausa de lote finalizada! Retomando entradas...\n")
        else:
            # Intervalo normal curto entre um grupo e outro
            if numero < len(alvos_pendentes):
                print(f"   ⏱️ Aguardando {INTERVALO_SEGUNDOS}s...")
                await asyncio.sleep(INTERVALO_SEGUNDOS)

    print("\n" + "=" * 45)
    print("🎉 MIGRAÇÃO CONCLUÍDA!")
    print(f"Sucessos: {len(progresso['sucessos'])}")
    print(f"Falhas  : {len(progresso['falhas'])}")
    print("=" * 45)

    salvar_progresso(progresso)
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
