# FastAPI Full-Stack Template: навигация, загрузка и пагинация

Проверено 18 августа 2026 года по `master` репозитория
[`fastapi/full-stack-fastapi-template`](https://github.com/fastapi/full-stack-fastapi-template) — commit
[`162344da111e833b30892728372ab95331f06873`](https://github.com/fastapi/full-stack-fastapi-template/tree/162344da111e833b30892728372ab95331f06873).

## Вывод

Шаблон **не реализует визуальный pending-state для перехода между маршрутами**. Он использует
TanStack Router и React Query, но скелетон есть только у области таблицы внутри отдельных страниц.
Поэтому это не образец решения проблемы «во время перехода всё ещё видна предыдущая страница»:
при ожидании проверки маршрута или данных старый route может оставаться на экране, а после монтирования
нового route скелетон заменит лишь таблицу — заголовок и описание уже будут видны.

## Маршруты и навигация

- Приложение создаёт `QueryClient`, `createRouter({ routeTree })` и рендерит `RouterProvider`.
  В конфигурации роутера нет `defaultPendingComponent` либо другого глобального индикатора:
  [`main.tsx`, строки 31–56](https://github.com/fastapi/full-stack-fastapi-template/blob/162344da111e833b30892728372ab95331f06873/frontend/src/main.tsx#L31-L56).
- Корневой route выводит только `HeadContent`, `Outlet`, DevTools и компоненты error/not found — pending UI отсутствует:
  [`__root.tsx`, строки 7–18](https://github.com/fastapi/full-stack-fastapi-template/blob/162344da111e833b30892728372ab95331f06873/frontend/src/routes/__root.tsx#L7-L18).
- Общий layout держит sidebar, header и `Outlet`, также без loading boundary:
  [`_layout.tsx`, строки 12–40](https://github.com/fastapi/full-stack-fastapi-template/blob/162344da111e833b30892728372ab95331f06873/frontend/src/routes/_layout.tsx#L12-L40).
- Пункты sidebar — обычные `RouterLink`. `useRouterState()` используется только для определения активного URL;
  состояние навигации (`isLoading`/pending) не читается и в интерфейсе не показывается:
  [`Sidebar/Main.tsx`, строки 23–60](https://github.com/fastapi/full-stack-fastapi-template/blob/162344da111e833b30892728372ab95331f06873/frontend/src/components/Sidebar/Main.tsx#L23-L60).
- У маршрута `/admin` есть асинхронный `beforeLoad`, вызывающий `readUserMe()` перед допуском на страницу.
  Для этой задержки отдельного UI тоже нет:
  [`admin.tsx`, строки 20–37](https://github.com/fastapi/full-stack-fastapi-template/blob/162344da111e833b30892728372ab95331f06873/frontend/src/routes/_layout/admin.tsx#L20-L37).

## Данные и визуальная загрузка

- Страницы `/items` и `/admin` получают данные через `useSuspenseQuery` из React Query.
  В каждой запрос вынесен в дочерний компонент таблицы, обёрнутый в `Suspense`:
  [`items.tsx`, строки 12–18 и 31–54](https://github.com/fastapi/full-stack-fastapi-template/blob/162344da111e833b30892728372ab95331f06873/frontend/src/routes/_layout/items.tsx#L12-L54),
  [`admin.tsx`, строки 12–18 и 39–56](https://github.com/fastapi/full-stack-fastapi-template/blob/162344da111e833b30892728372ab95331f06873/frontend/src/routes/_layout/admin.tsx#L12-L56).
- Fallback — специальные table-skeleton компоненты, по пять строк, а не текстовый или полноэкранный loader:
  [`PendingItems.tsx`](https://github.com/fastapi/full-stack-fastapi-template/blob/162344da111e833b30892728372ab95331f06873/frontend/src/components/Pending/PendingItems.tsx#L11-L46),
  [`PendingUsers.tsx`](https://github.com/fastapi/full-stack-fastapi-template/blob/162344da111e833b30892728372ab95331f06873/frontend/src/components/Pending/PendingUsers.tsx#L11-L53).
- Заголовок, описание и кнопка создания находятся **вне** `Suspense`, поэтому после монтирования нового route
  появляются сразу, тогда как загружается только таблица:
  [`items.tsx`, строки 57–70](https://github.com/fastapi/full-stack-fastapi-template/blob/162344da111e833b30892728372ab95331f06873/frontend/src/routes/_layout/items.tsx#L57-L70),
  [`admin.tsx`, строки 59–74](https://github.com/fastapi/full-stack-fastapi-template/blob/162344da111e833b30892728372ab95331f06873/frontend/src/routes/_layout/admin.tsx#L59-L74).
- Используемые версии подтверждают стек: React Query 5, TanStack Router 1 и TanStack Table 8:
  [`package.json`, строки 29–34](https://github.com/fastapi/full-stack-fastapi-template/blob/162344da111e833b30892728372ab95331f06873/frontend/package.json#L29-L34).

## Пагинация

- Сетевые запросы всегда запрашивают одну выборку `skip: 0, limit: 100`; это не зависит от выбранной пользователем страницы:
  [`items.tsx`, строки 12–18](https://github.com/fastapi/full-stack-fastapi-template/blob/162344da111e833b30892728372ab95331f06873/frontend/src/routes/_layout/items.tsx#L12-L18),
  [`admin.tsx`, строки 12–18](https://github.com/fastapi/full-stack-fastapi-template/blob/162344da111e833b30892728372ab95331f06873/frontend/src/routes/_layout/admin.tsx#L12-L18).
- Query key — соответственно только `["items"]` и `["users"]`: в нём нет номера страницы, page size и route search params. Следовательно, отдельного React Query-кэша по страницам нет; URL тоже не отражает номер страницы.
- `DataTable` передаёт уже загруженный массив в `useReactTable` с `getPaginationRowModel()` — это **клиентская пагинация** первых 100 записей:
  [`DataTable.tsx`, строки 37–46](https://github.com/fastapi/full-stack-fastapi-template/blob/162344da111e833b30892728372ab95331f06873/frontend/src/components/Common/DataTable.tsx#L37-L46).
- UI показывает диапазон по `data.length`, даёт выбор размера страницы `5/10/25/50` и кнопки first/previous/next/last;
  они меняют локальное table state (`setPageSize`, `previousPage`, `nextPage`, `setPageIndex`), не инициируя HTTP-запрос:
  [`DataTable.tsx`, строки 93–190](https://github.com/fastapi/full-stack-fastapi-template/blob/162344da111e833b30892728372ab95331f06873/frontend/src/components/Common/DataTable.tsx#L93-L190).
- Поэтому на переключении страниц нет ни сетевой задержки, ни специального pending-state. Скелетоны `PendingItems`/`PendingUsers` относятся только к первоначальной Suspense-загрузке query, а не к клиентской пагинации.

## Следствие для «Список ↔ Аудит»

У шаблона можно заимствовать идею table-skeleton, но не механизм навигационной загрузки: его там нет.
Чтобы сразу скрывать старый экран при смене «Список»/«Аудит», pending-state нужно реализовать выше `Outlet`
либо вокруг содержимого целевой страницы и связать его с состоянием TanStack Router. Для честной серверной
пагинации потребуются `page`/`pageSize` в URL и query key, передача их в `skip`/`limit`, а также отдельное
состояние `isFetching` для обновления страницы.
