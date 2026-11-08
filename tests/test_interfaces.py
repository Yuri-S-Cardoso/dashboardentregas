import secrets
from datetime import date, time
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from conferencia.models import EspelhoEmpresa, Pagamento
from entregas.models import Entrega
from jornadas.models import Jornada
from painel.models import Configuracao


class InterfacesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.senha = secrets.token_urlsafe(24)
        cls.usuario = get_user_model().objects.create_user(username="operador_teste", password=cls.senha)
        cls.admin = get_user_model().objects.create_superuser(username="admin_teste", password=secrets.token_urlsafe(24))
        cls.entrega = Entrega.objects.create(codigo="000123", data=date(2026, 10, 15), horario=time(12), situacao="Baixa realizada")
        cls.espelho = EspelhoEmpresa.objects.create(data_competencia=date(2026, 10, 15), valor_empresa=Decimal("160.00"))
        cls.jornada = Jornada.objects.create(data=date(2026, 10, 15))
        cls.pagamento = Pagamento.objects.create(data_pagamento=date(2026, 10, 25), inicio_quinzena=date(2026, 10, 1), fim_quinzena=date(2026, 10, 15), valor_recebido=Decimal("160.00"))

    def enderecos(self):
        return [
            reverse("painel:inicio"), reverse("painel:configuracoes"),
            reverse("entregas:lista"), reverse("entregas:nova"),
            reverse("entregas:editar", args=[self.entrega.pk]), reverse("entregas:excluir", args=[self.entrega.pk]),
            reverse("conferencia:espelhos"), reverse("conferencia:novo_espelho"), reverse("conferencia:editar_espelho", args=[self.espelho.pk]),
            reverse("conferencia:pagamentos"), reverse("conferencia:novo_pagamento"), reverse("conferencia:editar_pagamento", args=[self.pagamento.pk]),
            reverse("jornadas:lista"), reverse("jornadas:nova"), reverse("jornadas:editar", args=[self.jornada.pk]),
        ]

    def test_todas_as_paginas_e_posts_exigem_login(self):
        for endereco in self.enderecos():
            for metodo in (self.client.get, self.client.post):
                with self.subTest(url=endereco, metodo=metodo.__name__):
                    resposta = metodo(endereco)
                    self.assertEqual(resposta.status_code, 302)
                    self.assertIn(reverse("login"), resposta.url)
        self.assertEqual(Entrega.objects.count(), 1)

    def test_login_incorreto_correto_e_logout(self):
        resposta = self.client.post(reverse("login"), {"username": self.usuario.username, "password": secrets.token_urlsafe(24)})
        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        resposta = self.client.post(reverse("login"), {"username": self.usuario.username, "password": self.senha})
        self.assertRedirects(resposta, reverse("painel:inicio"))
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_todas_as_telas_renderizam_para_usuario_autenticado(self):
        self.client.force_login(self.usuario)
        for endereco in self.enderecos():
            with self.subTest(url=endereco):
                self.assertEqual(self.client.get(endereco).status_code, 200)

    def test_criar_editar_e_excluir_entrega_com_confirmacao(self):
        self.client.force_login(self.usuario)
        dados = {"codigo": "000123", "data": "2026-10-16", "horario": "17:15:22", "situacao": "Insucesso"}
        self.assertRedirects(self.client.post(reverse("entregas:nova"), dados), reverse("entregas:lista"))
        nova = Entrega.objects.order_by("pk").last()
        self.assertEqual(nova.codigo, "000123")
        self.assertEqual(nova.horario, time(17, 15, 22))
        dados.update(situacao="Baixa realizada", horario="18:00:00")
        self.assertRedirects(self.client.post(reverse("entregas:editar", args=[nova.pk]), dados), reverse("entregas:lista"))
        nova.refresh_from_db()
        self.assertEqual(nova.situacao, "Baixa realizada")
        self.assertEqual(nova.valor_previsto, Decimal("5.00"))
        endereco = reverse("entregas:excluir", args=[nova.pk])
        self.assertContains(self.client.get(endereco), "Confirmar exclusão")
        self.assertTrue(Entrega.objects.filter(pk=nova.pk).exists())
        self.assertRedirects(self.client.post(endereco), reverse("entregas:lista"))
        self.assertFalse(Entrega.objects.filter(pk=nova.pk).exists())
        self.assertTrue(Entrega.objects.filter(pk=self.entrega.pk).exists())

    def test_formulario_invalido_nao_grava(self):
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.post(reverse("entregas:nova"), {"codigo": "x"}).status_code, 200)
        self.assertEqual(Entrega.objects.count(), 1)

    def test_filtros_data_situacao_e_erro_visivel(self):
        self.client.force_login(self.usuario)
        Entrega.objects.create(codigo="outro", data=date(2026, 10, 16), horario=time(12), situacao="Insucesso")
        lista = reverse("entregas:lista")
        resposta = self.client.get(lista, {"data": "2026-10-15", "situacao": "Baixa realizada"})
        self.assertContains(resposta, "000123")
        self.assertNotContains(resposta, ">outro<")
        self.assertContains(self.client.get(lista, {"situacao": "Insucesso"}), ">outro<")
        resposta = self.client.get(lista, {"data": "invalida"})
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.context["filtro"].errors)
        self.assertEqual(resposta.context["paginator"].count, 0)

    def test_paginacao_preserva_filtros(self):
        self.client.force_login(self.usuario)
        Entrega.objects.bulk_create([
            Entrega(codigo=f"pagina-{i}", data=date(2026, 10, 15), horario=time(12), situacao="Baixa realizada", valor_por_baixa=Decimal("5.00"))
            for i in range(51)
        ])
        resposta = self.client.get(reverse("entregas:lista"), {"data": "2026-10-15", "situacao": "Baixa realizada", "page": 2})
        self.assertEqual(resposta.context["paginator"].count, 52)
        self.assertEqual(len(resposta.context["object_list"]), 2)
        self.assertIn("data=2026-10-15", resposta.context["filtros_query"])

    def test_formularios_espelho_jornada_pagamento_criam_e_editam(self):
        self.client.force_login(self.usuario)
        casos = [
            ("conferencia:novo_espelho", "conferencia:editar_espelho", EspelhoEmpresa, {"data_competencia": "2026-10-16", "baixas_pagas": "48", "insucessos": "2", "valor_empresa": "240,00", "documento": "OS teste"}),
            ("jornadas:nova", "jornadas:editar", Jornada, {"data": "2026-10-20", "custo_combustivel": "13,54"}),
            ("conferencia:novo_pagamento", "conferencia:editar_pagamento", Pagamento, {"data_pagamento": "2026-10-25", "inicio_quinzena": "2026-10-01", "fim_quinzena": "2026-10-15", "valor_recebido": "160,00", "comprovante": "referência"}),
        ]
        for criar, editar, modelo, dados in casos:
            with self.subTest(modelo=modelo.__name__):
                self.assertEqual(self.client.post(reverse(criar), dados).status_code, 302)
                registro = modelo.objects.order_by("pk").last()
                self.assertEqual(self.client.post(reverse(editar, args=[registro.pk]), dados).status_code, 302)
                self.assertEqual(modelo.objects.count(), 2)

    def test_configuracao_cria_versao_preservando_entrega(self):
        self.client.force_login(self.usuario)
        resposta = self.client.post(reverse("painel:configuracoes"), {"valor_por_baixa": "6,50", "meta_diaria": "350,00", "meta_semanal": "1.750,00", "meta_mensal": "7.000,00"})
        self.assertRedirects(resposta, reverse("painel:configuracoes"))
        self.assertEqual(Configuracao.objects.count(), 2)
        self.entrega.refresh_from_db()
        self.assertEqual(self.entrega.valor_por_baixa, Decimal("5.00"))
        self.assertEqual(Configuracao.atual().meta_mensal, Decimal("7000.00"))

    def test_painel_mostra_reais_e_jornada_mostra_ausencia(self):
        self.client.force_login(self.usuario)
        self.assertContains(self.client.get(reverse("painel:inicio"), {"periodo": "todos"}), "R$ 5,00")
        self.assertContains(self.client.get(reverse("jornadas:lista")), "Não informado")

    def test_csrf_ativo_em_todos_os_formularios_de_alteracao(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.usuario)
        for endereco in self.enderecos() + [reverse("logout")]:
            with self.subTest(url=endereco):
                self.assertContains(cliente.post(endereco, {}), "Acesso não permitido", status_code=403)
        pagina = cliente.get(reverse("entregas:nova"))
        self.assertContains(pagina, "csrfmiddlewaretoken")
        resposta = cliente.post(reverse("entregas:nova"), {"codigo": "CSRF", "data": "2026-10-21", "horario": "12:00", "situacao": "Insucesso", "csrfmiddlewaretoken": cliente.cookies["csrftoken"].value})
        self.assertEqual(resposta.status_code, 302)

    def test_admin_funciona_e_usuario_comum_nao_acessa(self):
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(reverse("admin:index")).status_code, 302)
        self.client.force_login(self.admin)
        for pagina in ["index", "entregas_entrega_changelist", "conferencia_espelhoempresa_changelist", "conferencia_pagamento_changelist", "jornadas_jornada_changelist", "painel_configuracao_changelist", "core_importacao_changelist"]:
            with self.subTest(pagina=pagina):
                self.assertEqual(self.client.get(reverse(f"admin:{pagina}")).status_code, 200)

    @override_settings(DEBUG=False)
    def test_paginas_de_erro_sem_detalhes_internos(self):
        self.assertContains(self.client.get("/pagina-inexistente/"), "Página não encontrada", status_code=404)
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(reverse("entregas:editar", args=[99999])).status_code, 404)
