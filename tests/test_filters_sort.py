"""
Фильтрация, сортировка и клавиатурная навигация в фильтрах.

Что проверяем:
  - Фильтр по уровню риска (crit/high/mid/low) + сброс всех фильтров.
  - Фильтр по тегу + пункт «Без тега».
  - Сортировка по score (по убыванию / по возрастанию).
  - Клавиатурная навигация в выпадашке фильтра: стрелки, Home, Enter.
  - Регрессия: стрелка в выпадашке тегов сдвигает фокус на 1 пункт, не на 2.
"""
import pytest
from playwright.sync_api import expect

from tests.pages import RiskMatrixPage


# ═══════════════════════════════════════════════════════════════════════════
#  Фильтр по уровню
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
def test_filter_by_level_shows_only_matching(rm: RiskMatrixPage):
    """Включаем фильтр «Критический» — в списке только критичные риски.
    Счётчик вкладки становится «X из Y»."""
    rm.add_risk(name="Крит #1", prob=4, sev=4)   # score 16 → crit
    rm.add_risk(name="Крит #2", prob=3, sev=4)   # score 12 → crit
    rm.add_risk(name="Высокий", prob=3, sev=3)   # score 9  → high
    rm.add_risk(name="Низкий",  prob=1, sev=1)   # score 1  → low

    rm.open_filter()
    assert rm.level_filter_count("crit") == 2
    assert rm.level_filter_count("high") == 1
    assert rm.level_filter_count("low") == 1

    rm.toggle_level_filter("crit")

    expect(rm.risk_items).to_have_count(2)
    names = rm.risk_names()
    assert "Крит #1" in names and "Крит #2" in names
    assert "Высокий" not in names and "Низкий" not in names
    expect(rm.page.locator("#tab-active-count")).to_have_text("2 из 4")


@pytest.mark.smoke
def test_reset_filters_restores_full_list(rm: RiskMatrixPage):
    """Включили фильтр → сбросили → полный список, счётчик без «X из Y»."""
    rm.add_risk(name="Первый", prob=4, sev=4)   # crit
    rm.add_risk(name="Второй", prob=1, sev=1)   # low

    rm.toggle_level_filter("crit")
    assert rm.risk_items.count() == 1

    rm.reset_all_filters()
    assert rm.risk_items.count() == 2
    expect(rm.page.locator("#tab-active-count")).to_have_text("2")


# ═══════════════════════════════════════════════════════════════════════════
#  Фильтр по тегу
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
def test_filter_by_tag_shows_only_matching(rm: RiskMatrixPage):
    """Фильтр по тегу 'frontend' — видны только риски с этим тегом."""
    rm.add_risk(name="Frontend-риск",  prob=2, sev=2, tags=["frontend"])
    rm.add_risk(name="Backend-риск",   prob=3, sev=3, tags=["backend"])
    rm.add_risk(name="Общий риск",     prob=1, sev=1, tags=["frontend", "backend"])
    rm.add_risk(name="Риск без тегов", prob=4, sev=4, tags=[])

    rm.toggle_tag_filter("frontend")

    names = rm.risk_names()
    assert "Frontend-риск" in names
    assert "Общий риск" in names
    assert "Backend-риск" not in names
    assert "Риск без тегов" not in names


@pytest.mark.smoke
def test_filter_no_tag_shows_only_untagged(rm: RiskMatrixPage):
    """Пункт «Без тега» — в списке только риски без тегов."""
    rm.add_risk(name="Риск с тегом",           prob=2, sev=2, tags=["tag"])
    rm.add_risk(name="Риск без тегов",          prob=1, sev=1)
    rm.add_risk(name="Ещё один риск без тегов", prob=3, sev=3)

    rm.open_tag_filter()
    no_tag_item = rm.page.locator(".tag-filter-item").filter(has_text="Без тега").first
    no_tag_item.locator('input[type="checkbox"]').click()

    names = rm.risk_names()
    assert "Риск без тегов" in names
    assert "Ещё один риск без тегов" in names
    assert "Риск с тегом" not in names


# ═══════════════════════════════════════════════════════════════════════════
#  Сортировка
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
@pytest.mark.parametrize("mode, expected", [
    ("desc", ["Тяжёлый", "Средний", "Лёгкий"]),
    ("asc",  ["Лёгкий",  "Средний", "Тяжёлый"]),
], ids=["По убыванию", "По возрастанию"])
def test_sort_orders_by_score(rm: RiskMatrixPage, mode: str, expected: list):
    rm.add_risk(name="Лёгкий",  prob=1, sev=1)   # score 1
    rm.add_risk(name="Тяжёлый", prob=4, sev=4)   # score 16
    rm.add_risk(name="Средний", prob=2, sev=3)   # score 6

    rm.set_sort(mode)
    assert rm.active_sort_mode() == mode
    names = rm.risk_names()
    assert names == expected, f"Режим {mode!r}: ожидался {expected}, получено: {names}"


# ═══════════════════════════════════════════════════════════════════════════
#  Клавиатурная навигация в фильтрах
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
def test_filter_dropdown_arrow_navigation_and_enter(rm: RiskMatrixPage):
    """Открываем фильтр → стрелка ↓ → Enter → активируется следующий уровень."""
    rm.add_risk(name="Критический риск", prob=4, sev=4)
    rm.add_risk(name="Высокий риск",     prob=3, sev=3)
    rm.add_risk(name="Средний риск",     prob=2, sev=2)
    rm.add_risk(name="Низкий риск",      prob=1, sev=1)

    rm.page.locator("#filter-btn").click()
    expect(rm.page.locator("#filter-crit")).to_be_focused()

    rm.page.keyboard.press("ArrowDown")
    expect(rm.page.locator("#filter-high")).to_be_focused()

    rm.page.keyboard.press("Enter")

    names = rm.risk_names()
    assert names == ["Высокий риск"], f"Ожидался только 'Высокий', а получено: {names}"


@pytest.mark.smoke
def test_filter_dropdown_home_key_jumps_to_first(rm: RiskMatrixPage):
    """Нажали ↓ несколько раз → Home → фокус возвращается на первый пункт (crit)."""
    rm.add_risk(name="Риск для навигации", prob=1, sev=1)
    rm.add_risk(name="Второй риск", prob=2, sev=2)
    rm.page.locator("#filter-btn").click()
    for _ in range(3):
        rm.page.keyboard.press("ArrowDown")
    rm.page.keyboard.press("Home")
    expect(rm.page.locator("#filter-crit")).to_be_focused()


@pytest.mark.smoke
def test_tag_filter_arrow_moves_one_step_not_two(rm: RiskMatrixPage):
    """Регрессия: keydown из #tag-filter-dropdown не должен всплывать в
    #filter-dropdown и двигать фокус дважды за одно нажатие."""
    rm.add_risk(name="A", prob=2, sev=2, tags=["alpha"])
    rm.add_risk(name="B", prob=2, sev=2, tags=["beta"])
    rm.add_risk(name="C", prob=2, sev=2, tags=["gamma"])

    rm.page.locator("#filter-btn").click()
    rm.page.locator("#tag-filter-btn").click()

    tag_checkboxes = rm.page.locator('#tag-filter-dropdown input[type="checkbox"]')
    assert tag_checkboxes.count() >= 3, "Нужны минимум 3 тега для теста"

    expect(tag_checkboxes.nth(0)).to_be_focused()

    rm.page.keyboard.press("ArrowDown")
    expect(tag_checkboxes.nth(1)).to_be_focused()

    rm.page.keyboard.press("ArrowDown")
    expect(tag_checkboxes.nth(2)).to_be_focused()
