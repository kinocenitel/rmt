"""
Редактирование рисков через модалку.

Что проверяем:
  - Изменение названия: новое имя появляется в списке, старое исчезает.
  - Изменение вероятности и влияния меняет уровень риска и зональные бейджи.

Валидация полей модалки (пустое имя, длина) — в test_validation.py.
Добавление тегов через модалку — в test_tags.py.
"""
import pytest

from tests.pages import RiskMatrixPage


@pytest.mark.smoke
def test_edit_risk_name_via_modal(rm: RiskMatrixPage):
    """Клик по имени → модалка → новое имя → сохранить. Старое имя исчезает."""
    rm.add_risk(name="Старое имя риска", prob=2, sev=2)

    rm.edit_risk(current_name="Старое имя риска", new_name="Новое имя риска")

    names = rm.risk_names()
    assert "Новое имя риска" in names
    assert "Старое имя риска" not in names


@pytest.mark.smoke
def test_edit_risk_updates_zone(rm: RiskMatrixPage):
    """Был low (1×1=1), стал crit (4×4=16) — зональные бейджи обновились."""
    rm.add_risk(name="Мигрирующий риск", prob=1, sev=1)
    assert rm.zone_count("low") == 1
    assert rm.zone_count("crit") == 0

    rm.edit_risk(current_name="Мигрирующий риск", new_prob=4, new_sev=4)

    rm.expect_zone_count("low", 0)
    rm.expect_zone_count("crit", 1)
