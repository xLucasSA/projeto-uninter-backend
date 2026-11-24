import uuid
from dataclasses import dataclass
from datetime import datetime

from raizes_api.application.autorizacao import VerificacaoDeEscopo
from raizes_api.application.paginacao import Pagina, Paginacao
from raizes_api.application.ports.leitura import (
    FiltroPedidos,
    LeituraPedidos,
    MudancaDeStatus,
    PedidoDetalhe,
    PedidoResumo,
)
from raizes_api.domain.compartilhado.atores import AtorAutenticado, TipoAtor
from raizes_api.domain.compartilhado.canais import CanalPedido
from raizes_api.domain.compartilhado.erros import DetalheErro, ErroDominio
from raizes_api.domain.compartilhado.escopo import unidades_do_escopo
from raizes_api.domain.pedidos.erros import PedidoNaoEncontrado
from raizes_api.domain.pedidos.status import StatusPedido

ENTIDADE_UNIDADE = "UNIDADE"


class PeriodoInvalido(ErroDominio):
    codigo = "VALIDACAO"
    mensagem_padrao = "Um ou mais campos são inválidos."


@dataclass(frozen=True, slots=True)
class CriteriosDaLista:
    unidade_id: int | None = None
    canal: CanalPedido | None = None
    status: StatusPedido | None = None
    inicio: datetime | None = None
    fim: datetime | None = None


class ListarPedidos:
    """Cliente vê só os próprios pedidos; funcionário, os das unidades do escopo; MATRIZ, todos."""

    def __init__(self, leitura: LeituraPedidos, escopo: VerificacaoDeEscopo) -> None:
        self._leitura = leitura
        self._escopo = escopo

    async def executar(
        self, ator: AtorAutenticado, criterios: CriteriosDaLista, paginacao: Paginacao
    ) -> Pagina[PedidoResumo]:
        if criterios.inicio and criterios.fim and criterios.inicio > criterios.fim:
            raise PeriodoInvalido(
                detalhes=[DetalheErro("dataInicio", "Deve ser anterior ou igual a dataFim.")]
            )
        if criterios.unidade_id is not None:
            await self._escopo.exigir(
                ator, criterios.unidade_id, entidade=ENTIDADE_UNIDADE, entidade_id=str(criterios.unidade_id)
            )
        filtro = FiltroPedidos(
            unidades=unidades_do_escopo(ator),
            cliente_id=uuid.UUID(ator.id) if ator.tipo is TipoAtor.CLIENTE else None,
            unidade_id=criterios.unidade_id,
            canal=criterios.canal,
            status=criterios.status,
            inicio=criterios.inicio,
            fim=criterios.fim,
        )
        return await self._leitura.listar(filtro, paginacao)


class ObterPedido:
    def __init__(self, leitura: LeituraPedidos, escopo: VerificacaoDeEscopo) -> None:
        self._leitura = leitura
        self._escopo = escopo

    async def executar(self, ator: AtorAutenticado, pedido_id: uuid.UUID) -> PedidoDetalhe:
        pedido = await self._leitura.obter(pedido_id)
        if pedido is None:
            raise PedidoNaoEncontrado()
        await self._escopo.exigir_acesso_ao_pedido(ator, pedido.id, pedido.vinculos)
        return pedido


class ObterHistoricoDoPedido:
    def __init__(self, leitura: LeituraPedidos, escopo: VerificacaoDeEscopo) -> None:
        self._obter_pedido = ObterPedido(leitura, escopo)
        self._leitura = leitura

    async def executar(self, ator: AtorAutenticado, pedido_id: uuid.UUID) -> list[MudancaDeStatus]:
        await self._obter_pedido.executar(ator, pedido_id)
        return await self._leitura.historico(pedido_id)
