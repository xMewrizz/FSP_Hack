# Сверка ответов Backend-заданий

Для 12 исходных вопросов и 24 вариантов сверены технические факты и ключи с указанными ниже источниками и условиями задач. Это не испытание сложности на кандидатах. Пробных прохождений пока не было. Отдельного Backend-рецензента в команде нет, поэтому независимую экспертную проверку не заявляем.

В столбце «Ключи» ответы идут в порядке: исходный вопрос / V2 / V3. Полный текст вопросов остаётся в [листе](09-question-review-sheet.md), а объяснения — в коде банка. Лист не нужно заполнять Тимофею или другим участникам, если тема им незнакома.

| Семья | Ключи | Основание проверки |
|---|---|---|
| BE-JR-01 | D / A / C | [Глоссарий PostgreSQL](https://www.postgresql.org/docs/current/glossary.html): сохранность после фиксации — долговечность; откат всей операции — атомарность; невидимость промежуточных изменений другой транзакции — изоляция. |
| BE-JR-02 | A / C / A | [Документация Python по сложности встроенных типов](https://docs.python.org/3.14/builtins/time-complexity.html): `list.append` — амортизированно O(1), поиск в `list` — O(n), в `set` — в среднем O(1). |
| BE-JR-03 | B / B / D | [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html): PUT заменяет ресурс и идемпотентен; POST подходит, когда сервер создаёт ресурс и назначает URI; DELETE запрашивает удаление ресурса. |
| BE-JR-04 | B / B / C | [Документация Git reset](https://git-scm.com/docs/git-reset): `--soft` сохраняет индекс; `--mixed` сбрасывает индекс, сохраняя рабочие файлы; `--hard` приводит отслеживаемые файлы к целевому коммиту. |
| BE-MID-01 | B / B / B | [Документация asyncio](https://docs.python.org/3/library/asyncio-task.html): `await asyncio.sleep` уступает управление; `asyncio.to_thread` выносит блокирующий вызов из потока event loop. Обычный `time.sleep` блокирует этот поток. В трёх вариантах одинаковая буква обозначает разные по смыслу варианты ответа. |
| BE-MID-02 | C / B / C | [Документация PostgreSQL по составным индексам](https://www.postgresql.org/docs/current/indexes-multicolumn.html): порядок ведущего поля указан верно. Существующий индекс `(city, age)` иногда может использоваться через skip scan; исходный вопрос корректно спрашивает о дополнительном индексе, прямо соответствующем фильтру. |
| BE-MID-03 | A / A / C | Следует из прямо заданного условия об идеальной блокировке на каждый ключ: для одного, двух и четырёх отсутствующих ключей требуется соответственно одна, две и четыре загрузки. Число ожидающих запросов не увеличивает число загрузок. |
| BE-MID-04 | C / A / B | [Документация SQLAlchemy Session](https://docs.sqlalchemy.org/en/20/orm/session_basics.html): `rollback` откатывает текущую транзакцию, `flush` отправляет ожидающие SQL-изменения без фиксации, `commit` сначала делает flush при необходимости и фиксирует транзакцию. |
| BE-SR-01 | C / B / C | [Документация Stripe об идемпотентных запросах](https://docs.stripe.com/api/idempotent_requests) подтверждает повтор сохранённого результата и конфликт при изменении параметров. В исходном вопросе ключ и перевод откатились до сохранения, поэтому сохранённого результата нет; его ответ следует из явно заданного атомарного сохранения ключа и результата. Это проверка описанного контракта, а не универсального поведения любого платёжного API. |
| BE-SR-02 | C / A / C | [Материалы MIT по согласованному хешированию](https://courses.csail.mit.edu/6.856/current/Notes/n10-hashing-advanced.html): при случайном расположении узлов ожидаемая доля нового узла после добавления к N существующим равна 1/(N+1). Для N = 5, 3, 4 это 1/6, 1/4, 1/5. |
| BE-SR-03 | B / A / C | [Описание circuit breaker Мартина Фаулера](https://martinfowler.com/bliki/CircuitBreaker.html) подтверждает Closed, Open и Half-open. Конкретный порог и события заданы внутри вопросов: три ошибки подряд открывают цепь; успех сбрасывает счётчик; после паузы до пробного вызова состояние Half-open. |
| BE-SR-04 | C / A / C | [Описание transactional outbox от AWS](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html): откат общей транзакции отменяет обе записи; сохранённое событие можно доставить позже; повторная отправка возможна, поэтому получатель должен распознавать дубликат. |

В этих 36 вариантах не обнаружено расхождения между ключом и указанным источником либо условиями задачи. Позже банк расширили; состав описан в [банке](07-question-bank.md). Число заданий само по себе не доказывает, что варианты одинаково сложны или определяют квалификацию: это проверяется в B-19. Если обнаружится неоднозначный вопрос, его исключаем из подсчёта до исправления.

## Добавленные задания

Для новых семей ниже проверены формулировки, смысл правильного варианта и соответствие ключа после перестановки вариантов ответа. В каждой строке ключи идут для V1 / V2 / V3. Проверка выполнена по указанным источникам и условиям задач; независимого Backend-рецензента по-прежнему нет.

| Семья | Ключи | Основание |
|---|---|---|
| BE-JR-05 | B / A / D | [Агрегатные функции PostgreSQL](https://www.postgresql.org/docs/16/functions-aggregate.html): `COUNT(DISTINCT user_id)` считает уникальные ненулевые значения. |
| BE-JR-06 | A / D / C | [Транзакции PostgreSQL](https://www.postgresql.org/docs/current/tutorial-transactions.html): COMMIT фиксирует, ROLLBACK отменяет изменения. |
| BE-JR-07 | C / B / A | [Коллекции Python](https://docs.python.org/3.12/tutorial/datastructures.html): `list.sort()` меняет список на месте и возвращает `None`; `sorted()` создаёт новый список. |
| BE-JR-08 | B / A / D | [Копирование в Python](https://docs.python.org/3/library/copy.html): присваивание сохраняет ссылку, `copy()` и полный срез создают новый внешний список. |
| BE-JR-09 | D / C / B | [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html): 201 — создание, 204 — успешный ответ без тела, 404 — ресурс не найден. |
| BE-JR-10 | B / A / D | [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html): GET запрашивает представление, HEAD — его метаданные без тела, OPTIONS — сведения о возможностях ресурса. |
| BE-JR-11 | B / A / D | [Git commit](https://git-scm.com/docs/git-commit): рабочее дерево, индекс и новый коммит — разные состояния. |
| BE-JR-12 | B / A / D | [Git restore](https://git-scm.com/docs/git-restore) и [Git revert](https://git-scm.com/docs/git-revert.html): убрать staged, вернуть рабочий файл, отменить опубликованный коммит новым. |
| BE-MID-05 | C / B / A | [asyncio.gather](https://docs.python.org/3/library/asyncio-task.html): порядок результатов соответствует аргументам, а не времени завершения. |
| BE-MID-06 | A / D / C | [asyncio.Queue](https://docs.python.org/3.12/library/asyncio-queue.html): `join()` ждёт соответствующего числа вызовов `task_done()`. |
| BE-MID-07 | A / D / C | [Частичные индексы PostgreSQL](https://www.postgresql.org/docs/current/indexes-partial.html): в индекс входят строки, удовлетворяющие предикату. |
| BE-MID-08 | A / D / C | [EXPLAIN PostgreSQL](https://www.postgresql.org/docs/current/using-explain.html): Seq Scan может быть подходящим планом; фактическое время смотрят через EXPLAIN ANALYZE. |
| BE-MID-09 | C / B / A | [Cache-aside Redis](https://redis.io/docs/latest/develop/use-cases/cache-aside/php/): после изменения источника старое значение кэша нужно удалить или обновить. |
| BE-MID-10 | A / D / C | [Ключи Redis](https://redis.io/docs/latest/develop/use/keyspace/): разные представления должны иметь разные ключи; проверка доступа остаётся отдельной. |
| BE-MID-11 | C / B / A | [SQLAlchemy Session](https://docs.sqlalchemy.org/en/20/orm/session_basics.html): различие flush, commit и rollback. |
| BE-MID-12 | C / B / A | [SQLAlchemy Session](https://docs.sqlalchemy.org/en/20/orm/session_basics.html): после ошибки flush для повторного использования Session нужен явный rollback. |
| BE-SR-05 | B / A / D | В условиях перевод и ключ находятся в одной БД; атомарная фиксация нужна, чтобы повтор на другом экземпляре не списал деньги снова. [Пример контракта идемпотентности](https://docs.stripe.com/api/idempotent_requests). |
| BE-SR-06 | D / C / B | [Контракт идемпотентных запросов Stripe](https://docs.stripe.com/api/idempotent_requests): точный повтор получает прежний результат, изменение параметров при том же ключе — конфликт. |
| BE-SR-07 | D / C / B | [AWS об ограничении нагрузки](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_mitigate_interaction_failure_throttle_requests.html): явный предел помогает не накапливать бесконечную очередь при перегрузке. |
| BE-SR-08 | B / A / D | [Описание виртуальных узлов Redis](https://redis.io/blog/cache-layer-architecture-guide/): несколько позиций физического узла помогают распределять доли ровнее. |
| BE-SR-09 | D / C / B | [Circuit breaker](https://martinfowler.com/bliki/CircuitBreaker.html): переход после пробного вызова задан прямо в каждом условии. |
| BE-SR-10 | B / A / D | [Bulkhead pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/bulkhead): раздельные ресурсы ограничивают распространение отказа. |
| BE-SR-11 | B / A / D | [Transactional outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html): возможны дубликаты, получателю нужна идемпотентная обработка. |
| BE-SR-12 | D / C / B | [Transactional outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html): заказ и запись события фиксируются или откатываются вместе. |

Ключи и технические факты проверены для прежних 108 вариантов. Ещё 36 вариантов добавлены под постоянный набор обязательных навыков; их ключи связаны с вариантами автоматическими тестами, но условия пока не проверены независимым специалистом. После этого подготовлены ещё 84 самостоятельных вопроса с тремя вариантами каждый. Для них [собраны ссылки на первоисточники](13-backend-question-sources.md); независимой технической проверки пока нет. Сходство сложности внутри семьи и пригодность порога для грейда остаются предметом B-19.
