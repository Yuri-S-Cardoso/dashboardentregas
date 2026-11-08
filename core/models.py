"""Rastreabilidade compartilhada, sem unicidade por código de entrega."""
from django.db import models


class Importacao(models.Model):
    nome_arquivo = models.CharField("arquivo", max_length=255)
    caminho = models.TextField("caminho lido")
    sha256 = models.CharField(max_length=64, unique=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    resumo = models.JSONField(default=dict)
    avisos = models.JSONField(default=list)

    class Meta:
        verbose_name = "importação"
        verbose_name_plural = "importações"

    def __str__(self):
        return f"{self.nome_arquivo} ({self.sha256[:12]})"


class RegistroOrigem(models.Model):
    importacao = models.ForeignKey(
        Importacao, null=True, blank=True, on_delete=models.PROTECT, editable=False
    )
    aba_origem = models.CharField(max_length=80, blank=True, editable=False)
    linha_origem = models.PositiveIntegerField(null=True, blank=True, editable=False)
    dados_origem = models.JSONField(default=dict, blank=True, editable=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        constraints = [models.UniqueConstraint(
            fields=["importacao", "aba_origem", "linha_origem"],
            name="%(app_label)s_%(class)s_origem_unica",
        )]

    @property
    def origem(self):
        if self.importacao_id:
            return f"Importação #{self.importacao_id} · {self.aba_origem}, linha {self.linha_origem}"
        return "Cadastro manual"
