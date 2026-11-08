"""Cronologia, população, ambiguidades e preservação financeira da conciliação."""
import csv
from datetime import date, time
from decimal import Decimal
from io import BytesIO, StringIO
import secrets

from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse
from openpyxl import load_workbook

from core.periodos import FiltroPeriodo
from entregas.models import Entrega
from entregas.services.conciliacao import (
    BAIXA, INSUCESSO, REVISAO, conciliar_entregas,
)
from painel.dashboard import montar_dashboard
from painel.exportacao import exportar_conciliacao_csv, exportar_csv, exportar_xlsx
from painel.forms import FiltroPainelForm


class ConciliacaoTests(SimpleTestCase):
    def setUp(self):
        self.registros = []

    def registro(self, situacao=INSUCESSO, dia="2026-10-15", horario="12:00:00", codigo="000123", valor="5.00"):
        registro = Entrega(pk=len(self.registros) + 1, codigo=codigo,
                           data=date.fromisoformat(dia), horario=time.fromisoformat(horario) if horario else None,
                           situacao=situacao, valor_por_baixa=Decimal(valor))
        self.registros.append(registro)
        return registro

    def conciliar(self, filtro=None, referencia=None):
        return conciliar_entregas(self.registros, filtro, referencia)

    def test_insucesso_seguido_de_baixa_no_dia_seguinte(self):
        self.registro()
        self.registro(BAIXA, "2026-10-16")
        r = self.conciliar()
        self.assertEqual((r["concluidas"], r["recuperadas"], r["insucessos_reais"]), (1, 1, 0))
        self.assertEqual(r["sucesso_percentual"], 100)

    def test_recuperacao_varios_dias_depois_sem_prazo_inventado(self):
        self.registro()
        self.registro(BAIXA, "2026-11-20")
        self.assertEqual(self.conciliar()["recuperadas"], 1)

    def test_insucessos_repetidos_contam_uma_entrega_pendente(self):
        self.registro()
        self.registro(dia="2026-10-16")
        r = self.conciliar()
        self.assertEqual((r["com_insucesso"], r["insucessos_reais"], r["recuperadas"]), (1, 1, 0))
        self.assertEqual(r["ciclos"][0].tentativas, 2)

    def test_varios_insucessos_e_uma_baixa(self):
        for dia in ("2026-10-15", "2026-10-16", "2026-10-20"):
            self.registro(dia=dia)
        self.registro(BAIXA, "2026-10-21")
        r = self.conciliar()
        self.assertEqual(r["recuperadas"], 1)
        self.assertEqual((r["ciclos"][0].insucessos, r["ciclos"][0].tentativas), (3, 4))

    def test_baixas_repetidas_no_mesmo_dia_contam_uma_conclusao_com_alerta(self):
        self.registro(BAIXA, horario="10:00:00")
        self.registro(BAIXA, horario="10:05:00", valor="7.00")
        r = self.conciliar()
        self.assertEqual((r["concluidas"], r["alertas_financeiros"]), (1, 1))
        self.assertEqual(r["ciclos"][0].receita_registrada, Decimal("12.00"))

    def test_codigo_repetido_mesmo_dia_ordem_por_horario_e_nao_pk(self):
        self.registro(BAIXA, horario="15:00:00")
        self.registro(horario="10:00:00")
        r = self.conciliar()
        self.assertEqual(r["recuperadas"], 1)
        self.assertEqual(r["ciclos"][0].ids_registros, (2, 1))

    def test_baixa_anterior_nao_recupera_insucesso_posterior(self):
        self.registro(BAIXA, horario="10:00:00")
        self.registro(horario="15:00:00")
        r = self.conciliar()
        self.assertEqual((r["recuperadas"], r["codigos_em_revisao"], r["ciclos_em_revisao"]), (0, 1, 2))
        self.assertIsNone(r["sucesso_percentual"])
        self.assertIsNone(r["ciclos"][1].data_baixa)

    def test_possivel_reuso_separa_candidatos_sem_inventar_identidade(self):
        self.registro(BAIXA)
        self.registro(dia="2027-02-01")
        self.registro(BAIXA, "2027-02-02")
        r = self.conciliar()
        self.assertEqual(len(r["ciclos"]), 2)
        self.assertEqual(r["entregas_identificadas"], 0)
        self.assertTrue(all(c.situacao == REVISAO for c in r["ciclos"]))
        self.assertEqual(r["recuperadas"], 0)

    def test_baixas_em_datas_distintas_pedem_revisao(self):
        self.registro(BAIXA)
        self.registro(BAIXA, "2027-02-01")
        r = self.conciliar()
        self.assertEqual((r["concluidas"], r["codigos_em_revisao"]), (0, 1))

    def test_fim_de_mes_recuperacao_no_mes_seguinte(self):
        self.registro(dia="2026-10-31")
        self.registro(BAIXA, "2026-11-01")
        filtro = FiltroPeriodo(date(2026, 10, 1), date(2026, 10, 31))
        r = self.conciliar(filtro)
        self.assertEqual((r["recuperadas"], r["recuperadas_apos_periodo"]), (1, 1))
        passado = self.conciliar(filtro, date(2026, 10, 31))
        self.assertEqual((passado["concluidas"], passado["insucessos_reais"]), (0, 1))

    def test_quinzena_recuperada_na_segunda_nao_muda_populacao(self):
        self.registro()
        self.registro(BAIXA, "2026-10-16")
        primeira = self.conciliar(FiltroPeriodo(date(2026, 10, 1), date(2026, 10, 15)))
        segunda = self.conciliar(FiltroPeriodo(date(2026, 10, 16), date(2026, 10, 31)))
        self.assertEqual(primeira["recuperadas"], 1)
        self.assertEqual(segunda["entregas_identificadas"], 0)

    def test_horarios_ausentes_em_dias_distintos_permitem_cronologia(self):
        self.registro(horario=None)
        self.registro(BAIXA, "2026-10-16", horario=None)
        r = self.conciliar()
        self.assertEqual(r["recuperadas"], 1)
        self.assertIsNone(r["ciclos"][0].horario_baixa)

    def test_horario_ausente_no_mesmo_dia_exige_revisao(self):
        self.registro(horario=None)
        self.registro(BAIXA)
        r = self.conciliar()
        self.assertEqual((r["recuperadas"], r["codigos_em_revisao"]), (0, 1))

    def test_horario_empatado_nao_usa_pk_como_prova(self):
        self.registro()
        self.registro(BAIXA)
        r = self.conciliar()
        self.assertEqual(r["codigos_em_revisao"], 1)
        self.assertIsNone(r["ciclos"][0].data_baixa)

    def test_meia_noite_conhecida_nao_e_horario_ausente(self):
        self.registro(horario="00:00:00")
        self.registro(BAIXA, horario="00:00:01")
        self.assertEqual(self.conciliar()["recuperadas"], 1)

    def test_codigos_textuais_e_zeros_preservados(self):
        self.registro(BAIXA, codigo="000123")
        self.registro(codigo="123")
        r = self.conciliar()
        self.assertEqual((r["concluidas"], r["insucessos_reais"]), (1, 1))
        self.assertEqual({c.codigo for c in r["ciclos"]}, {"000123", "123"})

    def test_registros_sem_codigo_nao_sao_fundidos(self):
        self.registro(codigo="")
        self.registro(codigo="")
        r = self.conciliar()
        self.assertEqual(r["ciclos_em_revisao"], 2)
        self.assertEqual(r["entregas_identificadas"], 0)

    def test_taxa_final_por_entregas_e_nao_por_tentativas(self):
        self.registro()
        self.registro(BAIXA, "2026-10-16")
        self.registro(codigo="outro")
        self.registro(dia="2026-10-16", codigo="outro")
        r = self.conciliar()
        self.assertEqual(r["sucesso_percentual"], Decimal("50"))
        self.assertEqual(r["tentativas_populacao"], 4)

    def test_ausencia_de_registros_nao_divide_por_zero(self):
        r = self.conciliar()
        self.assertEqual((r["concluidas"], r["insucessos_reais"], r["recuperadas"]), (0, 0, 0))
        self.assertIsNone(r["sucesso_percentual"])
        self.assertIsNone(r["referencia"])

    def test_corte_historico_nao_consulta_futuro_para_ambiguidade(self):
        self.registro(BAIXA)
        self.registro(dia="2026-11-01")
        passado = self.conciliar(referencia=date(2026, 10, 31))
        self.assertEqual((passado["concluidas"], passado["codigos_em_revisao"]), (1, 0))
        self.assertEqual(self.conciliar()["codigos_em_revisao"], 1)

    def test_ocorrencias_identicas_continuam_no_historico(self):
        self.registro()
        self.registro()
        r = self.conciliar()
        self.assertEqual((r["ocorrencias_identicas"], r["ocorrencias_adicionais"]), (1, 1))
        self.assertEqual(r["ciclos"][0].tentativas, 2)

    def test_todos_os_filtros_usam_primeira_tentativa_e_historico_posterior(self):
        self.registro()
        self.registro(BAIXA, "2026-11-02")
        self.registro(BAIXA, "2026-10-01", codigo="antigo")
        parametros = [
            {"periodo": "todos"}, {"periodo": "dia", "dia": "2026-10-15"},
            {"periodo": "semana", "semana": "2026-10-15"},
            {"periodo": "mes", "mes": 10, "ano": 2026},
            {"periodo": "quinzena", "mes": 10, "ano": 2026, "quinzena": 1},
            {"periodo": "intervalo", "inicio": "2026-10-14", "fim": "2026-10-16"},
        ]
        for params in parametros:
            with self.subTest(params=params):
                form = FiltroPainelForm(params)
                self.assertTrue(form.is_valid(), form.errors)
                self.assertEqual(self.conciliar(form.cleaned_data["filtro"])["recuperadas"], 1)


class ConciliacaoIntegracaoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_user(username="conciliacao_teste", password=secrets.token_urlsafe(24))
        for codigo, dia, horario, situacao, valor in [
            ("000123", 15, time(12), INSUCESSO, "99.00"),
            ("000123", 16, time(10), BAIXA, "5.00"),
            ("000123", 16, time(11), BAIXA, "7.00"),
            ("outro", 15, None, INSUCESSO, "5.00"),
        ]:
            Entrega.objects.create(codigo=codigo, data=date(2026, 10, dia), horario=horario,
                                   situacao=situacao, valor_por_baixa=Decimal(valor))

    def setUp(self):
        self.client.force_login(self.usuario)

    def test_receita_historica_media_e_ocorrencias_preservadas(self):
        antes = list(Entrega.objects.values())
        p = montar_dashboard()
        self.assertEqual((p["resumo"]["tentativas"], p["resumo"]["baixas"], p["resumo"]["insucessos"]), (4, 2, 2))
        self.assertEqual((p["resumo"]["receita"], p["resumo"]["ganho_medio_baixa"]), (Decimal("12.00"), Decimal("6.00")))
        self.assertEqual((p["conciliacao"]["concluidas"], p["conciliacao"]["insucessos_reais"]), (1, 1))
        self.assertEqual(p["conciliacao"]["sucesso_percentual"], 50)
        self.assertEqual(p["conciliacao"]["alertas_financeiros"], 1)
        self.assertEqual(antes, list(Entrega.objects.values()))

    def test_filtro_mantem_receita_na_data_real_da_baixa(self):
        p = montar_dashboard(FiltroPeriodo(date(2026, 10, 15), date(2026, 10, 15)))
        self.assertEqual((p["resumo"]["receita"], p["resumo"]["baixas"]), (0, 0))
        self.assertEqual(p["conciliacao"]["recuperadas_apos_periodo"], 1)
        self.assertEqual(p["conciliacao_ate_fim"]["insucessos_reais"], 2)
        seguinte = montar_dashboard(FiltroPeriodo(date(2026, 10, 16), date(2026, 10, 16)))
        self.assertEqual(seguinte["resumo"]["receita"], 12)
        self.assertEqual(seguinte["conciliacao"]["concluidas"], 0)

    def test_cards_e_graficos_diferenciam_unidades(self):
        resposta = self.client.get(reverse("painel:inicio"), {"periodo": "todos"})
        for texto in ["Total com insucesso", "Insucesso Real", "Entregas recuperadas", "Taxa de Sucesso", "Baixas realizadas", "Os valores registrados foram preservados"]:
            self.assertContains(resposta, texto)
        auditoria = self.client.get(reverse("painel:auditoria"), {"periodo": "todos"})
        for texto in ["Sucesso por tentativa", "Ocorrências de baixa", "Ganho médio por baixa"]:
            self.assertContains(auditoria, texto)
        # O gráfico principal agora representa encomendas, não ocorrências por dia.
        series = resposta.context["dashboard"]["graficos"][0]["series"]
        self.assertEqual([serie["valores"] for serie in series], [[0], [1], [1]])

    def test_listagem_consulta_recuperadas_e_pendentes(self):
        rota = reverse("painel:conciliacao")
        recuperadas = self.client.get(rota, {"periodo": "todos", "situacao_conciliacao": "recuperada"})
        self.assertContains(recuperadas, "000123")
        self.assertNotContains(recuperadas, "<td>outro")
        self.assertEqual(recuperadas.context["pagina"].paginator.count, 1)
        pendentes = self.client.get(rota, {"periodo": "todos", "situacao_conciliacao": "insucesso_real"})
        self.assertContains(pendentes, "<td>outro")
        self.assertNotContains(pendentes, "<td>000123")
        self.assertContains(pendentes, "Sem baixa posterior registrada")

    def test_consulta_codigo_textual_e_vazia(self):
        resposta = self.client.get(reverse("painel:conciliacao"), {"periodo": "todos", "codigo": "000"})
        self.assertEqual(resposta.context["pagina"].paginator.count, 1)
        vazia = self.client.get(reverse("painel:conciliacao"), {"periodo": "todos", "codigo": "inexistente"})
        self.assertContains(vazia, "Nenhum código nesta consulta")
        self.assertNotContains(vazia, "Corrija os campos")

    def test_paginacao_sem_perder_filtro_e_tabela_acessivel(self):
        Entrega.objects.bulk_create([Entrega(codigo=f"novo{i:03}", data=date(2026, 10, 15),
                                            situacao=INSUCESSO, valor_por_baixa=5) for i in range(35)])
        resposta = self.client.get(reverse("painel:conciliacao"), {"periodo": "todos", "codigo": "novo", "pagina": 2})
        self.assertEqual(len(resposta.context["pagina"]), 5)
        self.assertContains(resposta, 'tabindex="0"')
        self.assertContains(resposta, "codigo=novo")
        self.assertContains(resposta, "Página 2 de 2")

    def test_rotas_exigem_login_somente_get_e_csv_privado(self):
        for nome in ("painel:conciliacao", "painel:exportar_conciliacao"):
            with self.subTest(nome=nome):
                self.assertEqual(Client().get(reverse(nome)).status_code, 302)
                self.assertEqual(self.client.post(reverse(nome)).status_code, 405)
        resposta = self.client.get(reverse("painel:exportar_conciliacao"), {"periodo": "todos"})
        self.assertEqual(resposta["Cache-Control"], "private, no-store")
        self.assertIn("attachment", resposta["Content-Disposition"])
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.usuario)
        self.assertEqual(csrf.post(reverse("painel:conciliacao")).status_code, 403)

    def test_filtros_invalidos_nao_vazam_historico(self):
        for nome in ("painel:conciliacao", "painel:exportar_conciliacao"):
            resposta = self.client.get(reverse(nome), {"periodo": "dia", "dia": "invalido"})
            self.assertEqual(resposta.status_code, 400 if nome.endswith("exportar_conciliacao") else 200)
            self.assertNotContains(resposta, "000123", status_code=resposta.status_code)
        resposta = self.client.get(reverse("painel:exportar_conciliacao"), {"situacao_conciliacao": "invalida"})
        self.assertEqual(resposta.status_code, 400)

    def test_csv_conciliacao_filtro_corte_e_registros_sem_formula(self):
        Entrega.objects.create(codigo="=1+1", data=date(2026, 10, 15), situacao=INSUCESSO, valor_por_baixa=5)
        filtro = FiltroPeriodo(date(2026, 10, 15), date(2026, 10, 15))
        dados = exportar_conciliacao_csv(filtro)
        self.assertTrue(dados.startswith(b"\xef\xbb\xbf"))
        linhas = list(csv.DictReader(StringIO(dados.decode("utf-8-sig")), delimiter=";"))
        codigos = {linha["Código"] for linha in linhas}
        self.assertEqual(codigos, {"000123", "outro", "'=1+1"})
        linha = next(linha for linha in linhas if linha["Código"] == "000123")
        self.assertEqual(linha["Baixa posterior / conclusão"], "16/10/2026")
        self.assertEqual(linha["Receita registrada (R$)"], "12,00")
        self.assertEqual(linha["Tentativas"], "3")

    def test_csv_respeita_consulta_e_nao_apenas_pagina(self):
        resposta = self.client.get(reverse("painel:exportar_conciliacao"), {"periodo": "todos", "codigo": "000", "situacao_conciliacao": "recuperada", "pagina": 99})
        linhas = list(csv.DictReader(StringIO(resposta.content.decode("utf-8-sig")), delimiter=";"))
        self.assertEqual([linha["Código"] for linha in linhas], ["000123"])

    def test_xlsx_resumo_coerente_e_csv_operacional_inalterado(self):
        antes = list(Entrega.objects.values())
        livro = load_workbook(BytesIO(exportar_xlsx(FiltroPeriodo())))
        self.addCleanup(livro.close)
        self.assertEqual(len(livro.sheetnames), 5)
        aba = livro["Resumo de Indicadores"]
        linhas = {r[0]: r[1] for r in aba.iter_rows(min_row=6, values_only=True)}
        self.assertEqual(linhas["Baixas realizadas — entregas distintas"], 1)
        self.assertEqual(linhas["Insucesso Real — sem baixa posterior registrada"], 1)
        self.assertEqual(linhas["Sucesso por encomenda distinta (%)"], 50)
        self.assertEqual(linhas["Faturamento previsto"], 12)
        self.assertEqual(len(list(csv.reader(StringIO(exportar_csv(FiltroPeriodo()).decode("utf-8-sig")), delimiter=";"))), 5)
        self.assertEqual(antes, list(Entrega.objects.values()))
