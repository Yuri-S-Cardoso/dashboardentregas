"""Seleção LAN e operação com um Waitress, sem modificar a rede ou o banco real."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
import http.client
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Barrier, Thread
from unittest.mock import patch

from django.test import SimpleTestCase
from waitress import create_server

from config.rede import interfaces_elegiveis
from scripts.iniciar_sistema import consultar_interfaces, escolher_ip


INTERFACE = dict(ip="192.168.1.10", nome="Ethernet", descricao="Placa de rede",
                 perfil="Private", fisica=True, ativa=True, tipo=6, indice=16,
                 secundario=False)


class InicializacaoLANTests(SimpleTestCase):
    def test_apenas_ethernet_wifi_fisicas_ativas_privadas_com_ipv4_rfc1918(self):
        alteracoes = [dict(ativa=False), dict(fisica=False), dict(tipo=23),
                      dict(perfil="Public"), dict(perfil="DomainAuthenticated"),
                      dict(perfil=""), dict(ip="169.254.1.2"), dict(ip="26.1.2.3"),
                      dict(ip="8.8.8.8"), dict(ip="::1"), dict(nome="Radmin VPN"),
                      dict(descricao="Hyper-V Virtual Ethernet"), dict(indice=None)]
        self.assertEqual(interfaces_elegiveis([INTERFACE]), [INTERFACE])
        wifi = {**INTERFACE, "tipo": 71, "nome": "Wi-Fi", "indice": 3}
        self.assertEqual(interfaces_elegiveis([wifi]), [wifi])
        for alteracao in alteracoes:
            with self.subTest(alteracao=alteracao):
                self.assertEqual(interfaces_elegiveis([{**INTERFACE, **alteracao}]), [])

    def test_varios_ips_da_mesma_interface_geram_uma_opcao_com_ip_principal(self):
        secundario = {**INTERFACE, "ip": "192.168.1.2", "secundario": True}
        outra = {**INTERFACE, "ip": "10.0.0.3", "indice": 3, "tipo": 71}
        opcoes = interfaces_elegiveis([secundario, INTERFACE, INTERFACE, outra])
        self.assertEqual(len(opcoes), 2)
        self.assertEqual({i["ip"] for i in opcoes}, {INTERFACE["ip"], outra["ip"]})

    def test_sem_interface_inicia_local_sem_perguntar_e_explica_requisitos(self):
        saida = StringIO()
        with redirect_stdout(saida), patch("builtins.input", side_effect=AssertionError("Não deve perguntar.")):
            self.assertIsNone(escolher_ip([]))
        for termo in ("Ethernet", "Wi-Fi", "ativa", "IPv4 privado", "Private", "localhost"):
            self.assertIn(termo, saida.getvalue())

    def test_interface_unica_selecionada_sem_pergunta(self):
        with patch("builtins.input", side_effect=AssertionError("Não deve perguntar.")):
            self.assertEqual(escolher_ip([INTERFACE]), INTERFACE["ip"])

    def test_multiplas_interfaces_solicitam_escolha_e_so_usam_a_escolhida(self):
        outra = {**INTERFACE, "ip": "10.0.0.3", "nome": "Wi-Fi", "indice": 3}
        saida = StringIO()
        with redirect_stdout(saida), patch("builtins.input", return_value="2") as entrada:
            self.assertEqual(escolher_ip([INTERFACE, outra]), outra["ip"])
        entrada.assert_called_once()
        self.assertIn("Ethernet", saida.getvalue())
        self.assertIn("Wi-Fi", saida.getvalue())

    def test_multiplas_interfaces_permitem_local_e_nao_inferem_escolha_sem_entrada(self):
        opcoes = [INTERFACE, {**INTERFACE, "ip": "10.0.0.3"}]
        for resposta in ("0", ""):
            with self.subTest(resposta=resposta), patch("builtins.input", return_value=resposta):
                self.assertIsNone(escolher_ip(opcoes))
        with patch("builtins.input", side_effect=EOFError):
            self.assertIsNone(escolher_ip(opcoes))

    def test_escolha_invalida_nao_seleciona_interface(self):
        for resposta in ("3", "-1", "abc"):
            with self.subTest(resposta=resposta), patch("builtins.input", return_value=resposta), self.assertRaises(ValueError):
                escolher_ip([INTERFACE, {**INTERFACE, "ip": "10.0.0.3"}])

    @patch("scripts.iniciar_sistema.os.name", "nt")
    def test_consulta_windows_interpreta_array_objeto_e_bom(self):
        for dados in ([INTERFACE], INTERFACE):
            resultado = subprocess.CompletedProcess([], 0, "\ufeff" + json.dumps(dados), "")
            with self.subTest(dados=dados), patch("scripts.iniciar_sistema.subprocess.run", return_value=resultado):
                self.assertEqual(consultar_interfaces(), [INTERFACE])

    @patch("scripts.iniciar_sistema.os.name", "nt")
    def test_falhas_na_consulta_limitam_acesso_ao_computador_com_explicacao(self):
        resultados = [subprocess.CompletedProcess([], 1, "", "erro"),
                      subprocess.CompletedProcess([], 0, "invalido", ""),
                      subprocess.CompletedProcess([], 0, '["invalido"]', ""),
                      subprocess.CompletedProcess([], 0, "null", "")]
        for resultado in resultados:
            saida = StringIO()
            with self.subTest(resultado=resultado), redirect_stdout(saida), patch("scripts.iniciar_sistema.subprocess.run", return_value=resultado):
                self.assertEqual(consultar_interfaces(), [])
                self.assertIn("somente neste computador", saida.getvalue())
        for erro in (OSError("indisponível"), subprocess.TimeoutExpired("powershell", 20)):
            with self.subTest(erro=erro), patch("scripts.iniciar_sistema.subprocess.run", side_effect=erro):
                self.assertEqual(consultar_interfaces(), [])

    def test_inicializador_configura_hosts_restritos_e_uma_instancia_waitress(self):
        # Processo novo permite conferir settings reais após a seleção, sem cache Django.
        codigo = '''
from contextlib import nullcontext, redirect_stdout
from io import StringIO
import json, os, sys
from unittest.mock import patch
import scripts.iniciar_sistema as inicializador
opcoes, argumentos, resposta = json.loads(sys.argv[1])
with patch.object(inicializador, 'consultar_interfaces', return_value=opcoes) as consulta, \\
     patch.object(inicializador, 'verificar_porta'), \\
     patch.object(inicializador, 'preparar_estaticos'), \\
     patch.object(inicializador, 'trava_exclusiva', return_value=nullcontext()), \\
     patch('django.core.management.call_command'), \\
     patch('django.contrib.auth.get_user_model'), \\
     patch('waitress.create_server') as criar, \\
     patch('builtins.input', return_value=resposta) as entrada, redirect_stdout(StringIO()) as saida:
    inicializador.main(argumentos)
    from django.conf import settings
    servidor = criar.return_value
    print_saida = {'hosts': settings.ALLOWED_HOSTS, 'debug': settings.DEBUG,
        'listen': criar.call_args.kwargs['listen'], 'criadas': criar.call_count,
        'run': servidor.run.call_count, 'close': servidor.close.call_count,
        'shutdown': servidor.task_dispatcher.shutdown.call_count,
        'consultas': consulta.call_count, 'perguntas': entrada.call_count,
        'saida': saida.getvalue()}
print(json.dumps(print_saida))
'''
        outra = {**INTERFACE, "ip": "10.0.0.3", "nome": "Wi-Fi", "indice": 3}
        casos = [([], [], "", None, 1, 0),
                 ([INTERFACE], [], "", INTERFACE["ip"], 1, 0),
                 ([INTERFACE, outra], [], "2", outra["ip"], 1, 1),
                 ([INTERFACE], ["--local"], "", None, 0, 0),
                 ([INTERFACE], ["--ip", INTERFACE["ip"]], "", INTERFACE["ip"], 1, 0)]
        for opcoes, argumentos, resposta, ip, consultas, perguntas in casos:
            with self.subTest(argumentos=argumentos, ip=ip):
                ambiente = {**os.environ, "DJANGO_ALLOWED_HOSTS": "192.168.99.99", "PYTHONIOENCODING": "utf-8"}
                resultado = subprocess.run([sys.executable, "-c", codigo, json.dumps([opcoes, argumentos, resposta])],
                                          cwd=Path(__file__).resolve().parent.parent, env=ambiente,
                                          capture_output=True, text=True, encoding="utf-8", timeout=30)
                self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)
                dados = json.loads(resultado.stdout)
                enderecos = ["127.0.0.1"] + ([ip] if ip else [])
                self.assertEqual(dados["hosts"], ["localhost", *enderecos])
                self.assertFalse(dados["debug"])
                self.assertEqual(dados["listen"], " ".join(f"{host}:8000" for host in enderecos))
                for acao in ("criadas", "run", "close", "shutdown"):
                    self.assertEqual(dados[acao], 1)
                self.assertEqual(dados["consultas"], consultas)
                self.assertEqual(dados["perguntas"], perguntas)
                self.assertIn("http://127.0.0.1:8000/", dados["saida"])
                if ip:
                    self.assertIn(f"http://{ip}:8000/", dados["saida"])

    def test_waitress_real_atende_dois_enderecos_locais_simultaneamente(self):
        # Dois loopbacks exercitam sockets reais sem publicar em uma rede não elegível.
        barreira = Barrier(2)
        corpo = f"mesma aplicacao, processo {os.getpid()}".encode()

        def aplicacao(environ, start_response):
            barreira.wait(timeout=5)
            start_response("200 OK", [("Content-Type", "text/plain"), ("Content-Length", str(len(corpo)))])
            return [corpo]

        servidor = create_server(aplicacao, listen="127.0.0.1:0 127.0.0.2:0", threads=2,
                                 asyncore_loop_timeout=0.05, expose_tracebacks=False)
        tarefa = Thread(target=servidor.run, daemon=True)
        tarefa.start()

        def solicitar(endereco):
            conexao = http.client.HTTPConnection(*endereco, timeout=10)
            try:
                conexao.request("GET", "/")
                resposta = conexao.getresponse()
                return resposta.status, resposta.read()
            finally:
                conexao.close()

        try:
            self.assertEqual(len(servidor.effective_listen), 2)
            with ThreadPoolExecutor(max_workers=2) as executor:
                respostas = list(executor.map(solicitar, servidor.effective_listen))
            self.assertEqual(respostas, [(200, corpo), (200, corpo)])
        finally:
            servidor.close()
            tarefa.join(timeout=3)
        self.assertFalse(tarefa.is_alive(), "Servidor de teste deve encerrar e liberar os dois sockets.")
