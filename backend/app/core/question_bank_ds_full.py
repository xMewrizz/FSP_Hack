"""Additional independent Data Science question families for six skills.

Each row tests one decision.  The three prepared wordings use different work
contexts but keep the same rule and answer.  A wording is not a new family.
"""

from typing import Any


SOURCES = {
    "python-tutorial": "https://docs.python.org/3/tutorial/datastructures.html",
    "python-generators": "https://docs.python.org/3/howto/functional.html#generators",
    "python-io": "https://docs.python.org/3/tutorial/inputoutput.html",
    "python-pickle": "https://docs.python.org/3/library/pickle.html",
    "python-processes": "https://docs.python.org/3/library/multiprocessing.html",
    "python-decimal": "https://docs.python.org/3/library/decimal.html",
    "python-exceptions": "https://docs.python.org/3/tutorial/errors.html",
    "python-queue": "https://docs.python.org/3/library/queue.html",
    "python-random": "https://docs.python.org/3/library/random.html",
    "pandas-missing": "https://pandas.pydata.org/docs/user_guide/missing_data.html",
    "pandas-merge": "https://pandas.pydata.org/docs/user_guide/merging.html",
    "pandas-groupby": "https://pandas.pydata.org/docs/user_guide/groupby.html",
    "pandas-index": "https://pandas.pydata.org/docs/user_guide/indexing.html",
    "pandas-timeseries": "https://pandas.pydata.org/docs/user_guide/timeseries.html",
    "pandas-duplicates": "https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.drop_duplicates.html",
    "pandas-io": "https://pandas.pydata.org/docs/user_guide/io.html",
    "pandas-integer": "https://pandas.pydata.org/docs/user_guide/integer_na.html",
    "numpy-broadcast": "https://numpy.org/doc/stable/user/basics.broadcasting.html",
    "numpy-copies": "https://numpy.org/doc/stable/user/basics.copies.html",
    "numpy-sum": "https://numpy.org/doc/stable/reference/generated/numpy.sum.html",
    "pg-aggregate": "https://www.postgresql.org/docs/16/functions-aggregate.html",
    "pg-join": "https://www.postgresql.org/docs/16/queries-table-expressions.html",
    "pg-select": "https://www.postgresql.org/docs/16/sql-select.html",
    "pg-conditional": "https://www.postgresql.org/docs/16/functions-conditional.html",
    "pg-explain": "https://www.postgresql.org/docs/16/using-explain.html",
    "pg-index": "https://www.postgresql.org/docs/16/indexes.html",
    "pg-partial": "https://www.postgresql.org/docs/16/indexes-partial.html",
    "pg-partition": "https://www.postgresql.org/docs/16/ddl-partitioning.html",
    "pg-isolation": "https://www.postgresql.org/docs/16/transaction-iso.html",
    "pg-matview": "https://www.postgresql.org/docs/16/rules-materializedviews.html",
    "pg-index-only": "https://www.postgresql.org/docs/16/indexes-index-only-scans.html",
    "pg-upsert": "https://www.postgresql.org/docs/16/sql-insert.html",
    "stats-scipy": "https://docs.scipy.org/doc/scipy/reference/stats.html",
    "stats-bootstrap": "https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html",
    "stats-ttest": "https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.ttest_ind.html",
    "stats-multiple": "https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html",
    "stats-experiments": "https://exp-platform.com/survey/",
    "stats-cuped": "https://exp-platform.com/Documents/2013-02-CUPED-ImprovingSensitivityOfControlledExperiments.pdf",
    "sklearn-split": "https://scikit-learn.org/stable/modules/cross_validation.html",
    "sklearn-metrics": "https://scikit-learn.org/stable/modules/model_evaluation.html",
    "sklearn-pitfalls": "https://scikit-learn.org/stable/common_pitfalls.html",
    "sklearn-preprocess": "https://scikit-learn.org/stable/modules/preprocessing.html",
    "sklearn-pipeline": "https://scikit-learn.org/stable/modules/compose.html",
    "sklearn-calibration": "https://scikit-learn.org/stable/modules/calibration.html",
    "sklearn-importance": "https://scikit-learn.org/stable/modules/permutation_importance.html",
    "sklearn-threshold": "https://scikit-learn.org/stable/modules/classification_threshold.html",
    "sklearn-hyperparams": "https://scikit-learn.org/stable/modules/grid_search.html",
    "sklearn-drift": "https://scikit-learn.org/stable/common_pitfalls.html#data-leakage",
    "sklearn-target-encoder": "https://scikit-learn.org/stable/auto_examples/preprocessing/plot_target_encoder_cross_val.html",
}

# title, source, question, correct answer, three plausible alternatives, explanation.
Row = tuple[str, str, str, str, str, str, str, str]

CONTEXTS = {
    "ds_python": ("обработка заказов", "обработка событий", "обработка профилей"),
    "ds_pandas": ("витрина заказов", "журнал событий", "таблица клиентов"),
    "ds_sql": ("витрина продаж", "журнал транзакций", "таблица пользователей"),
    "ds_statistics": ("исследование конверсии", "исследование времени ответа", "исследование удержания"),
    "ds_ab": ("эксперимент с поиском", "эксперимент с оплатой", "эксперимент с регистрацией"),
    "ds_ml": ("модель оттока", "модель отказов", "модель риска"),
}

TOTAL_PER_SKILL = {"ds_python": 10, "ds_pandas": 10, "ds_sql": 10, "ds_statistics": 10, "ds_ab": 10, "ds_ml": 10}
EXISTING_PER_GRADE = {
    "junior": {"ds_pandas": 1, "ds_sql": 1, "ds_statistics": 1, "ds_ml": 1},
    "middle": {"ds_pandas": 1, "ds_sql": 1, "ds_ab": 1, "ds_ml": 1},
    "senior": {"ds_sql": 1, "ds_ab": 1, "ds_ml": 1},
}


def _rows(grade: str, blocks: dict[str, list[Row]]) -> list[tuple[Any, ...]]:
    result = []
    grade_tag = {"junior": "JR", "middle": "MID", "senior": "SR"}[grade]
    next_number = 5
    if set(blocks) != set(TOTAL_PER_SKILL):
        raise ValueError(f"Incomplete Data Science blocks for {grade}")
    for skill_code, items in blocks.items():
        expected = TOTAL_PER_SKILL[skill_code] - EXISTING_PER_GRADE[grade].get(skill_code, 0)
        if len(items) != expected:
            raise ValueError(f"Expected {expected} new questions for {grade}/{skill_code}, got {len(items)}")
        for item_index, (title, source, question, correct, wrong1, wrong2, wrong3, explanation) in enumerate(items):
            code = f"DS-{grade_tag}-{next_number + item_index:02d}"
            prompts = tuple(
                f"Данные: {context}. {question}" for context in CONTEXTS[skill_code]
            )
            result.append((
                code, skill_code, title, source,
                (correct, wrong1, wrong2, wrong3), prompts, explanation,
            ))
        next_number += len(items)
    return result


from app.core.question_bank_ds_junior import JUNIOR
from app.core.question_bank_ds_middle import MIDDLE
from app.core.question_bank_ds_senior import SENIOR


def expanded_rows() -> list[tuple[Any, ...]]:
    return _rows("junior", JUNIOR) + _rows("middle", MIDDLE) + _rows("senior", SENIOR)
