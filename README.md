# Raízes do Nordeste — Back-end

API da rede de lanchonetes Raízes do Nordeste (Projeto Multidisciplinar UNINTER 2026, trilha Back-end), com o fluxo
**Pedido → Pagamento (mock) → Atualização de status**, autenticação JWT com perfis, escopo por unidade e erro padronizado.

Repositório: https://github.com/xLucasSA/projeto-uninter-backend

## Requisitos

- Docker Desktop com Compose v2
- Git

Tudo roda em contêineres: Python 3.12 (uv), FastAPI, Django 5.2 e PostgreSQL 16. Não é preciso instalar Python nem
banco na máquina.

## Configuração

```powershell
Copy-Item .env.example .env      # Linux/macOS: cp .env.example .env
```

O `.env.example` já traz valores prontos para o ambiente local, incluindo `SEED_DEMO=true`, que cria os dados de
demonstração. Fora do ambiente local, troque todos os segredos (`*_PASSWORD`, `DJANGO_SECRET_KEY`, `JWT_SECRET` e
`PAYMENT_WEBHOOK_SECRET`). O `.env` nunca é versionado.

## Execução

```powershell
docker compose up -d --build
docker compose ps                # serviços healthy; backoffice-migrate e api-migrate com Exited (0)
```

O build instala as dependências de cada serviço a partir do `uv.lock`. Se a porta 5432 estiver em uso, altere
`POSTGRES_HOST_PORT` no `.env`.

## Banco, migrations e seed

O `docker compose up` faz tudo automaticamente, nesta ordem:

1. `postgres` cria os perfis de acesso e os schemas `catalogo` e `vendas`.
2. `backoffice-migrate` aplica as migrations do Django e a carga de demonstração (unidades, produtos, estoque,
   funcionários e totem).
3. `api-migrate` aplica as migrations do Alembic e cria a cliente de demonstração.

A carga é idempotente e roda a cada `up`. Para recriar o banco do zero (apaga os dados): `docker compose down -v` e,
em seguida, `docker compose up -d --build`.

## Documentação da API

| Item | Endereço |
|---|---|
| Swagger | http://localhost:8001/docs (também `/redoc` e `/openapi.json`) |
| Admin do back-office | http://localhost:8000/admin/ |
| Gateway de pagamento simulado | http://localhost:8002/docs |

## Credenciais de demonstração

Senha de todos os usuários: `Senha@123`.

| Perfil | Login |
|---|---|
| Cliente | `maria@exemplo.com` |
| Equipe de REC-01 | `atendente.rec`, `cozinha.rec`, `estoquista.rec` e `gerente.rec`, todos `@raizes.dev` |
| Matriz | `matriz@raizes.dev` |
| Superusuário (admin) | `admin@raizes.dev` |
| Totem de REC-01 | `clientId` `totem-rec-01`, segredo `totem-rec-01-segredo-demo` |

## Coleção Postman

Arquivos em `docs/postman/`: `raizes.postman_collection.json` (coleção) e `local.postman_environment.json` (ambiente).

1. Suba o ambiente e confira o seed, como descrito acima.
2. No Postman, importe os dois arquivos e selecione o ambiente **Raízes do Nordeste — local**
   (`baseUrl` = `http://localhost:8001`).
3. Rode a coleção inteira pelo **Runner**, na ordem das pastas: `00 Setup`, `01 Auth e acesso`, `02 Validação`,
   `03 Pedidos e estoque`, `04 Pagamento`, `05 Operação` e `06 Auditoria`.

A pasta `00 Setup` faz os logins e guarda tokens e IDs nas variáveis da coleção, então não é preciso copiar token à mão.
Ela também cadastra um cliente novo a cada execução, o que permite repetir a coleção sem recriar o banco.

Pelo terminal, sem instalar nada, com o Newman em Docker:

```powershell
docker run --rm --network raizes_default -v "${PWD}/docs:/etc/newman" postman/newman:6.1.3-alpine `
  run postman/raizes.postman_collection.json -e postman/local.postman_environment.json `
  --env-var baseUrl=http://api:8001
```

## Estrutura do repositório

```text
apps/api/            API FastAPI (domain, application, infrastructure, api) e migrations
apps/backoffice/     back-office Django (catálogo, estoque, unidades, funcionários e carga de demonstração)
apps/payment-mock/   gateway de pagamento simulado
infra/postgres/      inicialização do banco
docs/                coleção Postman e diagramas
docker-compose.yml   serviços e ordem de inicialização
```
