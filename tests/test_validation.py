"""
Валидация полей и лимиты.

Что проверяем:
  - Название риска: пустое (ошибка), 1 символ, 80 символов (успех), 81 символ
    (обрезается maxlength=80). Проверяется и форма добавления, и модалка.
  - Лимит 100 рисков: 101-й блокируется; архивированные учитываются в лимите.
  - Теги: длина ≤25 символов, уникальность, максимум 4 тега на риск.
"""
import pytest
from playwright.sync_api import expect

from tests.pages import RiskMatrixPage


# ═══════════════════════════════════════════════════════════════════════════
#  Название — форма добавления
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
def test_add_name_empty_shows_error(rm: RiskMatrixPage):
    """Пустое название → ошибка валидации, риск не создаётся."""
    rm.add_btn.click()
    rm.expect_error_message("имя")
    rm.expect_active_count(0)


@pytest.mark.smoke
def test_add_name_1_char_accepted(rm: RiskMatrixPage):
    """1 символ — минимально допустимое название."""
    rm.add_risk(name="А", prob=1, sev=1)
    rm.expect_active_count(1)
    assert rm.risk_item_by_name("А").is_visible()


@pytest.mark.smoke
def test_add_name_80_chars_accepted(rm: RiskMatrixPage):
    """80 символов — максимально допустимое название."""
    name = "А" * 80
    rm.add_risk(name=name, prob=1, sev=1)
    rm.expect_active_count(1)
    assert rm.risk_item_by_name(name).is_visible()


@pytest.mark.smoke
def test_add_name_81_chars_blocked_by_maxlength(rm: RiskMatrixPage):
    """81-й символ не принимается: maxlength=80 обрезает ввод до 80 символов."""
    rm.name_input.press_sequentially("А" * 81)
    actual = rm.name_input.input_value()
    assert len(actual) <= 80, f"Ожидали ≤80 символов, получили {len(actual)}"
    # После обрезки риск с 80-символьным именем добавляется без ошибок
    rm.add_btn.click()
    expect(rm.name_error).not_to_be_visible()
    rm.expect_active_count(1)


# ═══════════════════════════════════════════════════════════════════════════
#  Название — модалка редактирования
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
def test_edit_name_empty_shows_error(rm: RiskMatrixPage):
    """Очистить название в модалке и сохранить → ошибка, модалка остаётся."""
    rm.add_risk(name="Исходный риск", prob=1, sev=1)
    rm.open_edit_modal("Исходный риск")
    rm.modal_name_input.fill("")
    rm.modal_save_btn.click()
    expect(rm.page.locator("#modal-name-error")).to_be_visible()
    expect(rm.page.locator("#edit-modal")).to_be_visible()


@pytest.mark.smoke
def test_edit_name_1_char_accepted(rm: RiskMatrixPage):
    """1 символ в модалке — сохраняется успешно."""
    rm.add_risk(name="Исходный риск", prob=1, sev=1)
    rm.edit_risk("Исходный риск", new_name="Б")
    assert rm.risk_item_by_name("Б").is_visible()


@pytest.mark.smoke
def test_edit_name_80_chars_accepted(rm: RiskMatrixPage):
    """80 символов в модалке — сохраняется успешно."""
    rm.add_risk(name="Исходный риск", prob=1, sev=1)
    new_name = "Б" * 80
    rm.edit_risk("Исходный риск", new_name=new_name)
    assert rm.risk_item_by_name(new_name).is_visible()


@pytest.mark.smoke
def test_edit_name_81_chars_blocked_by_maxlength(rm: RiskMatrixPage):
    """81-й символ в модалке не принимается: maxlength=80 обрезает до 80."""
    rm.add_risk(name="Исходный риск", prob=1, sev=1)
    rm.open_edit_modal("Исходный риск")
    modal_input = rm.modal_name_input
    modal_input.fill("")
    modal_input.press_sequentially("Б" * 81)
    actual = modal_input.input_value()
    assert len(actual) <= 80, f"Ожидали ≤80 символов, получили {len(actual)}"


# ═══════════════════════════════════════════════════════════════════════════
#  Лимит 100 рисков
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
def test_limit_100_blocks_101st_active(rm: RiskMatrixPage):
    """100 рисков через state-инъекцию, 101-й через UI → ошибка."""
    rm.page.evaluate(
        """
        () => {
          risks = Array.from({length: 100}, (_, i) => ({
            id: i + 1, name: 'Risk #' + (i + 1), prob: 1, sev: 1,
            createdAt: Date.now(), tags: []
          }));
          nextId = 101;
          saveToStorage();
          render();
        }
        """
    )
    rm.expect_active_count(100)
    rm.add_risk(name="101-й лишний", prob=1, sev=1)
    rm.expect_error_message("максимум 100")
    rm.expect_active_count(100)


@pytest.mark.smoke
def test_limit_100_counts_archive_too(rm: RiskMatrixPage):
    """80 активных + 20 в архиве = 100. 101-й блокируется."""
    rm.page.evaluate(
        """
        () => {
          risks = Array.from({length: 80}, (_, i) => ({
            id: i + 1, name: 'Active #' + (i + 1), prob: 1, sev: 1,
            createdAt: Date.now(), tags: []
          }));
          archivedRisks = Array.from({length: 20}, (_, i) => ({
            id: 100 + i + 1, name: 'Archived #' + (i + 1), prob: 1, sev: 1,
            createdAt: Date.now(), archivedAt: Date.now(), tags: []
          }));
          nextId = 121;
          saveToStorage();
          saveArchive();
          render();
        }
        """
    )
    rm.expect_active_count(80)
    rm.expect_archive_count(20)
    rm.add_risk(name="Лишний, поверх лимита", prob=1, sev=1)
    rm.expect_error_message("максимум 100")
    rm.expect_active_count(80)
    rm.expect_archive_count(20)


# ═══════════════════════════════════════════════════════════════════════════
#  Теги — ограничения
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.smoke
def test_tag_length_limit(rm: RiskMatrixPage):
    """25 символов — ровно на границе (тег добавляется). 26 — ошибка."""
    rm.name_input.fill("Риск для теста тегов")

    rm.add_tag("a" * 25)
    assert rm.tag_pills() == ["a" * 25]
    expect(rm.tag_error).not_to_be_visible()

    rm.add_tag("b" * 26)
    assert len(rm.tag_pills()) == 1
    expect(rm.tag_error).to_be_visible()
    expect(rm.tag_error).to_contain_text("25")


@pytest.mark.smoke
def test_duplicate_tag_is_rejected(rm: RiskMatrixPage):
    """Дубликат тега (в любом регистре) не добавляется — показывается ошибка."""
    rm.name_input.fill("Риск с дублирующими тегами")

    rm.add_tag("qa")
    expect(rm.tag_error).not_to_be_visible()

    for dup in ["qa", "QA", "qA", "Qa"]:
        rm.add_tag(dup)
        expect(rm.tag_error).to_be_visible()
        expect(rm.tag_error).to_contain_text("уже есть")

    assert len(rm.tag_pills()) == 1
    assert rm.tag_pills()[0].lower() == "qa"


@pytest.mark.smoke
def test_max_four_tags_per_risk(rm: RiskMatrixPage):
    """Максимум 4 тега на риск — пятый отклоняется с ошибкой."""
    rm.name_input.fill("Риск с кучей тегов")

    for tag in ["one", "two", "three", "four"]:
        rm.add_tag(tag)
    assert len(rm.tag_pills()) == 4

    rm.add_tag("five")
    assert len(rm.tag_pills()) == 4
    expect(rm.tag_error).to_be_visible()
    expect(rm.tag_error).to_contain_text("4")
