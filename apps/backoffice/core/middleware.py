from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from core.escopo import PossuiEscopoUnidade, usar_escopo


class EscopoUnidadeMiddleware:
    """Define o escopo de unidades do funcionário autenticado durante a request.

    Precisa vir depois do `AuthenticationMiddleware`. Request anônima segue sem escopo (fail-closed).
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        usuario = request.user
        if not usuario.is_authenticated or not isinstance(usuario, PossuiEscopoUnidade):
            return self.get_response(request)
        with usar_escopo(usuario.escopo_unidade()):
            return self.get_response(request)
