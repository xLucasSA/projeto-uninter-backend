from raizes_api.domain.compartilhado.erros import ErroDominio


class UnidadeNaoEncontrada(ErroDominio):
    codigo = "UNIDADE_NAO_ENCONTRADA"
    mensagem_padrao = "A unidade não existe ou está inativa."


class ProdutoNaoEncontrado(ErroDominio):
    codigo = "PRODUTO_NAO_ENCONTRADO"
    mensagem_padrao = "Um ou mais produtos não existem."


class ProdutoIndisponivelNaUnidade(ErroDominio):
    codigo = "PRODUTO_INDISPONIVEL_NA_UNIDADE"
    mensagem_padrao = "Um ou mais produtos não estão disponíveis no cardápio desta unidade hoje."
