"""
Page Object для Risk Matrix.

Инкапсулирует селекторы и действия, чтобы тесты были читаемы и
при изменениях UI правки делались в одном месте.

Стратегия селекторов:
- Там, где есть стабильный id, используем id-селектор (#tab-active).
- Там, где нет — используем data-testid, который мы добавили в index.html.
- Кастомные селекты prob/sev выставляем через page.evaluate(selectOption(...)),
  а не кликами по списку опций — это надёжнее и быстрее.
"""
from __future__ import annotations

from playwright.sync_api import Page, Locator, expect


class RiskMatrixPage:
    """Обёртка над страницей Risk Matrix."""

    def __init__(self, page: Page) -> None:
        self.page = page

    # ─── Общее ────────────────────────────────────────────────────────────
    @property
    def title(self) -> str:
        return self.page.title()

    def reload(self) -> None:
        self.page.reload()
        self.page.wait_for_load_state("domcontentloaded")

    # ─── Форма добавления риска ───────────────────────────────────────────
    @property
    def name_input(self) -> Locator:
        return self.page.locator("#risk-name")

    @property
    def name_error(self) -> Locator:
        return self.page.locator("#risk-name-error")

    @property
    def tag_input(self) -> Locator:
        return self.page.locator("#tag-text-input")

    @property
    def add_btn(self) -> Locator:
        return self.page.get_by_test_id("btn-add-risk")

    def set_probability(self, value: int) -> None:
        """value ∈ {1,2,3,4}"""
        assert 1 <= value <= 4, "probability must be 1..4"
        self.page.evaluate(f"selectOption('cs-risk-prob', {value})")

    def set_severity(self, value: int) -> None:
        """value ∈ {1,2,3,4}"""
        assert 1 <= value <= 4, "severity must be 1..4"
        self.page.evaluate(f"selectOption('cs-risk-sev', {value})")

    def add_tag(self, tag: str) -> None:
        """Добавить тег через Enter."""
        self.tag_input.fill(tag)
        self.tag_input.press("Enter")

    def add_tag_via_comma(self, tag: str) -> None:
        """Добавить тег через запятую."""
        self.tag_input.fill(tag)
        self.tag_input.press(",")

    def add_risk(
        self,
        name: str,
        prob: int = 1,
        sev: int = 1,
        tags: list[str] | None = None,
    ) -> None:
        """Заполнить форму и нажать «Добавить»."""
        self.name_input.fill(name)
        self.set_probability(prob)
        self.set_severity(sev)
        for tag in tags or []:
            self.add_tag(tag)
        self.add_btn.click()

    # ─── Тулбар ───────────────────────────────────────────────────────────
    @property
    def export_xlsx_btn(self) -> Locator:
        return self.page.locator("#btn-export-xlsx")

    @property
    def import_xlsx_label(self) -> Locator:
        return self.page.locator("#btn-import-xlsx")

    @property
    def import_xlsx_input(self) -> Locator:
        return self.page.locator('#btn-import-xlsx input[type="file"]')

    @property
    def export_png_btn(self) -> Locator:
        return self.page.get_by_test_id("btn-export-png")

    @property
    def export_html_btn(self) -> Locator:
        return self.page.get_by_test_id("btn-export-html")

    @property
    def clear_btn(self) -> Locator:
        return self.page.get_by_test_id("btn-clear-all")

    # ─── Вкладки и счётчики ───────────────────────────────────────────────
    @property
    def active_tab(self) -> Locator:
        return self.page.locator("#tab-active")

    @property
    def archive_tab(self) -> Locator:
        return self.page.locator("#tab-archive")

    def open_active_tab(self) -> None:
        self.active_tab.click()

    def open_archive_tab(self) -> None:
        self.archive_tab.click()

    def active_count(self) -> int:
        """Число в бейдже вкладки «Активные». Может быть 'X из Y' при фильтре."""
        text = self.page.locator("#tab-active-count").inner_text().strip()
        # При фильтрации: '3 из 10' → берём число после 'из'
        return int(text.split()[-1]) if text else 0

    def archive_count(self) -> int:
        text = self.page.locator("#tab-archive-count").inner_text().strip()
        return int(text.split()[-1]) if text else 0

    # ─── Зональные бейджи ─────────────────────────────────────────────────
    def zone_count(self, zone: str) -> int:
        """zone ∈ {'crit','high','mid','low'}"""
        return int(self.page.locator(f"#zone-badge-{zone}").inner_text().strip())

    # ─── Список рисков ────────────────────────────────────────────────────
    @property
    def risk_items(self) -> Locator:
        """Все элементы активного списка (с testid='risk-item')."""
        return self.page.get_by_test_id("risk-item")

    @property
    def archive_items(self) -> Locator:
        """Все элементы архивного списка."""
        return self.page.get_by_test_id("risk-item-archive")

    def risk_item_by_name(self, name: str) -> Locator:
        """Найти строку активного риска по имени."""
        return self.risk_items.filter(
            has=self.page.get_by_test_id("risk-item-name").filter(has_text=name)
        ).first

    def archive_item_by_name(self, name: str) -> Locator:
        """Найти строку архивного риска по имени."""
        return self.archive_items.filter(
            has=self.page.get_by_test_id("risk-item-name").filter(has_text=name)
        ).first

    def risk_names(self) -> list[str]:
        """Список имён всех активных рисков в текущем порядке."""
        return self.risk_items.locator('[data-testid="risk-item-name"]').all_inner_texts()

    def archive_names(self) -> list[str]:
        return self.archive_items.locator('[data-testid="risk-item-name"]').all_inner_texts()

    # ─── Удаление / архивирование / восстановление ────────────────────────
    def archive_risk(self, name: str) -> None:
        """Удалить риск → выбрать «В архив» в модалке."""
        self.risk_item_by_name(name).get_by_test_id("risk-del").click()
        self.page.get_by_test_id("confirm-delete-archive").click()

    def delete_risk(self, name: str) -> None:
        """Удалить риск → выбрать «Удалить» (насовсем) в модалке."""
        self.risk_item_by_name(name).get_by_test_id("risk-del").click()
        self.page.get_by_test_id("confirm-delete-ok").click()

    def restore_risk(self, name: str) -> None:
        """Восстановить риск из архива (нужно быть на вкладке «Архив»)."""
        self.archive_item_by_name(name).get_by_test_id("risk-restore").click()

    def clear_all(self, confirm: bool = True) -> None:
        """Нажать «Очистить» и, если confirm=True, подтвердить."""
        self.clear_btn.click()
        if confirm:
            self.page.get_by_test_id("confirm-clear-ok").click()

    @property
    def confirm_modal(self) -> Locator:
        return self.page.locator("#confirm-modal")

    @property
    def confirm_modal_close_btn(self) -> Locator:
        return self.page.locator("#confirm-modal .modal-close")

    # ─── Сортировка ───────────────────────────────────────────────────────
    def set_sort(self, mode: str) -> None:
        """mode ∈ {'default', 'desc', 'asc'}"""
        assert mode in ("default", "desc", "asc")
        self.page.locator(f"#sort-{mode}").click()

    def active_sort_mode(self) -> str:
        """Какой режим сортировки сейчас активен."""
        for mode in ("default", "desc", "asc"):
            cls = self.page.locator(f"#sort-{mode}").get_attribute("class") or ""
            if "active" in cls.split():
                return mode
        return "default"

    # ─── Фильтры по уровню ────────────────────────────────────────────────
    def open_filter(self) -> None:
        """Открыть выпадашку фильтра (если ещё не открыта)."""
        dropdown = self.page.locator("#filter-dropdown")
        if not dropdown.is_visible():
            self.page.locator("#filter-btn").click()

    def toggle_level_filter(self, level: str) -> None:
        """level ∈ {'crit','high','mid','low'}. Кликает чекбокс напрямую."""
        assert level in ("crit", "high", "mid", "low")
        self.open_filter()
        self.page.locator(f"#filter-{level}").click()

    def reset_all_filters(self) -> None:
        """Нажать «Сбросить всё» в выпадашке фильтра."""
        self.open_filter()
        self.page.locator("#filter-reset-btn").click()

    def level_filter_count(self, level: str) -> int:
        """Счётчик рядом с уровнем в выпадашке фильтра."""
        assert level in ("crit", "high", "mid", "low")
        return int(self.page.locator(f"#fc-{level}").inner_text().strip())

    # ─── Теги ─────────────────────────────────────────────────────────────
    @property
    def tag_error(self) -> Locator:
        """Сообщение об ошибке ввода тега (форма добавления)."""
        return self.page.locator("#tag-error")

    def tag_pills(self) -> list[str]:
        """Текущие теги-пилюли в форме добавления (в нижнем регистре).

        В DOM пилюля выглядит как:
          <span class="tag-pill">#имя<span class="tag-pill-x">✕</span></span>
        Берём только первый text-node, игнорируя дочерний span с крестиком,
        и убираем ведущий '#', который проект рисует как визуальный маркер.
        """
        return self.page.locator("#tag-pills-row .tag-pill").evaluate_all(
            "els => els.map(el => {"
            "  const t = el.firstChild ? el.firstChild.textContent.trim() : '';"
            "  return t.startsWith('#') ? t.slice(1) : t;"
            "})"
        )

    # ─── Фильтр по тегам (вложен в фильтр) ───────────────────────────────
    def open_tag_filter(self) -> None:
        """Открыть главную выпадашку фильтра + подвыпадашку по тегам."""
        self.open_filter()
        tag_dropdown = self.page.locator("#tag-filter-dropdown")
        if not tag_dropdown.is_visible():
            self.page.locator("#tag-filter-btn").click()

    def toggle_tag_filter(self, tag: str) -> None:
        """Включить/выключить фильтр по тегу. tag передаётся без '#'."""
        self.open_tag_filter()
        # Пункт: <label class="tag-filter-item">…#tag</label>
        item = (
            self.page.locator(".tag-filter-item")
            .filter(has_text=f"#{tag}")
            .first
        )
        item.locator('input[type="checkbox"]').click()

    # ─── Автокомплит тегов ────────────────────────────────────────────────
    @property
    def tag_autocomplete(self) -> Locator:
        return self.page.locator("#tag-autocomplete")

    def tag_autocomplete_items(self) -> list[str]:
        """Варианты, которые сейчас показываются в выпадашке автокомплита."""
        if not self.tag_autocomplete.is_visible():
            return []
        return self.tag_autocomplete.locator(".tag-autocomplete-item").all_inner_texts()

    # ─── Матрица / тема ───────────────────────────────────────────────────
    @property
    def matrix_toggle_btn(self) -> Locator:
        return self.page.locator("#matrix-toggle-btn")

    def is_matrix_collapsed(self) -> bool:
        return self.page.locator("body").evaluate(
            "el => el.classList.contains('matrix-collapsed')"
        )

    def toggle_matrix(self) -> None:
        self.matrix_toggle_btn.click()

    @property
    def theme_toggle_btn(self) -> Locator:
        return self.page.locator("#theme-toggle")

    def is_dark_theme(self) -> bool:
        """Проверка по классу на <body>, куда проект вешает .dark."""
        return self.page.locator("body").evaluate(
            "el => el.classList.contains('dark')"
        )

    def toggle_theme(self) -> None:
        self.theme_toggle_btn.click()

    def ls_get(self, key: str) -> str | None:
        """Достать значение из localStorage — удобно для проверок persistence."""
        return self.page.evaluate(f"() => localStorage.getItem({key!r})")

    # ─── Модалка редактирования риска ────────────────────────────────────
    @property
    def modal_name_input(self) -> Locator:
        return self.page.locator("#modal-name")

    @property
    def modal_save_btn(self) -> Locator:
        return self.page.locator(".modal-save")

    def open_edit_modal(self, risk_name: str) -> None:
        """Открыть модалку редактирования кликом по имени риска."""
        self.risk_item_by_name(risk_name).get_by_test_id("risk-item-name").click()

    def set_modal_probability(self, value: int) -> None:
        assert 1 <= value <= 4
        self.page.evaluate(f"selectOption('cs-modal-prob', {value})")

    def set_modal_severity(self, value: int) -> None:
        assert 1 <= value <= 4
        self.page.evaluate(f"selectOption('cs-modal-sev', {value})")

    def edit_risk(
        self,
        current_name: str,
        new_name: str | None = None,
        new_prob: int | None = None,
        new_sev: int | None = None,
    ) -> None:
        """Открыть модалку по текущему имени, изменить указанные поля, сохранить."""
        self.open_edit_modal(current_name)
        if new_name is not None:
            self.modal_name_input.fill(new_name)
        if new_prob is not None:
            self.set_modal_probability(new_prob)
        if new_sev is not None:
            self.set_modal_severity(new_sev)
        self.modal_save_btn.click()
        expect(self.page.locator("#edit-modal")).to_be_hidden()

    def add_modal_tag(self, tag: str) -> None:
        """Добавить тег в открытой модалке редактирования через Enter."""
        tag_input = self.page.locator("#modal-tag-input")
        tag_input.fill(tag)
        tag_input.press("Enter")

    # ─── Удобные ожидания ─────────────────────────────────────────────────
    def expect_active_count(self, n: int) -> None:
        expect(self.page.locator("#tab-active-count")).to_have_text(str(n))

    def expect_archive_count(self, n: int) -> None:
        expect(self.page.locator("#tab-archive-count")).to_have_text(str(n))

    def expect_zone_count(self, zone: str, n: int) -> None:
        expect(self.page.locator(f"#zone-badge-{zone}")).to_have_text(str(n))

    def expect_error_message(self, substring: str) -> None:
        expect(self.name_error).to_be_visible()
        expect(self.name_error).to_contain_text(substring)
