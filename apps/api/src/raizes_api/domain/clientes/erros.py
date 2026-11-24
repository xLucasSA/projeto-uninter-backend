from raizes_api.domain.compartilhado.erros import ErroDominio


class EmailJaCadastrado(ErroDominio):
    codigo = "EMAIL_JA_CADASTRADO"
    mensagem_padrao = "Já existe uma conta com este e-mail."


class TelefoneJaCadastrado(ErroDominio):
    codigo = "TELEFONE_JA_CADASTRADO"
    mensagem_padrao = "Já existe uma conta com este telefone."


class ConsentimentoJaAtivo(ErroDominio):
    codigo = "CONSENTIMENTO_JA_ATIVO"
    mensagem_padrao = "Já existe um consentimento ativo para esta finalidade."


class ConsentimentoNaoEncontrado(ErroDominio):
    codigo = "CONSENTIMENTO_NAO_ENCONTRADO"
    mensagem_padrao = "Não há consentimento ativo para esta finalidade."
