"""
Критичные smoke-тесты: основной happy path приложения.

Здесь только то, что должно работать всегда — если хоть один тест упал,
приложение нельзя считать рабочим. Быстрый старт: запускай эти тесты первыми.

Валидация и лимиты — test_validation.py
Фильтры и сортировка — test_filters_sort.py
Редактирование — test_editing.py
Теги — test_tags.py
UI-состояние и хоткеи — test_ui.py
Очистка — test_clear.py
Экспорт / импорт — test_export_import.py
"""
import re

import pytest
from playwright.sync_api import expect

from tests.pages import RiskMatrixPage


# ═══════════════════════════════════════════════════════════════════════════
#  1. Первый запуск: 8 демо-рисков, интерфейс инициализирован.
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
def test_first_run_default_risks(rm_fresh: RiskMatrixPage):
    """На чистом localStorage появляются 8 демо-рисков, счётчик = 8."""
    expect(rm_fresh.page).to_have_title(re.compile("Матрица рисков", re.I))
    rm_fresh.expect_active_count(8)
    assert rm_fresh.risk_items.count() == 8
    total = sum(rm_fresh.zone_count(z) for z in ("crit", "high", "mid", "low"))
    assert total == 8, f"Сумма по зонам ({total}) не равна числу рисков (8)"


# ═══════════════════════════════════════════════════════════════════════════
#  2. Добавление одного риска с пустого состояния.
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
def test_add_single_risk(rm: RiskMatrixPage):
    """Добавили один риск — появился в списке, счётчик = 1."""
    rm.expect_active_count(0)
    rm.add_risk(name="Прод упадёт в пятницу вечером", prob=3, sev=4, tags=["беда"])
    rm.expect_active_count(1)
    assert rm.risk_items.count() == 1
    assert rm.risk_item_by_name("Прод упадёт в пятницу вечером").is_visible()


# ═══════════════════════════════════════════════════════════════════════════
#  3. Зональные бейджи корректно считают количество по уровням.
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
def test_zone_badges_count_by_level(rm: RiskMatrixPage):
    """
    score = prob × sev:
      ≥12 → crit, 9–11 → high, 4–8 → mid, <4 → low
    """
    rm.add_risk(name="Критичный", prob=4, sev=4)   # 16 → crit
    rm.add_risk(name="Высокий",   prob=3, sev=4)   # 12 → crit (≥12)
    rm.add_risk(name="Средний",   prob=3, sev=3)   # 9  → high
    rm.add_risk(name="Пустяк",    prob=1, sev=1)   # 1  → low

    assert rm.zone_count("crit") == 2
    assert rm.zone_count("high") == 1
    assert rm.zone_count("mid") == 0
    assert rm.zone_count("low") == 1


# ═══════════════════════════════════════════════════════════════════════════
#  4. Архивирование: риск уходит во вкладку «Архив».
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
def test_archive_risk(rm: RiskMatrixPage):
    """Добавили → архивировали → активных 0, архив 1."""
    rm.add_risk(name="Для архива", prob=2, sev=2)
    rm.expect_active_count(1)

    rm.archive_risk("Для архива")
    rm.expect_active_count(0)
    rm.expect_archive_count(1)

    rm.open_archive_tab()
    assert rm.archive_item_by_name("Для архива").is_visible()


# ═══════════════════════════════════════════════════════════════════════════
#  5. Восстановление из архива.
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
def test_restore_from_archive(rm: RiskMatrixPage):
    """Архивировали → восстановили → риск снова в «Активных»."""
    rm.add_risk(name="Для восстановления", prob=2, sev=2)
    rm.archive_risk("Для восстановления")
    rm.open_archive_tab()

    rm.restore_risk("Для восстановления")
    rm.expect_archive_count(0)
    rm.expect_active_count(1)

    rm.open_active_tab()
    assert rm.risk_item_by_name("Для восстановления").is_visible()


# ═══════════════════════════════════════════════════════════════════════════
#  6. Удаление насовсем.
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
def test_delete_risk_permanently(rm: RiskMatrixPage):
    """Удалили насовсем — риска нет ни в активных, ни в архиве."""
    rm.add_risk(name="Для удаления", prob=1, sev=1)
    rm.expect_active_count(1)

    rm.delete_risk("Для удаления")
    rm.expect_active_count(0)
    rm.expect_archive_count(0)


# ═══════════════════════════════════════════════════════════════════════════
#  7. Риски сохраняются после reload.
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
def test_risks_persist_after_reload(rm: RiskMatrixPage):
    """Добавили риск → reload → риск на месте."""
    rm.add_risk(name="Риск переживёт reload", prob=2, sev=3, tags=["persist"])
    rm.expect_active_count(1)

    rm.reload()

    rm.expect_active_count(1)
    assert rm.risk_item_by_name("Риск переживёт reload").is_visible()
