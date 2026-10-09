"""Статический анализатор безопасности кода (AST Security Inspector) для Task B-25.

Предотвращает запуск вредоносного или деструктивного кода до создания процессов.
Блокирует доступ к файловой системе, сокетам, процессам, рефлексии и побегам из песочницы.
"""

import ast
from dataclasses import dataclass


FORBIDDEN_MODULES: frozenset[str] = frozenset({
    "os",
    "sys",
    "subprocess",
    "shutil",
    "socket",
    "pty",
    "commands",
    "threading",
    "multiprocessing",
    "signal",
    "asyncio",
    "resource",
    "ctypes",
    "builtins",
    "importlib",
    "inspect",
    "pickle",
    "posix",
    "nt",
    "gc",
    "webbrowser",
    "urllib",
    "requests",
    "httpx",
    "aiohttp",
    "tempfile",
    "traceback",
    "pdb",
    "code",
    "codecs",
    "platform",
    "site",
    "_thread",
})

FORBIDDEN_CALLS: frozenset[str] = frozenset({
    "eval",
    "exec",
    "__import__",
    "compile",
    "open",
    "input",
    "breakpoint",
    "globals",
    "locals",
    "vars",
    "memoryview",
    "help",
})

FORBIDDEN_ATTRIBUTES: frozenset[str] = frozenset({
    "__class__",
    "__bases__",
    "__mro__",
    "__subclasses__",
    "__code__",
    "__globals__",
    "__dict__",
    "__closure__",
    "__builtins__",
    "__import__",
    "__loader__",
    "__spec__",
    "gi_frame",
    "cr_frame",
    "ag_frame",
    "f_globals",
    "f_locals",
    "f_code",
})


@dataclass
class SecurityAuditResult:
    is_safe: bool
    error_message: str | None = None
    violation_node: str | None = None


class SafetyVisitor(ast.NodeVisitor):
    def __init__(self):
        self.violations: list[str] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            base_mod = alias.name.split(".")[0]
            if base_mod in FORBIDDEN_MODULES:
                self.violations.append(f"Импорт запрещенного модуля '{alias.name}' (строка {node.lineno})")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            base_mod = node.module.split(".")[0]
            if base_mod in FORBIDDEN_MODULES:
                self.violations.append(f"Импорт из запрещенного модуля '{node.module}' (строка {node.lineno})")
        for alias in node.names:
            if alias.name in FORBIDDEN_MODULES or alias.name in FORBIDDEN_CALLS:
                self.violations.append(f"Импорт запрещенного объекта '{alias.name}' (строка {node.lineno})")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Проверка прямого вызова запрещенной функции: eval(), exec(), open()
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                self.violations.append(f"Вызов запрещенной функции '{node.func.id}()' (строка {node.lineno})")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        if node.attr in FORBIDDEN_ATTRIBUTES:
            self.violations.append(f"Доступ к запрещенному атрибуту '{node.attr}' (строка {node.lineno})")
        self.generic_visit(node)


def audit_code_safety(source_code: str) -> SecurityAuditResult:
    """Выполняет статический анализ исходного кода на наличие запрещенных операций."""
    if not source_code or not source_code.strip():
        return SecurityAuditResult(is_safe=True)

    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        return SecurityAuditResult(
            is_safe=False,
            error_message=f"Синтаксическая ошибка: {e.msg} (строка {e.lineno})",
            violation_node="SyntaxError",
        )

    visitor = SafetyVisitor()
    visitor.visit(tree)

    if visitor.violations:
        return SecurityAuditResult(
            is_safe=False,
            error_message="; ".join(visitor.violations),
            violation_node="SecurityViolation",
        )

    return SecurityAuditResult(is_safe=True)
