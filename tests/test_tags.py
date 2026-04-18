"""
Работа с тегами: ввод, автокомплит, теги при редактировании.

Что проверяем:
  - Добавление тегов через Enter и через запятую; нормализация в нижний регистр.
  - Автокомплит подсказывает теги из уже существующих рисков проекта.
  - Добавление нового тега к существующему риску через модалку редактирования.

Граничные значения и ограничения (длина, дубли, лимит 4 тега)
вынесены в test_validation.py.
"""
import pytest
from playwright.sync_api import expect

from tests.pages import RiskMatrixPage


@pytest.mark.smoke
def test_tags_add_via_enter_and_comma(rm: RiskMatrixPage):
    """Теги через Enter и запятую добавляются; регистр нормализуется в нижний."""
    rm.name_input.fill("Риск с тегами")
    rm.add_tag("prod")              # Enter
    rm.add_tag_via_comma("Срочно")  # запятая
    rm.add_tag("ТЕСТ")              # Enter
    rm.add_tag_via_comma("кОмАнДА") # запятая

    pills = rm.tag_pills()
    assert pills == ["prod", "срочно", "тест", "команда"], f"Теги: {pills}"

    rm.add_btn.click()
    rm.expect_active_count(1)


@pytest.mark.smoke
def test_tag_autocomplete_suggests_existing_tags(rm: RiskMatrixPage):
    """Автокомплит предлагает теги из уже добавленных рисков проекта."""
    rm.add_risk(name="Первый риск", prob=1, sev=1, tags=["инфра"])

    rm.name_input.fill("Второй риск")
    rm.tag_input.fill("инф")

    expect(rm.tag_autocomplete).to_be_visible()
    items = rm.tag_autocomplete_items()
    assert "инфра" in items, f"Ожидалась подсказка 'инфра', получено: {items}"


@pytest.mark.smoke
def test_edit_modal_adds_tag_to_existing_risk(rm: RiskMatrixPage):
    """Добавляем тег через модалку редактирования — он появляется в карточке риска."""
    rm.add_risk(name="Риск без тегов → с тегом", prob=2, sev=2)

    rm.open_edit_modal("Риск без тегов → с тегом")
    rm.add_modal_tag("Первый тег")
    rm.modal_save_btn.click()

    risk_row = rm.risk_item_by_name("Риск без тегов → с тегом")
    expect(risk_row).to_contain_text("#первый тег")
