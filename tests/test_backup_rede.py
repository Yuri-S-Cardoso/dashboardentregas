from contextlib import closing
import hashlib
from io import StringIO
import json
import os
import subprocess
from pathlib import Path
import socket
import sqlite3
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase, override_settings
from core.backups import criar_backup, verificar_backup, TABELAS_OBRIGATORIAS
from core.locks import trava_exclusiva
from config.rede import hosts_permitidos, interfaces_elegiveis, ipv4_privado, verificar_porta
from scripts.iniciar_sistema import escolher_ip, CONSULTA_INTERFACES


def banco_teste(caminho, valor):
    with closing(sqlite3.connect(caminho)) as db:
        for tabela in TABELAS_OBRIGATORIAS:
            db.execute(f'CREATE TABLE "{tabela}" (id INTEGER PRIMARY KEY, valor TEXT)')
        db.execute("INSERT INTO entregas_entrega(valor) VALUES(?)", (valor,))
        db.commit()


class BackupTests(SimpleTestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix="entregas_teste_backup_")
        self.addCleanup(self.tmp.cleanup)
        self.pasta = Path(self.tmp.name).resolve()
        self.origem = self.pasta / "atual.sqlite3"
        banco_teste(self.origem, "atual")

    def test_backup_com_banco_em_uso_hash_integridade_e_manifesto(self):
        with closing(sqlite3.connect(self.origem)) as aberto:
            destino, info = criar_backup(self.origem, self.pasta / "backups")
            self.assertEqual(aberto.execute("SELECT valor FROM entregas_entrega").fetchone()[0], "atual")
        self.assertEqual(verificar_backup(destino)["integridade"], "ok")
        self.assertEqual(info["sha256"], hashlib.sha256(destino.read_bytes()).hexdigest())
        self.assertEqual(info["bytes"], destino.stat().st_size)
        self.assertTrue(destino.with_suffix(".sqlite3.json").exists())

    def test_nomes_unicos_sem_excluir_anteriores(self):
        primeiro, _ = criar_backup(self.origem, self.pasta / "backups")
        conteudo = primeiro.read_bytes()
        segundo, _ = criar_backup(self.origem, self.pasta / "backups")
        self.assertNotEqual(primeiro, segundo)
        self.assertEqual(primeiro.read_bytes(), conteudo)

    def test_origem_ausente_nao_cria_banco_vazio(self):
        ausente = self.pasta / "ausente.sqlite3"
        with self.assertRaises(ValueError):
            criar_backup(ausente, self.pasta / "backups")
        self.assertFalse(ausente.exists())

    def test_arquivo_invalido_ou_schema_estranho_rejeitado(self):
        invalido = self.pasta / "invalido.sqlite3"
        invalido.write_bytes(b"nao e sqlite")
        with self.assertRaises(sqlite3.DatabaseError):
            verificar_backup(invalido)
        with closing(sqlite3.connect(self.pasta / "outro.sqlite3")):
            pass
        with self.assertRaises(ValueError):
            verificar_backup(self.pasta / "outro.sqlite3")

    def test_manifesto_alterado_e_detectado(self):
        destino, _ = criar_backup(self.origem, self.pasta / "backups")
        manifesto = destino.with_suffix(".sqlite3.json")
        info = json.loads(manifesto.read_text(encoding="utf-8"))
        info["sha256"] = "0" * 64
        manifesto.write_text(json.dumps(info), encoding="utf-8")
        with self.assertRaisesMessage(ValueError, "SHA-256"):
            verificar_backup(destino)

    def test_falta_de_espaco_aborta_sem_apagar_backups(self):
        with patch("core.backups.shutil.disk_usage", return_value=type("Disco", (), {"free": 1})()):
            with self.assertRaisesMessage(ValueError, "Espaço"):
                criar_backup(self.origem, self.pasta / "backups")

    def restaurar(self, confirmar):
        selecionado = self.pasta / "selecionado.sqlite3"
        banco_teste(selecionado, "backup")
        with override_settings(BASE_DIR=self.pasta), patch.dict(settings.DATABASES["default"], {"NAME": self.origem}), patch("builtins.input", return_value=confirmar), patch("core.management.commands.restaurar_backup.connections.close_all"):
            call_command("restaurar_backup", str(selecionado), stdout=StringIO())
        return selecionado

    def test_restauracao_cancelada_preserva_atual(self):
        antes = self.origem.read_bytes()
        self.restaurar("NAO")
        self.assertEqual(self.origem.read_bytes(), antes)
        self.assertTrue(list((self.pasta / ".local/backups").glob("*.sqlite3")))

    def test_recuperacao_confirmada_somente_no_ambiente_isolado(self):
        self.restaurar("RESTAURAR")
        with closing(sqlite3.connect(self.origem)) as db:
            self.assertEqual(db.execute("SELECT valor FROM entregas_entrega").fetchone()[0], "backup")
        salvos = list((self.pasta / ".local/backups").glob("*.sqlite3"))
        self.assertEqual(len(salvos), 1)
        with closing(sqlite3.connect(salvos[0])) as db:
            self.assertEqual(db.execute("SELECT valor FROM entregas_entrega").fetchone()[0], "atual")
        self.assertEqual(list((self.pasta / ".local/restauracoes").iterdir()), [])

    def test_servidor_ativo_impede_restauracao(self):
        with trava_exclusiva(self.pasta / ".local/servidor.lock"), override_settings(BASE_DIR=self.pasta), patch.dict(settings.DATABASES["default"], {"NAME": self.origem}):
            with self.assertRaises(CommandError):
                call_command("restaurar_backup", str(self.origem), stdout=StringIO())


class RedeTests(SimpleTestCase):
    def test_consulta_windows_com_sintaxe_valida_sem_executar_rede(self):
        if os.name != "nt":
            self.skipTest("Parser PowerShell disponível no Windows.")
        parser = "$texto=[Console]::In.ReadToEnd(); $erros=$null; [System.Management.Automation.Language.Parser]::ParseInput($texto,[ref]$null,[ref]$erros) | Out-Null; if ($erros.Count) { $erros | Out-String | Write-Output; exit 1 }"
        resultado = subprocess.run(["powershell.exe", "-NoProfile", "-Command", parser], input=CONSULTA_INTERFACES, capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)

    def test_ipv4_rfc1918_e_hosts_explicitos(self):
        for ip in ["10.0.0.5", "172.16.0.1", "172.31.255.254", "192.168.1.10"]:
            self.assertTrue(ipv4_privado(ip))
        for ip in ["172.32.0.1", "8.8.8.8", "127.0.0.1", "169.254.1.1", "0.0.0.0", "*", "::1"]:
            self.assertFalse(ipv4_privado(ip))
        self.assertEqual(hosts_permitidos("localhost,127.0.0.1,192.168.1.10"), ["localhost", "127.0.0.1", "192.168.1.10"])

    def test_curingas_enderecos_publicos_e_hosts_invalidos_rejeitados(self):
        for texto in ["*", "localhost,*", "0.0.0.0", "example.com", "8.8.8.8", "http://localhost", ""]:
            with self.subTest(texto=texto), self.assertRaises(ValueError):
                hosts_permitidos(texto)

    def test_interfaces_vpn_virtuais_publicas_e_sem_perfil_privado_excluidas(self):
        padrao = dict(ip="192.168.1.10", nome="Wi-Fi", descricao="Placa sem fio", perfil="Private", fisica=True, ativa=True, tipo=71, indice=3)
        casos = [padrao, {**padrao, "nome": "VPN"}, {**padrao, "fisica": False}, {**padrao, "perfil": "Public"}, {**padrao, "ip": "8.8.8.8"}]
        self.assertEqual(interfaces_elegiveis(casos), [padrao])

    def test_selecao_automatica_explicita_e_modo_local(self):
        opcoes = [dict(ip="192.168.1.10", nome="Wi-Fi")]
        with patch("builtins.input", side_effect=AssertionError("Interface única não exige escolha.")):
            self.assertEqual(escolher_ip(opcoes), "192.168.1.10")
        self.assertEqual(escolher_ip(opcoes, solicitado="192.168.1.10"), "192.168.1.10")
        with self.assertRaises(ValueError):
            escolher_ip(opcoes, solicitado="192.168.1.11")
        self.assertIsNone(escolher_ip(opcoes, local=True))

    def test_porta_ocupada_e_invalida_informam_erro(self):
        with socket.socket() as ocupado:
            ocupado.bind(("127.0.0.1", 0))
            ocupado.listen(1)
            with self.assertRaises(ValueError):
                verificar_porta(["127.0.0.1"], ocupado.getsockname()[1])
        with self.assertRaises(ValueError):
            verificar_porta(["127.0.0.1"], 0)


class InterfaceEstaticaTests(TestCase):
    def test_whitenoise_serve_css_js_e_admin_com_debug_false(self):
        self.assertFalse(settings.DEBUG)
        for caminho in ["css/app.css", "css/responsivo.css", "js/graficos.js", "js/navegacao.js", "admin/css/base.css"]:
            with self.subTest(caminho=caminho):
                self.assertEqual(self.client.get("/static/" + caminho).status_code, 200)

    def test_backup_segredos_e_banco_nao_tem_download_publico(self):
        for caminho in ["/.local/secret_key", "/db.sqlite3", "/static/.local/secret_key", "/.local/backups/"]:
            self.assertEqual(self.client.get(caminho).status_code, 404)

    def test_paginas_carregam_estilo_mobile_e_menu_acessivel(self):
        resposta = self.client.get("/contas/entrar/")
        self.assertContains(resposta, "/static/css/responsivo.css")
        self.assertContains(resposta, 'name="viewport"')
        self.assertContains(resposta, 'lang="pt-BR"')
