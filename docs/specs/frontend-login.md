# Frontend Login

## Problem Statement

Пользователю нужен полноценный вход в приложение через развёрнутый self-hosted Ory Kratos. Текущий frontend содержит только общий shell и не реализует browser login flow.

## Solution

Добавить русскоязычную страницу `/login` с отдельным полноэкранным layout и центрированной формой на shared UI-компонентах проекта. Страница загружает password login flow из Kratos через узкий same-origin adapter, отображает его поля и отправляет форму нативным browser `POST`.

## User Stories

1. Как пользователь, я хочу войти по login и password, чтобы получить browser-сессию приложения.
2. Как пользователь, я хочу видеть понятные ошибки Kratos рядом с формой и исправлять данные.
3. Как пользователь, я хочу показать или скрыть password перед отправкой.
4. Как пользователь с истёкшим или неверным flow, я хочу автоматически начать новый login flow.
5. Как пользователь клавиатуры или screen reader, я хочу доступную форму с корректными labels, focus и error semantics.
6. Как разработчик, я хочу использовать единый Base UI + shadcn стек без параллельной UI-системы Ory.

## Implementation Decisions

- Не использовать Ory Elements, `@ory/client-fetch` или другой Ory runtime SDK.
- Скрыть Kratos HTTP contract за узким frontend adapter на native `fetch`; наружу не выпускать transport-specific ошибки и необработанный payload.
- Без `flow` в URL выполнять browser navigation на `/self-service/login/browser`. С `flow` загружать его через `/self-service/login/flows` с same-origin cookies.
- Отправлять форму нативным `POST` в проверенный same-origin `flow.ui.action`. Kratos управляет CSRF, session cookie, validation redirects и возвратом на `/` после успеха.
- Поддержать только активный password contract: hidden CSRF, login, password, submit и flow/node messages. Неизвестный обязательный node считать несовместимым контрактом и показывать явную ошибку.
- Невалидный или истёкший flow перезапускать; невосстановимые self-service ошибки показывать на `/auth/error` с возможностью повторить вход.
- `/login` использует отдельный auth-layout без общего header и footer: нейтральный фон, центрированная карточка, название приложения и русский текст.
- Форму собирать только из shared UI-компонентов проекта на Base UI + shadcn. Добавить password visibility toggle; не добавлять registration, recovery и remember-me controls.
- В development проксировать опубликованные Kratos Public routes из Vite на loopback Public API. Production остаётся на существующей same-origin маршрутизации Traefik.
- Не логировать login flow payload, CSRF token или password.

## Testing Decisions

- Главный seam — наблюдаемый browser flow: Playwright проверяет инициализацию, validation error, успешный вход и возврат в приложение через настоящий Kratos в opt-in infrastructure scenario.
- Быстрые tests проверяют страницу с подменённым adapter: loading, сообщения, password toggle, restart flow и невосстановимую ошибку.
- Adapter tests проверяют mapping поддерживаемых nodes, отказ на несовместимом node и отсутствие чувствительных данных в ошибках.
- Тестировать внешнее поведение и доступную разметку, а не внутренний порядок вызовов или структуру компонентов.

## Out of Scope

- Registration, recovery, verification, settings, MFA, OIDC, passkeys и универсальный renderer всех Ory UI nodes.
- Remember-me, постоянная session cookie и session caching.
- User-management UI, logout flow, route guards и редизайн общего application shell.
- i18n framework и дополнительные языки.

## Further Notes

- Kratos `v26.2.0` и identity schema с обязательным lowercase login остаются источником истины для flow contract.
- Расширение способов входа требует явного расширения adapter contract и тестовой матрицы; неизвестные nodes нельзя молча игнорировать.
