# Банк заданий по Data Science (B-02)

Документ описывает структуру, темы, критерии оценки и авторитетные источники для банка тестовых заданий по направлению **Data Science**.

Банк заданий структурирован по трем уровням квалификации (Junior, Middle, Senior) и покрывает четыре ключевые компетенции, необходимые для работы с данными в продакшене.

---

## 1. Компетенции и матрица покрытия

| Компетенция | Код темы | Junior | Middle | Senior |
|---|---|---|---|---|
| **Python & Data Processing (NumPy, Pandas)** | `ds_python_pandas` | `DS-JR-01`: Векторизация vs `iterrows` | `DS-MID-01`: Категориальный тип (`category`) и оптимизация RAM | `DS-SR-01`: NumPy Strides, Views vs Copies, C-contiguous layout |
| **SQL & Data Analytics (PostgreSQL)** | `ds_sql_analytics` | `DS-JR-02`: Оконные функции ранжирования (`DENSE_RANK`) | `DS-MID-02`: Многомерная агрегация с `GROUPING SETS` | `DS-SR-02`: Оконные фреймы `ROWS` vs `RANGE` и `WindowAgg` |
| **Статистика и A/B тестирование** | `ds_stats_ab` | `DS-JR-03`: Ошибки I и II рода ($\alpha$, $\beta$) | `DS-MID-03`: Диагностика Sample Ratio Mismatch (SRM) | `DS-SR-03`: Снижение дисперсии метрик методом CUPED |
| **Машинное обучение и валидация** | `ds_ml_modeling` | `DS-JR-04`: Предотвращение Data Leakage при масштабировании | `DS-MID-04`: PR-AUC vs ROC-AUC при сильном дисбалансе | `DS-SR-04`: Калибровка вероятностей (Platt/Isotonic) и Brier Score |

Каждая семья заданий включает 3 варианта с различными практическими сценариями и параметрами, обеспечивая защиту от прямого заучивания при повторных попытках тестирования (всего 36 подготовленных вопросов).

---

## 2. Авторитетные источники для проверки ключей

Формулировки и правильные ответы сверены со следующей официальной технической документацией и научной литературой:

1. **Pandas (Vectorization & Performance)**:
   - Ссылка: https://pandas.pydata.org/docs/user_guide/enhancingperf.html
   - Правило: Векторизованные операции над `Series` выполняются скомпилированным C/Cython кодом без создания питоновских объектов на каждую строку таблицы.
2. **Pandas (Categorical Data)**:
   - Ссылка: https://pandas.pydata.org/docs/user_guide/categorical.html
   - Правило: `astype('category')` заменяет повторяющиеся строки целочисленными кодами (`codes`) и словарем уникальных категорий, радикально снижая потребление RAM и ускоряя операции сравнения/группировки.
3. **NumPy (Copies vs Views)**:
   - Ссылка: https://numpy.org/doc/stable/user/basics.copies.and.views.html
   - Правило: Базовые срезы (`arr[::2, :]`) создают легковесные представления (`view`) с измененными шагами смещения (`strides`), а индексные массивы и маски (`fancy indexing`) требуют аллокации нового непрерывного буфера памяти.
4. **PostgreSQL (Window Functions & Frames)**:
   - Ссылка: https://www.postgresql.org/docs/16/tutorial-window.html
   - Ссылка: https://www.postgresql.org/docs/16/sql-expressions.html#SYNTAX-WINDOW-FUNCTIONS
   - Правило: `DENSE_RANK()` не оставляет пропусков в рангах. Дефолтный фрейм `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` заставляет узел `WindowAgg` буферизовать все строки с одинаковым значением ключа сортировки; явный `ROWS` обрабатывает строки потоково.
5. **PostgreSQL (GROUPING SETS, CUBE, ROLLUP)**:
   - Ссылка: https://www.postgresql.org/docs/16/queries-table-expressions.html#QUERIES-GROUPING-SETS
   - Правило: `GROUPING SETS` позволяет рассчитать агрегаты нескольких измерений за один проход сканирования таблицы facts без тяжелых соединений `UNION ALL`.
6. **SciPy Stats (Hypothesis Testing Errors)**:
   - Ссылка: https://docs.scipy.org/doc/scipy/reference/stats.html
   - Правило: Ошибка I рода ($\alpha$) — отклонение истинной нулевой гипотезы $H_0$; ошибка II рода ($\beta$) — принятие ложной нулевой гипотезы.
7. **Kohavi et al. (A/B Testing, SRM Diagnostics)**:
   - Ссылка: https://exp-platform.com/survey/
   - Правило: Проверка Sample Ratio Mismatch (критерием согласия $\chi^2$) обязательна перед анализом любых эффектов: нарушение долей свидетельствует о сбоях сплиттера или смещенной фильтрации трафика.
8. **Deng, Xu, Kohavi, Walker (CUPED Variance Reduction)**:
   - Ссылка: https://exp-platform.com/Documents/2013-02-CUPED-ImprovingSensitivityOfControlledExperiments.pdf
   - Правило: CUPED использует предэкспериментальную ковариату $X$, независимую от экспериментального воздействия, снижая дисперсию на коэффициент $(1 - \rho^2)$.
9. **Scikit-Learn (Data Leakage & Pipelines)**:
   - Ссылка: https://scikit-learn.org/stable/common_pitfalls.html#data-leakage
   - Правило: `StandardScaler.fit()` вызывается строго на обучающем фолде; применение `fit` ко всей выборке искажает валидацию из-за утечки глобального математического ожидания и дисперсии.
10. **Scikit-Learn (Precision-Recall AUC vs ROC-AUC)**:
    - Ссылка: https://scikit-learn.org/stable/modules/model_evaluation.html#precision-recall-f-measure-metrics
    - Правило: При сильном дисбалансе классов преобладание True Negatives занижает FPR в ROC-кривой; PR-AUC адекватно отражает компромисс между точностью и полнотой редкого класса.
11. **Scikit-Learn (Probability Calibration & Brier Score)**:
    - Ссылка: https://scikit-learn.org/stable/modules/calibration.html
    - Правило: Калибровка (Platt scaling или Isotonic regression) согласует скоры моделей (GBDT, SVM) с реальными апостериорными вероятностями, что необходимо для задач с явной матрицей стоимостей и оценивается с помощью Brier Score.

---

## 3. Принципы формулирования дистракторов

Все варианты ответов соответствуют строгим критериям:
- Отсутствие карикатурных или заведомо абсурдных вариантов.
- Ошибочные ответы представляют собой распространенные заблуждения кандидатов (например, предположение, что `ROC-AUC` всегда универсален, или смешивание `fit_transform` на всем наборе данных).
- Дистракторы технически правдоподобны и заставляют кандидата демонстрировать глубокое понимание устройства алгоритмов и архитектуры систем.
