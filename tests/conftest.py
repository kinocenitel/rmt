"""
Фикстуры для тестов Risk Matrix.

Ключевые решения:
1. Локальный http.server поднимается один раз на всю сессию (session scope).
   Тесты ходят на http://localhost:<port>/index.html.
2. Каждый тест получает новый browser_context — это даёт чистый localStorage
   и изоляцию тестов друг от друга.
3. add_init_script выполняется ДО загрузки страницы — мы записываем в
   localStorage пустые массивы для rm_risks / rm_archive, чтобы 8 демо-рисков
   не создавались. Один тест (test_first_run_default_risks) эту фикстуру
   не использует и проверяет дефолтное поведение.
4. Фикстура xlsx_builder умеет создавать валидные/невалидные xlsx-файлы
   для импортных тестов в памяти (во временной папке).
"""
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from openpyxl import Workbook
from playwright.sync_api import Browser, BrowserContext, Page


# ──────────────────────────────────────────────────────────────────────────────
#  Корень проекта: conftest.py лежит в tests/, index.html — на уровень выше.
# ──────────────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _find_free_port() -> int:
    """Находим свободный порт, чтобы не конфликтовать с другими процессами."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_server(host: str, port: int, timeout: float = 5.0) -> None:
    """Ждём, пока http.server действительно начнёт принимать соединения."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError(f"http.server не поднялся на {host}:{port} за {timeout}с")


# ──────────────────────────────────────────────────────────────────────────────
#  Сессионные фикстуры: http-сервер запускается один раз на все тесты.
# ──────────────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def http_server():
    """
    Запускаем python -m http.server из корня проекта. Используем свободный
    порт, чтобы можно было запускать тесты параллельно и не конфликтовать с
    локальными сервисами пользователя.
    """
    port = _find_free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_server("127.0.0.1", port)
        yield f"http://127.0.0.1:{port}"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(scope="session")
def base_url(http_server: str) -> str:
    """URL главной страницы. Использовать в тестах: page.goto(base_url)."""
    return f"{http_server}/index.html"


# ──────────────────────────────────────────────────────────────────────────────
#  Параметры браузера pytest-playwright. Переопределяем только то, что нужно.
# ──────────────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """
    Дефолтные настройки контекста + viewport для стабильности адаптива.
    Desktop 1440x900 — комфортная ширина, где матрица развёрнута.
    """
    return {
        **browser_context_args,
        "viewport": {"width": 1440, "height": 900},
        "locale": "ru-RU",
    }


# ──────────────────────────────────────────────────────────────────────────────
#  Очистка localStorage — главная гарантия изоляции тестов.
# ──────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def clean_context(context: BrowserContext) -> BrowserContext:
    """
    Помечаем контекст — после goto мы вручную очистим демо-риски через JS.
    Просто писать в localStorage пустой массив бесполезно: loadFromStorage()
    в index.html видит length === 0 и перезагружает 8 демо-рисков
    (см. index.html: if (parsed.risks.length > 0) ...).

    Ключи в localStorage (для справки):
      - risk_matrix_risks    — объект { risks: [...], nextId: N }
      - risk_matrix_archive  — массив архива
      - rm_theme             — тема (light/dark)
      - rm_matrix_collapsed  — свёрнута ли матрица (0/1)

    Тест, который хочет проверить дефолтное поведение (8 демо),
    использует fresh_page, а не clean_page.
    """
    return context


@pytest.fixture
def clean_page(clean_context: BrowserContext, base_url: str) -> Page:
    """
    Страница с гарантированно пустым состоянием (0 активных, 0 архив).

    Стратегия: грузим страницу (демо создаются) → через JS обнуляем
    глобальные risks/archivedRisks и перерисовываем. Это быстрее, чем
    нажимать «Очистить» → модалка → подтверждение, и надёжнее, чем
    бороться с loadFromStorage().
    """
    page = clean_context.new_page()
    page.goto(base_url)
    # Ждём, чтобы страница инициализировалась (JS на верхнем уровне
    # уже отработал к моменту, когда load event срабатывает).
    page.wait_for_load_state("domcontentloaded")
    page.evaluate(
        """
        () => {
          risks = [];
          archivedRisks = [];
          nextId = 1;
          if (typeof saveToStorage === 'function') saveToStorage();
          if (typeof saveArchive === 'function') saveArchive();
          if (typeof render === 'function') render();
        }
        """
    )
    return page


@pytest.fixture
def fresh_page(context: BrowserContext, base_url: str) -> Page:
    """
    Страница БЕЗ предварительной очистки localStorage.
    Используется для теста первого запуска, где должны появиться 8 демо-рисков.
    """
    page = context.new_page()
    page.goto(base_url)
    return page


# ──────────────────────────────────────────────────────────────────────────────
#  Page Object.
# ──────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def rm(clean_page: Page):
    """Page Object поверх clean_page (пустое состояние)."""
    from tests.pages import RiskMatrixPage
    return RiskMatrixPage(clean_page)


@pytest.fixture
def rm_fresh(fresh_page: Page):
    """Page Object поверх fresh_page (8 демо-рисков)."""
    from tests.pages import RiskMatrixPage
    return RiskMatrixPage(fresh_page)


# ──────────────────────────────────────────────────────────────────────────────
#  Фикстуры для xlsx-импорта.
# ──────────────────────────────────────────────────────────────────────────────
class XlsxBuilder:
    """
    Генерирует xlsx-файлы для импортных тестов во временной папке.

    Формат подогнан под importXLSX() в index.html:
      - Нужен лист с именем 'Активные' (обязательно).
      - Опциональный лист 'Архив' (для архивных рисков).
      - Колонки (проект принимает как со звёздочкой, так и без):
          ID*, Название риска*, Вероятность*, Влияние*, Теги, Дата добавления
      - ID обязателен, иначе импорт отклоняет файл.
      - prob и sev должны быть 1..4.
    """

    HEADERS = ["ID*", "Название риска*", "Вероятность*", "Влияние*", "Теги"]

    def __init__(self, tmp_path: Path) -> None:
        self._tmp = tmp_path

    def _write(self, active_rows: list[tuple], filename: str) -> Path:
        """Общий писатель. active_rows — список кортежей (id, name, prob, sev, tags)."""
        wb = Workbook()
        ws = wb.active
        ws.title = "Активные"
        ws.append(self.HEADERS)
        for row in active_rows:
            ws.append(list(row))
        path = self._tmp / filename
        wb.save(path)
        return path

    def valid(
        self,
        rows: list[tuple[int, str, int, int, str]] | None = None,
        filename: str = "risks.xlsx",
    ) -> Path:
        """Валидный xlsx: заголовок + строки с данными.
        Каждая строка — (id, name, prob 1..4, sev 1..4, tags через запятую)."""
        rows = rows if rows is not None else [
            (1, "Импорт — риск 1", 2, 3, "qa,smoke"),
            (2, "Импорт — риск 2", 4, 4, "критичный"),
            (3, "Импорт — риск 3", 1, 1, ""),
        ]
        return self._write(rows, filename)

    def empty(self, filename: str = "empty.xlsx") -> Path:
        """Пустой xlsx — только заголовок, ни одного риска."""
        return self._write([], filename)

    def oversized(self, count: int = 101, filename: str = "too_many.xlsx") -> Path:
        """xlsx с количеством рисков больше лимита 100."""
        rows = [(i, f"Риск {i}", 1, 1, "") for i in range(1, count + 1)]
        return self._write(rows, filename)

    def without_id(self, filename: str = "no_id.xlsx") -> Path:
        """xlsx с пустым ID — должен вызвать ошибку импорта."""
        return self._write([("", "Риск без ID", 1, 1, "")], filename)


@pytest.fixture
def xlsx_builder(tmp_path: Path) -> XlsxBuilder:
    """Каждому тесту — свой tmp_path, чтобы файлы не пересекались."""
    return XlsxBuilder(tmp_path)
