# Источники новых Backend-заданий

Здесь перечислены источники для 12 ранее добавленных вопросов и 84 новых вопросов базового набора. Три версии одного кода проверяют одно правило и не считаются тремя самостоятельными вопросами. Формулировки написаны для проекта, тексты источников не копировались.

Ссылки помогают проверить технический факт и ключ. Они не доказывают, что вопрос подходит заявленному грейду, что варианты одинаково сложны или что тест определяет квалификацию. Для этого нужен разбор с Backend-специалистом и пробные прохождения. Кандидату этот файл и ключи до завершения теста не показывать.

| Код | Навык | Проверяемое правило | Ключи V1 / V2 / V3 | Источник |
|---|---|---|---|---|
| BE-JR-13 | Надёжность сервиса | Таймаут внешнего вызова | C / B / A | [Документация](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_limit_retries.html) |
| BE-JR-14 | Надёжность сервиса | Безопасный повтор операции | B / A / D | [Документация](https://www.rfc-editor.org/rfc/rfc9110.html) |
| BE-JR-15 | Надёжность сервиса | Готовность принимать трафик | C / B / A | [Документация](https://kubernetes.io/docs/concepts/workloads/pods/probes/) |
| BE-MID-13 | HTTP API и интеграция | Условное обновление ресурса | C / B / A | [Документация](https://www.rfc-editor.org/rfc/rfc9110.html) |
| BE-MID-14 | HTTP API и интеграция | Пагинация изменяющегося списка | D / C / B | [Документация](https://learn.microsoft.com/en-us/azure/data-api-builder/keywords/after-rest) |
| BE-MID-15 | HTTP API и интеграция | Контракт временного ограничения | A / D / C | [Документация](https://www.rfc-editor.org/rfc/rfc6585.html) |
| BE-SR-13 | Python | Отказ в группе асинхронных задач | D / C / B | [Документация](https://docs.python.org/3.12/library/asyncio-task.html) |
| BE-SR-14 | Python | Таймаут асинхронной операции | B / A / D | [Документация](https://docs.python.org/3.12/library/asyncio-task.html) |
| BE-SR-15 | Python | Освобождение ресурса при отмене | D / C / B | [Документация](https://docs.python.org/3.12/library/asyncio-task.html) |
| BE-SR-16 | SQL и работа с данными | Повтор сериализуемой транзакции | B / A / D | [Документация](https://www.postgresql.org/docs/16/transaction-iso.html) |
| BE-SR-17 | SQL и работа с данными | Согласованный снимок отчёта | B / A / D | [Документация](https://www.postgresql.org/docs/16/transaction-iso.html) |
| BE-SR-18 | SQL и работа с данными | Блокировка строки перед изменением | C / B / A | [Документация](https://www.postgresql.org/docs/16/explicit-locking.html) |
| BE-JR-16 | Python для Backend | Отсутствующий ключ словаря | B / A / D | [Документация](https://docs.python.org/3.12/tutorial/datastructures.html) |
| BE-JR-17 | Python для Backend | Изменяемый аргумент по умолчанию | A / D / C | [Документация](https://docs.python.org/3.12/tutorial/controlflow.html) |
| BE-JR-18 | Python для Backend | Потоковая обработка | A / D / C | [Документация](https://docs.python.org/3.12/library/itertools.html) |
| BE-JR-19 | Python для Backend | Закрытие файла | D / C / B | [Документация](https://docs.python.org/3.12/library/contextlib.html) |
| BE-JR-20 | Python для Backend | Обработка конкретной ошибки | D / C / B | [Документация](https://docs.python.org/3.12/tutorial/errors.html) |
| BE-JR-21 | Python для Backend | Удаление дублей | C / B / A | [Документация](https://docs.python.org/3.12/tutorial/datastructures.html) |
| BE-JR-22 | Python для Backend | Копирование вложенных данных | C / B / A | [Документация](https://docs.python.org/3.12/library/copy.html) |
| BE-JR-23 | SQL и работа с данными | Проверка NULL | C / B / A | [Документация](https://www.postgresql.org/docs/16/functions-comparison.html) |
| BE-JR-24 | SQL и работа с данными | Соединение с необязательной записью | C / B / A | [Документация](https://www.postgresql.org/docs/16/queries.html) |
| BE-JR-25 | SQL и работа с данными | Фильтр агрегатов | D / C / B | [Документация](https://www.postgresql.org/docs/16/queries.html) |
| BE-JR-26 | SQL и работа с данными | Уникальность данных | B / A / D | [Документация](https://www.postgresql.org/docs/16/ddl-constraints.html) |
| BE-JR-27 | SQL и работа с данными | Ссылочная целостность | C / B / A | [Документация](https://www.postgresql.org/docs/16/ddl-constraints.html) |
| BE-JR-28 | SQL и работа с данными | Порядок и ограничение выдачи | C / B / A | [Документация](https://www.postgresql.org/docs/16/queries.html) |
| BE-JR-29 | SQL и работа с данными | Условие в UPDATE | A / D / C | [Документация](https://www.postgresql.org/docs/16/sql-update.html) |
| BE-JR-30 | HTTP API и интеграция | Ошибка входных данных | A / D / C | [Документация](https://www.rfc-editor.org/rfc/rfc9110.html) |
| BE-JR-31 | HTTP API и интеграция | Отсутствие аутентификации | C / B / A | [Документация](https://www.rfc-editor.org/rfc/rfc9110.html) |
| BE-JR-32 | HTTP API и интеграция | Недостаточно прав | B / A / D | [Документация](https://www.rfc-editor.org/rfc/rfc9110.html) |
| BE-JR-33 | HTTP API и интеграция | Конфликт состояния | A / D / C | [Документация](https://www.rfc-editor.org/rfc/rfc9110.html) |
| BE-JR-34 | HTTP API и интеграция | Тип тела запроса | C / B / A | [Документация](https://www.rfc-editor.org/rfc/rfc9110.html) |
| BE-JR-35 | HTTP API и интеграция | Параметр ресурса | B / A / D | [Документация](https://learn.microsoft.com/en-us/azure/architecture/microservices/design/api-design) |
| BE-JR-36 | HTTP API и интеграция | Безопасность GET | B / A / D | [Документация](https://www.rfc-editor.org/rfc/rfc9110.html) |
| BE-JR-37 | Надёжность сервиса | Диагностика ошибки | A / D / C | [Документация](https://sre.google/sre-book/monitoring-distributed-systems/) |
| BE-JR-38 | Надёжность сервиса | Проверка жизнеспособности | A / D / C | [Документация](https://kubernetes.io/docs/concepts/workloads/pods/probes/) |
| BE-JR-39 | Надёжность сервиса | Ограничение одновременной работы | A / D / C | [Документация](https://sre.google/sre-book/handling-overload/) |
| BE-JR-40 | Надёжность сервиса | Пауза между повторами | A / D / C | [Документация](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_limit_retries.html) |
| BE-JR-41 | Надёжность сервиса | Повтор записи | A / D / C | [Документация](https://www.rfc-editor.org/rfc/rfc9110.html) |
| BE-JR-42 | Надёжность сервиса | Сохранность задания в очереди | C / B / A | [Документация](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues-at-least-once-delivery.html) |
| BE-JR-43 | Надёжность сервиса | Наблюдение за ошибками | C / B / A | [Документация](https://sre.google/sre-book/monitoring-distributed-systems/) |
| BE-MID-16 | Python для Backend | Отмена задачи asyncio | A / D / C | [Документация](https://docs.python.org/3.12/library/asyncio-task.html) |
| BE-MID-17 | Python для Backend | Группа задач | C / B / A | [Документация](https://docs.python.org/3.12/library/asyncio-task.html) |
| BE-MID-18 | Python для Backend | Обработка по готовности | C / B / A | [Документация](https://docs.python.org/3.12/library/asyncio-task.html) |
| BE-MID-19 | Python для Backend | Ограниченная очередь | A / D / C | [Документация](https://docs.python.org/3.12/library/asyncio-queue.html) |
| BE-MID-20 | Python для Backend | Таймаут корутины | A / D / C | [Документация](https://docs.python.org/3.12/library/asyncio-task.html) |
| BE-MID-21 | Python для Backend | Контекст запроса | A / D / C | [Документация](https://docs.python.org/3.12/library/contextvars.html) |
| BE-MID-22 | Python для Backend | Поток результатов | C / B / A | [Документация](https://docs.python.org/3.12/library/itertools.html) |
| BE-MID-23 | SQL и работа с данными | Видимость при Read Committed | C / B / A | [Документация](https://www.postgresql.org/docs/16/transaction-iso.html) |
| BE-MID-24 | SQL и работа с данными | Блокировка строки | C / B / A | [Документация](https://www.postgresql.org/docs/16/explicit-locking.html) |
| BE-MID-25 | SQL и работа с данными | Вставка при конфликте | A / D / C | [Документация](https://www.postgresql.org/docs/16/sql-insert.html) |
| BE-MID-26 | SQL и работа с данными | Индекс под фильтр | B / A / D | [Документация](https://www.postgresql.org/docs/16/indexes.html) |
| BE-MID-27 | SQL и работа с данными | NULL в ограничении UNIQUE | A / D / C | [Документация](https://www.postgresql.org/docs/16/ddl-constraints.html) |
| BE-MID-28 | SQL и работа с данными | Устойчивая пагинация | A / D / C | [Документация](https://www.postgresql.org/docs/16/queries.html) |
| BE-MID-29 | SQL и работа с данными | N+1 запросов | A / D / C | [Документация](https://docs.sqlalchemy.org/en/20/tutorial/orm_related_objects.html) |
| BE-MID-30 | HTTP API и интеграция | Проверка версии при чтении | B / A / D | [Документация](https://www.rfc-editor.org/rfc/rfc9110.html) |
| BE-MID-31 | HTTP API и интеграция | Частичное изменение | D / C / B | [Документация](https://www.rfc-editor.org/rfc/rfc5789.html) |
| BE-MID-32 | HTTP API и интеграция | Ключ повтора записи | C / B / A | [Документация](https://docs.stripe.com/api/idempotent_requests) |
| BE-MID-33 | HTTP API и интеграция | Переговоры о формате ответа | D / C / B | [Документация](https://www.rfc-editor.org/rfc/rfc9110.html) |
| BE-MID-34 | HTTP API и интеграция | Формат ошибки | B / A / D | [Документация](https://www.rfc-editor.org/rfc/rfc9457.html) |
| BE-MID-35 | HTTP API и интеграция | Временная недоступность | B / A / D | [Документация](https://www.rfc-editor.org/rfc/rfc9110.html) |
| BE-MID-36 | HTTP API и интеграция | Личный ответ и общий кэш | C / B / A | [Документация](https://www.rfc-editor.org/rfc/rfc9111.html) |
| BE-MID-37 | Надёжность сервиса | Бюджет повторов | C / B / A | [Документация](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_limit_retries.html) |
| BE-MID-38 | Надёжность сервиса | Предохранитель зависимости | C / B / A | [Документация](https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker) |
| BE-MID-39 | Надёжность сервиса | Изоляция ресурсов | B / A / D | [Документация](https://learn.microsoft.com/en-us/azure/architecture/patterns/bulkhead) |
| BE-MID-40 | Надёжность сервиса | Алерт по пользовательскому эффекту | A / D / C | [Документация](https://sre.google/workbook/alerting-on-slos/) |
| BE-MID-41 | Надёжность сервиса | Завершение при остановке | C / B / A | [Документация](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/) |
| BE-MID-42 | Надёжность сервиса | Повторная доставка | D / C / B | [Документация](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues-at-least-once-delivery.html) |
| BE-MID-43 | Надёжность сервиса | Сообщение с постоянной ошибкой | C / B / A | [Документация](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html) |
| BE-SR-19 | Python для Backend | Независимые результаты при ошибке | A / D / C | [Документация](https://docs.python.org/3.12/library/asyncio-task.html) |
| BE-SR-20 | Python для Backend | Защита отдельной операции от отмены | D / C / B | [Документация](https://docs.python.org/3.12/library/asyncio-task.html) |
| BE-SR-21 | Python для Backend | CPU задача и GIL | B / A / D | [Документация](https://docs.python.org/3.12/library/concurrent.futures.html) |
| BE-SR-22 | Python для Backend | Ограничение параллелизма | C / B / A | [Документация](https://docs.python.org/3.12/library/asyncio-task.html) |
| BE-SR-23 | Python для Backend | Потоковая выгрузка | C / B / A | [Документация](https://docs.python.org/3.12/library/itertools.html) |
| BE-SR-24 | Python для Backend | Атомарная замена файла | A / D / C | [Документация](https://docs.python.org/3.12/library/os.html) |
| BE-SR-25 | Python для Backend | Контекст между задачами | D / C / B | [Документация](https://docs.python.org/3.12/library/contextvars.html) |
| BE-SR-26 | SQL и работа с данными | Аномалия write skew | B / A / D | [Документация](https://www.postgresql.org/docs/16/transaction-iso.html) |
| BE-SR-27 | SQL и работа с данными | Порядок захвата блокировок | A / D / C | [Документация](https://www.postgresql.org/docs/16/explicit-locking.html) |
| BE-SR-28 | SQL и работа с данными | Индекс без долгой блокировки записи | B / A / D | [Документация](https://www.postgresql.org/docs/16/sql-createindex.html) |
| BE-SR-29 | SQL и работа с данными | Частичный индекс | C / B / A | [Документация](https://www.postgresql.org/docs/16/indexes-partial.html) |
| BE-SR-30 | SQL и работа с данными | План при неравномерных данных | C / B / A | [Документация](https://www.postgresql.org/docs/16/using-explain.html) |
| BE-SR-31 | SQL и работа с данными | Потерянное обновление | D / C / B | [Документация](https://www.postgresql.org/docs/16/transaction-iso.html) |
| BE-SR-32 | SQL и работа с данными | Разделы большой таблицы | D / C / B | [Документация](https://www.postgresql.org/docs/16/ddl-partitioning.html) |
| BE-SR-33 | HTTP API и интеграция | Отложенная операция | D / C / B | [Документация](https://www.rfc-editor.org/rfc/rfc9110.html) |
| BE-SR-34 | HTTP API и интеграция | Предусловие записи | A / D / C | [Документация](https://www.rfc-editor.org/rfc/rfc6585.html) |
| BE-SR-35 | HTTP API и интеграция | Условный GET и запись | D / C / B | [Документация](https://www.rfc-editor.org/rfc/rfc9110.html) |
| BE-SR-36 | HTTP API и интеграция | Совместимость API | A / D / C | [Документация](https://learn.microsoft.com/en-us/azure/architecture/microservices/design/api-design) |
| BE-SR-37 | HTTP API и интеграция | Ошибка без утечки деталей | A / D / C | [Документация](https://www.rfc-editor.org/rfc/rfc9457.html) |
| BE-SR-38 | HTTP API и интеграция | Ограничение тяжёлого запроса | B / A / D | [Документация](https://www.rfc-editor.org/rfc/rfc6585.html) |
| BE-SR-39 | HTTP API и интеграция | Снимок длинной выдачи | C / B / A | [Документация](https://www.postgresql.org/docs/16/transaction-iso.html) |
| BE-SR-40 | Надёжность сервиса | Бюджет ошибок | A / D / C | [Документация](https://sre.google/workbook/implementing-slos/) |
| BE-SR-41 | Надёжность сервиса | Шторм повторов | D / C / B | [Документация](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_limit_retries.html) |
| BE-SR-42 | Надёжность сервиса | Частичный отказ | D / C / B | [Документация](https://learn.microsoft.com/en-us/azure/architecture/patterns/bulkhead) |
| BE-SR-43 | Надёжность сервиса | Порядок событий outbox | A / D / C | [Документация](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) |
| BE-SR-44 | Надёжность сервиса | Восстановление и потеря данных | B / A / D | [Документация](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/plan-for-disaster-recovery-dr.html) |
| BE-SR-45 | Надёжность сервиса | Отказ при перегрузке | C / B / A | [Документация](https://sre.google/sre-book/handling-overload/) |
| BE-SR-46 | Надёжность сервиса | Сигнал об инциденте | D / C / B | [Документация](https://sre.google/workbook/alerting-on-slos/) |
