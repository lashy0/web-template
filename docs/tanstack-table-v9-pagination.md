# TanStack Table v9: пагинация общего `DataTable`

Дата проверки: 18.08.2026. Версия в проекте — `@tanstack/react-table`/`@tanstack/table-core` **9.1.2**.

## Вывод

Текущая таблица уже использует правильную v9-модель: подключены только
`rowPaginationFeature` и `createPaginatedRowModel()`, а компонент подписан
только на `state.pagination`. Однако копии `columns` и `data` через
`useMemo(() => [...value], [value])` в
[`DataTable.tsx`](../apps/frontend/src/components/Common/DataTable.tsx) не
являются рекомендуемым способом стабилизации входов. Лучше передавать исходные
массивы непосредственно в `useTable` и сделать стабильными их владельцев.

`data` и `columns` — входы модели: при смене их ссылки Table заново строит
зависимые модели. Для клиентской пагинации такая настоящая смена данных также
по умолчанию возвращает пользователя на первую страницу. Это полезная политика
после обновления списка, но она не должна срабатывать от повторного рендера.

## Что происходит сейчас

| Участок | Оценка | Причина |
| --- | --- | --- |
| `dataTableFeatures` в module scope | Правильно | Набор feature и row model стабилен и минимален. |
| `useTable(..., state => ({ pagination: state.pagination }))` | Правильно | Ререндер нужен только при изменении пагинации; внешнее владение state не требуется. |
| `tableColumns` / `tableData` с spread-копированием | Заменить | Это лишняя O(n) копия и новый слой ссылок. Мемоизация лишь компенсирует копирование, но не делает нестабильный input вызывающего кода правильным. |
| `auditColumns` | Правильно | Константа на module scope. |
| `userColumns()` в render `UsersTableContent` | Заменить | При каждом рендере создаётся новый массив определений колонок. Сейчас внутренний `useMemo` уменьшает эффект, но источник нестабильности остаётся. |
| `users.items` / `audit.items` из TanStack Query | Допустимо | Результат запроса уже является стабильным между реальными обновлениями; не нужно его копировать. |

## Рекомендуемая реализация для текущей клиентской таблицы

1. В `DataTable` убрать импорт `useMemo`, `tableColumns` и `tableData`; передать `columns` и `data` непосредственно:

   ```tsx
   const table = useTable(
     {
       columns,
       data,
       features: dataTableFeatures,
       initialState: { pagination: { pageIndex: 0, pageSize: 5 } },
     },
     (state) => ({ pagination: state.pagination }),
   )
   ```

   `initialState` нужен только если 5 — требуемый размер первой страницы. Он
   задаёт начальное/обычное reset-состояние; для дальнейшего управления им не
   используют.

2. В `columns.tsx` экспортировать пользовательские колонки как константу
   module scope, например `export const userColumns = [...]`, поскольку они не
   зависят от props или локального state. В маршруте передавать
   `columns={userColumns}`, без вызова функции. Если колонки когда-нибудь будут
   зависеть от props, создавать их через `useMemo` в их владельце с точными
   зависимостями, а не копировать в `DataTable`.

3. Оставить pagination внутренней. Для простой клиентской таблицы нужно
   вызывать API feature (`nextPage`, `previousPage`, `firstPage`, `lastPage`,
   `setPageSize`), как делает текущий код. Внешние `state.pagination` и
   `onPaginationChange` не добавлять без потребителя состояния.

4. В render использовать один финальный row model:

   ```tsx
   const pageRows = table.getRowModel().rows
   ```

   По нему одновременно определять empty state и рисовать строки. Это убирает
   смешение `getRowModel()` и `getPaginatedRowModel()`; в данном feature-наборе
   `getRowModel()` — итоговый модельный pipeline, включая pagination.

5. Для текста счётчика брать `table.getRowCount()` и отдельно обработать
   пустой набор (`0–0 из 0`), а не вычислять нижнюю границу как `1` всегда.

## Политика reset страницы

Не следует добавлять `autoResetPageIndex: false` как обход проблемы. В v9 для
клиентской пагинации reset на реальную смену `data` включён по умолчанию; это
защищает от пустой страницы после удаления или фильтрации. Правильное правило
для этой таблицы: сохранять страницу при обычном рендере, сбрасывать её при
новом наборе данных. Для этого достаточно стабильных ссылок на input-массивы.

Если продукту всё же нужно удерживать страницу при обновлении данных, задать
`autoResetPageIndex: false` осознанно и дополнительно проверять, что текущий
`pageIndex` остаётся в диапазоне.

## Когда понадобится серверная пагинация

Текущие endpoint'ы передают весь список, поэтому нужна клиентская схема выше.
При переходе на страницы API следует заменить её, а не сочетать две нарезки:

- передавать в `data` **только** полученную страницу;
- установить `manualPagination: true` и передать общий `rowCount` (либо
  `pageCount`);
- владеть `pagination` снаружи (`state.pagination` +
  `onPaginationChange`) и включить её в ключ запроса;
- при серверной сортировке/фильтрации также включить `manualSorting` /
  `manualFiltering` и параметры в запрос. Флаги `manual*` не делают запросы
  сами — они только отключают соответствующую клиентскую обработку.

## Первичные источники

- [Data Guide: стабильные ссылки на `data` и `columns`](https://github.com/TanStack/table/blob/main/docs/guide/data.md#give-data-a-stable-reference).
- [Pagination Guide для React](https://github.com/TanStack/table/blob/main/docs/framework/react/guide/pagination.md) и [локальная инструкция именно для 9.1.2](../node_modules/.pnpm/@tanstack+table-core@9.1.2/node_modules/@tanstack/table-core/skills/pagination/SKILL.md).
- [Table State Guide для React](https://github.com/TanStack/table/blob/main/docs/framework/react/guide/table-state.md) и [локальная инструкция 9.1.2](../apps/frontend/node_modules/@tanstack/react-table/skills/table-state/SKILL.md).
- [Типы pagination установленной версии](../node_modules/.pnpm/@tanstack+table-core@9.1.2/node_modules/@tanstack/table-core/dist/features/row-pagination/rowPaginationFeature.types.d.ts) и [реализация reset/page navigation](../node_modules/.pnpm/@tanstack+table-core@9.1.2/node_modules/@tanstack/table-core/dist/features/row-pagination/rowPaginationFeature.utils.js).
- [Тип `data` и контракт смены ссылки](../node_modules/.pnpm/@tanstack+table-core@9.1.2/node_modules/@tanstack/table-core/dist/core/table/coreTablesFeature.types.d.ts).

Производственный код в рамках исследования не изменялся.
