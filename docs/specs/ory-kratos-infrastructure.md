# Independent Ory Kratos Infrastructure Stack

## Problem Statement

Приложению нужна централизованная аутентификация по login и паролю. Identity-инфраструктура должна разворачиваться независимо от application stack, использовать существующие PostgreSQL и Traefik и не открывать административный API наружу.

## Solution

Добавить самостоятельный Compose project `web-identity` с Ory Kratos `v26.2.0`. Stack выполняет миграции перед запуском, подключается к отдельной БД `kratos`, публикует минимальный набор browser endpoints через `app.<domain>` и управляется через единый infrastructure CLI.

## User Stories

1. Как оператор, я хочу запускать и останавливать identity stack независимо, чтобы его lifecycle не зависел от приложения.
2. Как администратор, я хочу создавать пользователя с login и сразу заданным паролем, чтобы самостоятельная регистрация не требовалась.
3. Как пользователь, я хочу входить по login и паролю, даже если у меня нет email.
4. Как оператор, я хочу автоматически применять миграции перед запуском Kratos, чтобы сервер не работал с несовместимой схемой.
5. Как специалист по безопасности, я хочу закрыть registration, recovery, settings и Admin API от публичного доступа.
6. Как разработчик, я хочу использовать same-origin browser flows через Vite proxy в dev и Traefik в prod.
7. Как оператор, я хочу видеть понятную ошибку при отсутствии зависимых сетей или секретов.

## Implementation Decisions

- Закрепить образ `oryd/kratos:v26.2.0`.
- Использовать отдельный Compose project `web-identity` с сервисами миграции и Kratos; Kratos запускается только после успешной миграции.
- Stack создаёт и сохраняет собственную external network `web-identity`, но только проверяет наличие принадлежащих другим stacks сетей `web-database` и `traefik-public`.
- При инициализации нового PostgreSQL volume явно создавать БД `web_app` и `kratos`, их migrator/runtime роли и необходимые права через `/docker-entrypoint-initdb.d`. На существующем volume инициализацию повторно не выполнять.
- `kratos_migrator` владеет БД и схемой. `kratos_runtime` получает только CONNECT, USAGE, DML, sequence и соответствующие default privileges без DDL.
- Identity schema содержит единственный обязательный уникальный password identifier `login`: lowercase ASCII, 3–64 символа, шаблон `^[a-z0-9][a-z0-9._-]{2,63}$`.
- Включить только password method. Минимальная длина пароля — 12, identifier similarity check включён, HIBP отключён. Максимальную длину пока не задавать.
- Использовать Argon2id: 128 MiB памяти, 2 итерации, parallelism 1, salt 16 байт, key 32 байта.
- Registration, recovery и verification отключены. Settings flow не публикуется; самостоятельная смена пароля недоступна.
- Сессии непостоянные, сроком 12 часов, без автоматического продления; cookie host-only, Path `/`, SameSite Lax, Secure только в prod.
- CORS отключён. Разрешённый browser return origin: `http://localhost:5173` в dev и `https://app.${BASE_DOMAIN}` в prod.
- UI-контракт: login `/login`, flow error `/auth/error`, после logout `/login`, успешный/default return `/`.
- Через Traefik публиковать только login, logout, self-service errors, `/sessions/whoami` и identity schemas. Использовать native Kratos paths без дополнительного prefix.
- Для login router применить rate limit по IP: 10 запросов в минуту, burst 5.
- Admin API слушает внутренний TCP-порт Kratos `4434` и не публикуется через Traefik. В dev public/admin порты доступны исключительно на `127.0.0.1:4433` и `127.0.0.1:4434`; в prod host ports отсутствуют.
- Cookie и cipher secrets хранятся в игнорируемом identity `.env`, генерируются оператором один раз и не меняются автоматически. В репозитории остаются только placeholders.
- PostgreSQL-пароли Kratos хранятся в корневом `.env` как контракт database и identity stacks.
- CLI предоставляет `infra-identity up dev|prod`, `status dev|prod`, `down dev|prod`; `up` поддерживает health timeout и ожидает healthy Kratos.
- В prod лимиты памяти Kratos: 1 GiB; миграции: 512 MiB. В dev лимиты памяти не задавать.
- Логи: dev text/debug, prod JSON/info, sensitive values не выводить, telemetry/SQA отключить, Docker log rotation 10 MiB × 3.

## Testing Decisions

- Основной seam — инфраструктурный smoke test через публичные HTTP endpoints и Admin API на loopback в dev; внутреннюю реализацию Kratos не тестировать.
- Валидировать объединённые dev/prod Compose-конфигурации и обязательные environment variables.
- Проверить создание обеих баз, ролей и прав на новом PostgreSQL volume, а также отсутствие повторной инициализации на существующем volume.
- Проверить успешную миграцию, health/readiness Kratos и отказ запуска при ошибке миграции.
- Проверить публичную доступность разрешённых маршрутов и недоступность registration, recovery, settings, verification и Admin API через Traefik.
- Проверить создание identity с login и паролем, успешный login, `whoami`, logout, policy login/password и rate limit.

## Out of Scope

- Backend- и frontend-интеграция, включая UI входа, Vite proxy и readiness backend.
- CRUD пользователей, административная смена пароля, rename/disable пользователя и аудит в приложении.
- Самостоятельная регистрация, восстановление, verification, settings, email/SMTP и отдельный Ory UI container.
- Backup automation, metrics, tracing, HA и rollback миграций.

## Further Notes

- Kratos использует общий PostgreSQL cluster с приложением, поэтому production backup должен охватывать обе БД; перед обновлением Kratos требуется резервная копия.
- Операционный порядок запуска: database, Traefik, identity, application; остановка выполняется в обратном порядке.
