"""Inicialização opt-in do ngrok; prova externa isolada antes dos dados reais."""
import argparse
import json
import os
from pathlib import Path
import secrets
import sys
from tempfile import TemporaryDirectory
from threading import Thread
from time import monotonic, sleep

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from config.acesso_online import carregar_configuracao, gerar_politica
from config.proxy_online import ProxyOnline
from config.rede import verificar_porta
from core.backups import verificar_backup
from core.locks import trava_exclusiva
from scripts.ngrok_processos import ProcessoNgrok, comando_tunel, inspecionar_ngrok, validar_overlay


def preparar_ambiente_django(configuracao, chave):
    os.environ.update(DJANGO_SETTINGS_MODULE="config.settings_online", DJANGO_DEBUG="0",
                      DJANGO_ALLOWED_HOSTS="localhost,127.0.0.1",
                      ENTREGAS_ONLINE_DOMINIO=configuracao.dominio,
                      ENTREGAS_ONLINE_EMAILS=json.dumps(configuracao.emails), ENTREGAS_ONLINE_PROXY_KEY=chave)


def aplicacao_de_prova(environ, start_response):
    # Não importa Django, não abre SQLite e não contém dados ou credenciais.
    corpo = "Validação da proteção ngrok. Nenhum dado do sistema é servido neste modo.\n".encode()
    start_response("200 OK", [("Content-Type", "text/plain; charset=utf-8"), ("Content-Length", str(len(corpo))),
                              ("Cache-Control", "no-store"), ("X-Frame-Options", "DENY"), ("X-Content-Type-Options", "nosniff")])
    return [corpo]


def executar_servicos(application, comando, origem, duracao=0):
    from waitress import create_server
    servidor = create_server(application, listen="127.0.0.1:8000", threads=4, expose_tracebacks=False,
                             clear_untrusted_proxy_headers=True, ident="", asyncore_loop_timeout=0.1)
    tarefa = Thread(target=servidor.run, daemon=True)
    agente = ProcessoNgrok(comando, origem)
    try:
        tarefa.start()
        print("Computador: http://127.0.0.1:8000/", flush=True)
        print("HTTPS configurado: " + origem, flush=True)
        print("Ctrl+C encerra o túnel e este servidor. O inicializador local permanece disponível.", flush=True)
        try:
            agente.iniciar()
        except OSError:
            print("Não foi possível executar o ngrok. O acesso pelo computador continua ativo.", flush=True)
        inicio = monotonic()
        informado_pronto = informado_erro = False
        while tarefa.is_alive() and (not duracao or monotonic() - inicio < duracao):
            if agente.dominio_incorreto.is_set():
                agente.encerrar()
                agente.dominio_incorreto.clear()
                print("ngrok informou outro domínio; o processo foi encerrado. Localhost continua ativo.", flush=True)
                informado_erro = True
            if agente.pronto.is_set() and not informado_pronto:
                print("O agente informou o endpoint HTTPS esperado. Isso não substitui a validação OAuth no celular.", flush=True)
                informado_pronto = True
            if agente.processo is not None and agente.processo.poll() is not None and not informado_erro:
                detalhe = " (" + agente.codigo_erro + ")" if agente.codigo_erro else ""
                print("ngrok encerrou" + detalhe + ". Confira conta, plano e política. Localhost continua ativo; Ctrl+C encerra.", flush=True)
                informado_erro = True
            sleep(0.2)
    finally:
        agente.encerrar()
        servidor.close()
        servidor.task_dispatcher.shutdown(timeout=5)
        tarefa.join(timeout=3)
        print("Túnel e servidor encerrados.", flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Entregas online com domínio e OAuth explicitamente autorizados.")
    modos = parser.add_mutually_exclusive_group()
    modos.add_argument("--verificar", action="store_true", help="Confere configuração sem abrir túnel ou servidor.")
    modos.add_argument("--testar-protecao", action="store_true", help="Serve somente uma mensagem de prova, sem Django ou SQLite.")
    parser.add_argument("--duracao-teste", type=int, default=0, help="Encerra a prova após N segundos (1 a 300).")
    parser.add_argument("--config", type=Path, default=BASE / ".local/ngrok_online.json")
    parser.add_argument("--ngrok-config", type=Path)
    args = parser.parse_args(argv)
    if args.duracao_teste and (not args.testar_protecao or not 1 <= args.duracao_teste <= 300):
        raise ValueError("A duração limitada só se aplica ao modo de prova, entre 1 e 300 segundos.")
    if sys.version_info[:2] != (3, 13) or Path(sys.prefix).resolve() != (BASE / ".venv").resolve():
        raise ValueError("Execute Iniciar_Entregas_Online.bat ou o Python 3.13 da .venv deste projeto.")
    os.chdir(BASE)
    if not (BASE / "db.sqlite3").is_file():
        raise ValueError("Banco existente não encontrado. Nenhum banco novo será criado.")
    configuracao = carregar_configuracao(args.config)
    instalacao = inspecionar_ngrok(configuracao=args.ngrok_config)
    print("ngrok " + instalacao.versao + "; configuração v3 válida e authtoken cadastrado (valor não exibido).", flush=True)
    print("Domínio autorizado: " + configuracao.origem, flush=True)
    print(f"OAuth Google: somente {len(configuracao.emails)} e-mail(s) explícito(s), além do login Django.", flush=True)
    identificador = configuracao.identificador_validacao(instalacao.versao)
    print("Identificador da configuração para revisão: " + identificador, flush=True)
    if not args.verificar and not args.testar_protecao:
        configuracao.exigir_ativacao_aprovada(instalacao.versao)
    chave = secrets.token_urlsafe(48)
    pasta_privada = (Path(os.environ["LOCALAPPDATA"]) / "Entregas/ngrok_runtime"
                     if os.name == "nt" else BASE / ".local/ngrok_runtime")
    # No Windows herda a proteção do perfil do usuário, fora do código e dos relatórios.
    pasta_privada.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="ngrok_exec_", dir=pasta_privada) as temporario:
        pasta = Path(temporario).resolve()
        assert pasta.is_relative_to(pasta_privada.resolve())
        overlay, politica = pasta / "agente.json", pasta / "politica.json"
        overlay.write_text(json.dumps({"version": "3", "agent": {"web_addr": False, "console_ui": False,
                                "remote_management": False, "log": "false"}}), encoding="utf-8")
        politica.write_text(json.dumps(gerar_politica(configuracao, chave)), encoding="utf-8")
        validar_overlay(instalacao, overlay)
        if args.verificar:
            verificar_backup(BASE / "db.sqlite3", conferir_manifesto=False)
            print("Banco íntegro; opções do agente verificadas. Nenhum servidor ou túnel foi iniciado.")
            print("A aceitação da política pelo plano e o login OAuth exigem o ensaio externo. Aprovação para dados reais: "
                  + ("registrada" if configuracao.revisao_aprovada and configuracao.validacao_externa_sha256 == identificador else "pendente"))
            return
        with trava_exclusiva(BASE / ".local/servidor.lock"):
            verificar_porta(["127.0.0.1"], 8000)
            if args.testar_protecao:
                print("MODO DE PROVA: sem Django e sem acesso aos registros. Valide e-mail permitido, negado e HTTPS antes de aprovar.", flush=True)
                application = aplicacao_de_prova
            else:
                preparar_ambiente_django(configuracao, chave)
                import django
                django.setup()
                from django.core.management import call_command
                from django.core.wsgi import get_wsgi_application
                from django.contrib.auth import get_user_model
                from scripts.iniciar_sistema import preparar_estaticos
                call_command("check", verbosity=0)
                call_command("migrate", check_unapplied=True, verbosity=0)
                verificar_backup(BASE / "db.sqlite3", conferir_manifesto=False)
                if not get_user_model().objects.filter(is_active=True).exists():
                    raise ValueError("Não existe usuário Django ativo. Crie um acesso local antes de ativar o modo online.")
                preparar_estaticos()
                application = get_wsgi_application()
            protegido = ProxyOnline(application, configuracao, chave)
            executar_servicos(protegido, comando_tunel(instalacao, configuracao, overlay, politica), configuracao.origem, args.duracao_teste)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Encerramento solicitado.")
    except Exception:
        # Não reproduz repr/traceback de subprocessos, ambientes ou políticas.
        erro = sys.exception()
        if isinstance(erro, (ValueError, RuntimeError)):
            print("Não foi possível iniciar online: " + str(erro), file=sys.stderr)
        else:
            print("Não foi possível iniciar online. Confira ambiente, porta, conta ngrok e o guia; detalhes sensíveis não foram exibidos.", file=sys.stderr)
        raise SystemExit(1)
