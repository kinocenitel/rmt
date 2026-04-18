"""
Состояние UI и горячие клавиши.

Что проверяем:
  - Переключение тёмной/светлой темы и сохранение в localStorage.
  - Сворачивание/разворачивание матрицы и сохранение состояния.
  - Хоткей Shift+? открывает подсказку горячих клавиш.
  - Хоткей Shift+N фокусирует поле ввода названия нового риска.
"""
import pytest
from playwright.sync_api import expect

from tests.pages import RiskMatrixPage


# ═══════════════════════════════════════════════════════════════════════════
#  Тема
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
def test_theme_toggle_persists_after_reload(rm: RiskMatrixPage):
    """Переключаем в тёмную тему — после reload остаётся тёмная."""
    assert not rm.is_dark_theme(), "Стартуем в светлой теме"

    rm.toggle_theme()
    assert rm.is_dark_theme()
    assert rm.ls_get("rm_theme") == "dark"

    rm.reload()
    assert rm.is_dark_theme(), "После reload тёмная тема сохранилась"


@pytest.mark.smoke
def test_theme_can_switch_back_to_light(rm: RiskMatrixPage):
    """Повторный клик по переключателю возвращает светлую тему."""
    rm.toggle_theme()
    assert rm.is_dark_theme()

    rm.toggle_theme()
    assert not rm.is_dark_theme()
    assert rm.ls_get("rm_theme") == "light"


# ═══════════════════════════════════════════════════════════════════════════
#  Матрица
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
def test_matrix_collapse_persists_after_reload(rm: RiskMatrixPage):
    """Сворачиваем матрицу — после reload остаётся свёрнутой."""
    assert not rm.is_matrix_collapsed(), "Стартуем в развёрнутом режиме"

    rm.toggle_matrix()
    assert rm.is_matrix_collapsed()
    assert rm.ls_get("rm_matrix_collapsed") == "1"

    rm.reload()
    assert rm.is_matrix_collapsed(), "После reload матрица остаётся свёрнутой"


# ═══════════════════════════════════════════════════════════════════════════
#  Горячие клавиши
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
def test_hotkey_question_opens_help_modal(rm: RiskMatrixPage):
    """Shift+/ открывает модалку с подсказкой горячих клавиш."""
    hotkey_hint = rm.page.locator("#hotkey-hint")
    assert "open" not in (hotkey_hint.get_attribute("class") or "").split()

    rm.page.locator("body").click()
    rm.page.keyboard.press("Shift+Slash")

    rm.page.wait_for_function(
        "() => document.getElementById('hotkey-hint')?.classList.contains('open')",
        timeout=2_000,
    )


@pytest.mark.smoke
def test_hotkey_n_focuses_name_input(rm: RiskMatrixPage):
    """Shift+N фокусирует поле #risk-name."""
    rm.page.locator("body").click()
    rm.page.keyboard.press("Shift+N")
    expect(rm.name_input).to_be_focused()
