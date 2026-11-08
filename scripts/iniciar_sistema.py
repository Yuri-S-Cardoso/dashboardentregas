"""Uma instância local/LAN; apenas consulta interfaces, sem alterar firewall/rede."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from config.rede import interfaces_elegiveis, verificar_porta
from core.locks import trava_exclusiva

CONSULTA_INTERFACES = r"""$ErrorActionPreference = 'Stop'
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = $OutputEncoding
$itens = @(Get-NetAdapter -Physical | Where-Object { $_.Status -eq 'Up' -and -not $_.Virtual -and $_.InterfaceType -in @(6, 71) } | ForEach-Object {
  $adaptador = $_
  $perfil = Get-NetConnectionProfile -InterfaceIndex $adaptador.ifIndex -ErrorAction SilentlyContinue
  Get-NetIPAddress -InterfaceIndex $adaptador.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.AddressState -eq 'Preferred' } | ForEach-Object {
    [PSCustomObject]@{ip=$_.IPAddress; nome=$adaptador.Name; descricao=$adaptador.InterfaceDescription; perfil=[string]$perfil.NetworkCategory; fisica=[bool]$adaptador.HardwareInterface; ativa=($adaptador.Status -eq 'Up'); tipo=[int]$adaptador.InterfaceType; indice=[int]$adaptador.ifIndex; secundario=[bool]$_.SkipAsSource}
  }
})
ConvertTo-Json -InputObject $itens -Compress
"""


def consultar_interfaces():
    if os.name != "nt":
        print("Consulta de interfaces do Windows indisponível neste sistema; acesso limitado ao computador.")
        return []
    try:
        resultado = subprocess.run(["powershell.exe", "-NoProfile", "-Command", CONSULTA_INTERFACES], capture_output=True, text=True, encoding="utf-8", timeout=20)
        if resultado.returncode:
            raise ValueError("A consulta do Windows falhou.")
        dados = json.loads(resultado.stdout.lstrip("\ufeff").strip() or "[]")
        if isinstance(dados, dict):
            dados = [dados]
        if not isinstance(dados, list) or not all(isinstance(item, dict) for item in dados):
            raise ValueError("Resposta de interfaces inválida.")
        return interfaces_elegiveis(dados)
    except (OSError, subprocess.TimeoutExpired, ValueError, TypeError):
        print("Não foi possível confirmar as interfaces e seus perfis de rede. O sistema iniciará somente neste computador; confira a conexão e tente novamente.")
        return []


def escolher_ip(opcoes, local=False, solicitado=None):
    """Seleciona a única interface automaticamente; só pergunta quando há várias."""
    if local:
        print("Modo somente computador solicitado (--local).")
        return None
    if solicitado:
        if solicitado not in [i["ip"] for i in opcoes]:
            raise ValueError("O IP solicitado não pertence a uma interface física elegível no perfil Privado.")
        return solicitado
    if not opcoes:
        print("Nenhuma interface Ethernet ou Wi-Fi física, ativa, com IPv4 privado e perfil Private (Privado) foi encontrada. Redes públicas, VPNs, interfaces virtuais ou desconectadas não são elegíveis. Iniciando somente em localhost.")
        return None
    if len(opcoes) == 1:
        interface = opcoes[0]
        print(f"Rede Privada selecionada automaticamente: {interface['nome']} — {interface['ip']}.")
        return interface["ip"]
    print("\nHá várias interfaces elegíveis. Escolha a rede usada pelo celular.")
    print("\n0 — Somente este computador (opção padrão)")
    for numero, interface in enumerate(opcoes, 1):
        print(f"{numero} — {interface['nome']}: {interface['ip']} (rede Privada)")
    try:
        resposta = input("Escolha o número da interface [0]: ").strip() or "0"
    except EOFError:
        resposta = "0"
    if not resposta.isdigit() or not 0 <= int(resposta) <= len(opcoes):
        raise ValueError("Escolha de interface inválida.")
    return opcoes[int(resposta) - 1]["ip"] if int(resposta) else None


def preparar_estaticos():
    from django.conf import settings
    from django.core.management import call_command
    raiz = settings.STATIC_ROOT
    fontes = [p for p in (BASE / "static").rglob("*") if p.is_file()]
    fontes += [p for p in (Path(__import__("django").__file__).parent / "contrib/admin/static").rglob("*") if p.is_file()]
    marcador = raiz / ".coleta_concluida"
    obrigatorios = [raiz / nome for nome in ("css/app.css", "css/responsivo.css", "js/graficos.js", "js/navegacao.js", "admin/css/base.css")]
    if not marcador.exists() or not all(p.is_file() for p in obrigatorios) or any(p.stat().st_mtime_ns > marcador.stat().st_mtime_ns for p in fontes):
        print("Preparando CSS, JavaScript e arquivos do Admin...")
        call_command("collectstatic", interactive=False, verbosity=0)
        marcador.touch()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inicia Entregas com Waitress na rede privada selecionada.")
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--local", action="store_true", help="Somente loopback, sem seleção de rede.")
    grupo.add_argument("--ip", help="IPv4 de interface física no perfil Privado, selecionado explicitamente.")
    parser.add_argument("--porta", type=int, default=8000)
    parser.add_argument("--verificar", action="store_true", help="Executa verificações sem iniciar o servidor.")
    args = parser.parse_args(argv)
    if sys.version_info[:2] != (3, 13):
        raise ValueError("Utilize Python 3.13 no ambiente .venv.")
    if Path(sys.prefix).resolve() != (BASE / ".venv").resolve():
        raise ValueError("Execute com .venv\\Scripts\\python.exe ou com Iniciar_Entregas.bat.")
    os.chdir(BASE)
    ip = escolher_ip(consultar_interfaces() if not args.local else [], args.local, args.ip)
    enderecos = ["127.0.0.1"] + ([ip] if ip else [])
    verificar_porta(enderecos, args.porta)
    os.environ["DJANGO_DEBUG"] = "0"
    os.environ["DJANGO_ALLOWED_HOSTS"] = ",".join(["localhost", *enderecos])
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()
    from django.conf import settings
    from django.core.management import call_command
    from django.contrib.auth import get_user_model
    if not Path(settings.DATABASES["default"]["NAME"]).is_file():
        raise ValueError("Banco não encontrado. Não será criado ou reinicializado automaticamente.")
    with trava_exclusiva(BASE / ".local/servidor.lock"):
        call_command("check", verbosity=0)
        call_command("migrate", check_unapplied=True, verbosity=0)
        preparar_estaticos()
        if not get_user_model().objects.exists():
            print("Ainda não existe usuário. Crie um acesso com: .venv\\Scripts\\python.exe manage.py createsuperuser")
        print(f"\nComputador: http://127.0.0.1:{args.porta}/")
        print(f"Celular na mesma rede (Wi-Fi do roteador): http://{ip}:{args.porta}/" if ip else "Acesso pelo celular desativado nesta execução (somente computador).")
        print("HTTP não criptografa o tráfego. Use apenas rede privada confiável. Ctrl+C encerra o servidor.")
        if args.verificar:
            print("Verificações concluídas. Nenhum servidor foi iniciado.")
            return
        from waitress import create_server
        from config.wsgi import application
        # Uma aplicação e um pool de workers atendem os dois endereços explícitos.
        servidor = create_server(application, listen=" ".join(f"{e}:{args.porta}" for e in enderecos), threads=4, expose_tracebacks=False, clear_untrusted_proxy_headers=True)
        try:
            servidor.run()
        finally:
            servidor.close()
            servidor.task_dispatcher.shutdown(timeout=5)
            print("Servidor encerrado.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Encerramento solicitado.")
    except Exception as erro:
        print(f"Não foi possível iniciar: {erro}", file=sys.stderr)
        raise SystemExit(1)
