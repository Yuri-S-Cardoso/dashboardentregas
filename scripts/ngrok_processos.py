"""Agente filho: saída filtrada em memória, sem registrar credenciais ou tráfego."""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from threading import Event, Thread


def ambiente_ngrok():
    # Configuração e flags explícitas prevalecem; não herda opções NGROK_* ocultas.
    return {k: v for k, v in os.environ.items() if not k.upper().startswith("NGROK_")}


@dataclass(frozen=True)
class InstalacaoNgrok:
    executavel: Path
    configuracao: Path
    versao: str


def inspecionar_ngrok(executavel=None, configuracao=None):
    caminho = executavel or shutil.which("ngrok")
    if not caminho or not Path(caminho).is_file():
        raise ValueError("ngrok não encontrado no PATH. Instale/configure o agente conforme o guia, sem executar como administrador.")
    resultado = subprocess.run([str(caminho), "version"], capture_output=True, text=True, timeout=15, env=ambiente_ngrok())
    versao = re.fullmatch(r"ngrok version (3\.\d+\.\d+)\s*", resultado.stdout)
    if resultado.returncode or not versao or tuple(map(int, versao[1].split("."))) < (3, 35, 0):
        raise ValueError("Este modo foi preparado para ngrok 3.35.0 ou superior. Confira a versão instalada pelo canal oficial.")
    candidatos = [Path(configuracao)] if configuracao else [
        Path(os.environ.get("LOCALAPPDATA", "")) / "ngrok/ngrok.yml",
        Path.home() / ".config/ngrok/ngrok.yml", Path.home() / ".ngrok2/ngrok.yml",
    ]
    arquivo = next((p.resolve() for p in candidatos if p.is_file()), None)
    if not arquivo:
        raise ValueError("Configuração ngrok não encontrada. Configure o authtoken diretamente no agente; não o inclua no projeto ou relatório.")
    texto = arquivo.read_text(encoding="utf-8-sig")
    if not re.search(r"(?m)^version:\s*['\"]?3['\"]?\s*$", texto) or not re.search(r"(?m)^\s*authtoken:\s*\S+", texto):
        raise ValueError("É necessária uma configuração ngrok v3 com authtoken já cadastrado. O valor nunca será mostrado pelo inicializador.")
    resultado = subprocess.run([str(caminho), "config", "check", "--config", str(arquivo)],
                              capture_output=True, timeout=15, env=ambiente_ngrok())
    if resultado.returncode:
        raise ValueError("A configuração do agente ngrok é inválida. Confira-a no aplicativo ngrok; sua saída não foi reproduzida para proteger credenciais.")
    ajuda = subprocess.run([str(caminho), "http", "--help"], capture_output=True, text=True, timeout=15, env=ambiente_ngrok())
    if ajuda.returncode or not all(flag in ajuda.stdout for flag in ("--url", "--traffic-policy-file", "--inspect")):
        raise ValueError("O agente não oferece as opções de domínio, política e inspeção exigidas. O acesso online foi bloqueado.")
    return InstalacaoNgrok(Path(caminho).resolve(), arquivo, versao[1])


def validar_overlay(instalacao, overlay):
    # 'config check' aceita um arquivo; 'http --config' aceita a lista mesclada.
    # O arquivo original já foi conferido por inspecionar_ngrok.
    resultado = subprocess.run([str(instalacao.executavel), "config", "check", "--config", str(overlay)],
                              capture_output=True, timeout=15, env=ambiente_ngrok())
    if resultado.returncode:
        raise ValueError("O agente rejeitou as opções seguras de inspeção/desativação da interface local. Nenhum túnel foi aberto.")


def comando_tunel(instalacao, configuracao, overlay, politica):
    return [str(instalacao.executavel), "http", "http://127.0.0.1:8000", "--url", configuracao.origem,
            "--config", f"{instalacao.configuracao},{overlay}", "--traffic-policy-file", str(politica),
            "--inspect=false", "--log=stdout", "--log-format=json", "--log-level=info"]


class ProcessoNgrok:
    """Possui somente o processo que criou; nunca encerra instâncias de terceiros."""
    def __init__(self, comando, origem):
        self.comando, self.origem = comando, origem
        self.processo = None
        self.pronto, self.dominio_incorreto = Event(), Event()
        self.codigo_erro = ""
        self.leitor = None

    def iniciar(self):
        self.processo = subprocess.Popen(self.comando, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         text=True, encoding="utf-8", errors="replace", env=ambiente_ngrok(),
                                         creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        self.leitor = Thread(target=self._ler_eventos, daemon=True)
        self.leitor.start()

    def _ler_eventos(self):
        # Não mantém log bruto, cookies, URLs OAuth com state nem corpos HTTP.
        for linha in self.processo.stdout:
            codigo = re.search(r"\bERR_NGROK_[0-9]+\b", linha)
            if codigo:
                self.codigo_erro = codigo[0]
            try:
                evento = json.loads(linha)
            except ValueError:
                continue
            if isinstance(evento, dict) and evento.get("msg") == "started tunnel":
                if isinstance(evento.get("url"), str) and evento["url"].rstrip("/") == self.origem:
                    self.pronto.set()
                else:
                    self.dominio_incorreto.set()

    def encerrar(self):
        if self.processo is not None:
            if self.processo.poll() is None:
                self.processo.terminate()
                try:
                    self.processo.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.processo.kill()
                    self.processo.wait(timeout=5)
            if self.leitor is not None:
                self.leitor.join(timeout=2)
            self.processo.stdout.close()
