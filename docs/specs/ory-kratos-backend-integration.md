# Ory Kratos Backend Integration

## Problem Statement

Backend должен использовать развёрнутый self-hosted Ory Kratos для проверки browser-сессий и управления identities. Локальные пользователи, роли и аудит остаются в PostgreSQL, а login, password, состояние identity и сессии принадлежат Kratos.

## Solution

Добавить в backend изолированную интеграцию с Kratos Public и Admin API. Защищённые запросы проверяются через Kratos, административные операции координируются единым user-management модулем, а локальная read projection обеспечивает поиск и фильтрацию пользователей.

## User Stories

1. Как пользователь, я хочу входить через Kratos и обращаться к защищённому API с browser cookie.
2. Как администратор, я хочу создавать пользователя с login, password, ролью и явным состоянием активности.
3. Как администратор, я хочу просматривать, искать и фильтровать пользователей по локальным и identity-данным.
4. Как администратор, я хочу менять имя, роль, login и активность пользователя.
5. Как специалист по безопасности, я хочу немедленно закрывать доступ неактивной identity и отзывать её сессии.
6. Как оператор, я хочу автоматически создать первого администратора при первом запуске.
7. Как оператор, я хочу автоматически обнаруживать рассинхронизацию PostgreSQL и Kratos.
8. Как аудитор, я хочу видеть все успешные изменения пользователей и исправления reconciliation без чувствительных данных.

## Implementation Decisions

- Закрепить `ory-kratos-client==26.2.0`, соответствующий Kratos `v26.2.0`. Синхронные вызовы выполнять через AnyIO thread pool.
- Определить два seam: `SessionVerifier` для Public API и `IdentityManager` для Admin API. SDK-типы и ошибки не выходят за пределы adapters.
- Всю координацию Kratos, PostgreSQL, audit, компенсаций и блокировок скрыть в одном user-management модуле. Routers и bootstrap используют только его interface.
- Backend и prestart подключаются к internal network `web-identity`. Public URL по умолчанию `http://kratos:4433`, Admin URL — `http://kratos:4434`; оба переопределяются настройками.
- Public timeout по умолчанию 2 секунды, Admin timeout — 10 секунд. Automatic retries отключены. Лимиты параллелизма: Public 20, Admin 4; reconciler выполняет Admin-запросы последовательно. Значения настраиваемые.
- Business API работает fail-closed. Публичными остаются liveness/readiness и development API docs. Runtime OpenAPI/Swagger в production отключены.
- Backend извлекает и передаёт в Kratos только настраиваемую session cookie, по умолчанию `ory_kratos_session`. Результат `whoami` не кэшируется.
- Unsafe HTTP methods принимают только JSON и проверяют `Origin` по allowlist.
- Ошибки имеют единый envelope с lowercase `snake_case` code и request ID. Основные коды: `invalid_session`, `account_disabled`, `user_not_provisioned`, `forbidden`, `identity_provider_unavailable`, `login_already_exists`.
- Kratos является источником истины для login и активности. В `users` хранится read projection: nullable `identity_login`, `auth_state` (`active`, `inactive`) и nullable `auth_state_synced_at`. При отсутствующей identity локальная projection fail-closed переводится в `inactive`; это не является отдельным пользовательским статусом. Добавить индексы для состояния и поиска, включая `pg_trgm`.
- Reconciler запускается после startup и затем каждые 5 минут под PostgreSQL advisory lock. Он обновляет projection пакетами до 500 identities, обнаруживает `DB есть / Kratos нет` и `Kratos есть / DB нет`, а также логирует каждую рассинхронизацию один раз на процесс. Автоматически удалять или усыновлять orphan identity нельзя.
- Identity metadata использует namespace `provisioning` с `owner=backend`, `version=1`, `kind=standard|bootstrap` и `user_id`. `external_id` равен локальному user ID.
- `GET /users` поддерживает `q`, `role`, `auth_state`, `page`, `page_size`, `sort`, `order`. Поиск регистронезависимый по части имени/login. `page_size` по умолчанию 25, максимум 100. Список использует bounded-consistency projection.
- Добавить `GET /auth/me`, `GET /users`, `GET /users/{id}`, `POST /users`, обновление имени/роли, отдельные команды изменения login и активности.
- Permissions: `USER_READ`, `USER_CREATE`, `USER_UPDATE`, `USER_SET_LOGIN`, `USER_SET_ACTIVE`. На первом этапе они принадлежат только `ADMINISTRATOR`.
- Login строго валидируется по Kratos schema без нормализации. Изменение login не отзывает действующие сессии и обновляет Kratos до локальной projection.
- Создание всегда начинает с inactive identity. После локального commit identity активируется, только если обязательное поле запроса `active` равно `true`; `user.created` записывается только после полного успешного provisioning. После частичного сбоя coordinator компенсирует изменения в порядке Kratos identity, затем DB user; оба удаления идемпотентны и предпринимаются независимо. Частичные сбои возвращают `503 user_provisioning_failed`; `Idempotency-Key` пока не требуется.
- Деактивация сначала меняет state в Kratos, затем обновляет projection и отзывает все сессии. При ошибке отзыва возвращается `503`, identity остаётся inactive. Повторная активация не восстанавливает старые сессии.
- Нельзя деактивировать себя, снять с себя роль администратора или деактивировать/понизить последнего активного администратора. Проверка сериализуется PostgreSQL advisory lock и сверяет актуальные identities в Kratos.
- Password передаётся только в Kratos и никогда не сохраняется, не логируется, не возвращается и не включается в audit.
- Prestart bootstrap работает только при пустой таблице `users`, создаёт активного администратора и возобновляет собственный частично завершённый provisioning по metadata. Чужую identity автоматически не усыновляет.
- Bootstrap принимает password либо через `BACKEND_BOOTSTRAP_ADMIN_PASSWORD_FILE`, либо через `BACKEND_BOOTSTRAP_ADMIN_PASSWORD`; одновременное указание запрещено. При пустой таблице отсутствие обязательных bootstrap-настроек останавливает prestart.
- Аудировать создание, изменение имени/роли/login/активности, bootstrap и фактические reconciliation-исправления. Локальная projection и audit event записываются одной транзакцией.
- Kratos является обязательной readiness dependency. Ошибка отдельного reconciliation-прохода readiness не меняет.

## Testing Decisions

- Тестировать наблюдаемое поведение через interfaces user-management модуля, HTTP API и Kratos adapters, не внутренний порядок вызовов.
- Fast unit/API tests используют fake `SessionVerifier` и `IdentityManager` и проверяют permissions, CSRF, error mapping и частичные сбои.
- PostgreSQL integration tests проверяют projection, поиск/фильтры, audit, bootstrap и инвариант последнего администратора.
- Отдельный opt-in integration suite использует настоящий Kratos `v26.2.0` и проверяет provisioning, login, `whoami`, изменение login/state, отзыв сессий и reconciliation.
- Real-infrastructure tests остаются под существующим маркером `integration` и не входят в быстрый `pytest` по умолчанию.

## Out of Scope

- Frontend login и user-management UI.
- Удаление пользователя.
- Смена или reset password после создания.
- Операторская CLI.
- Auth/session caching.
- Автоматическое исправление orphan identities.
- Browser end-to-end tests.

## Further Notes

- Штатные identity-изменения после внедрения выполняются только через backend. Прямой Admin API считается break-glass каналом.
- Production login/logout flows остаются same-origin маршрутами Kratos через Traefik; backend их не проксирует.
