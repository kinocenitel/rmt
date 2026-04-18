"""
Очистка всех рисков.

Что проверяем:
  - «Очистить всё» + подтверждение: список пуст, после reload возвращаются
    8 демо-рисков (проект грузит дефолт, если хранилище пустое).
  - Отмена очистки (Escape, крестик, клик по фону): список не меняется.
"""
import pytest
from playwright.sync_api import expect

from tests.pages import RiskMatrixPage


@pytest.mark.smoke
def test_clear_all_empties_and_demo_returns_after_reload(rm: RiskMatrixPage):
    """Подтверждаем очистку → 0 рисков. После reload → 8 демо-рисков."""
    rm.add_risk(name="Риск на удаление #1", prob=2, sev=2)
    rm.add_risk(name="Риск на удаление #2", prob=4, sev=4)
    rm.expect_active_count(2)

    rm.clear_all(confirm=True)
    rm.expect_active_count(0)

    rm.reload()
    rm.expect_active_count(8)


@pytest.mark.smoke
@pytest.mark.parametrize("close_method", [
    "escape",
    "close_btn",
    "backdrop",
], ids=["Escape", "Крестик", "Клик по фону"])
def test_clear_all_cancel_closes_modal_safely(rm: RiskMatrixPage, close_method):
    """Отменяем очистку — модалка закрывается, риски на месте."""
    rm.add_risk(name="Риск должен выжить", prob=2, sev=2)

    rm.clear_btn.click()
    expect(rm.confirm_modal).to_be_visible()

    if close_method == "escape":
        rm.page.keyboard.press("Escape")
    elif close_method == "close_btn":
        rm.confirm_modal_close_btn.click()
    elif close_method == "backdrop":
        rm.page.mouse.click(10, 10)

    expect(rm.confirm_modal).to_be_hidden()
    rm.expect_active_count(1)
    assert "Риск должен выжить" in rm.risk_names()
