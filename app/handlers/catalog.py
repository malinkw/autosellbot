"""Каталог: просмотр категорий, товаров, поиск и покупка."""

from __future__ import annotations

import uuid

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.states import CatalogSearch
from app.handlers.texts import product_card_text
from app.keyboards.callbacks import CatalogCB, MenuCB
from app.keyboards.user import categories_kb, product_card_kb, products_kb
from app.models import User
from app.permissions import Permission
from app.services import ServiceContainer
from app.utils.formatting import money

router = Router(name="catalog")


async def _render_root(message: Message, services: ServiceContainer) -> None:
    categories = await services.catalog.root_categories()
    if not categories:
        await message.edit_text("Каталог пока пуст.", reply_markup=categories_kb([]))
        return
    await message.edit_text(
        "🛍 <b>Каталог</b>\nВыберите категорию:", reply_markup=categories_kb(categories)
    )


@router.callback_query(MenuCB.filter(F.action == "catalog"))
@router.callback_query(CatalogCB.filter(F.action == "root"))
async def show_root(callback: CallbackQuery, services: ServiceContainer) -> None:
    """Показать корневые категории."""
    if isinstance(callback.message, Message):
        await _render_root(callback.message, services)
    await callback.answer()


@router.callback_query(CatalogCB.filter(F.action == "open"))
async def open_category(
    callback: CallbackQuery, callback_data: CatalogCB, services: ServiceContainer
) -> None:
    """Открыть категорию: показать подкатегории или товары."""
    category_id = uuid.UUID(callback_data.id)
    subcategories = await services.catalog.subcategories(category_id)
    if subcategories:
        await callback.message.edit_text(
            "📂 Подкатегории:", reply_markup=categories_kb(subcategories)
        )
        await callback.answer()
        return
    products = await services.catalog.products(category_id)
    if not products:
        await callback.answer("В этой категории пока нет товаров.", show_alert=True)
        return
    await callback.message.edit_text("🛒 Товары:", reply_markup=products_kb(products))
    await callback.answer()


@router.callback_query(CatalogCB.filter(F.action == "product"))
async def show_product(
    callback: CallbackQuery, callback_data: CatalogCB, services: ServiceContainer
) -> None:
    """Показать карточку товара."""
    product = await services.catalog.get_product(uuid.UUID(callback_data.id))
    stock = await services.catalog.product_stock(product.id)
    await callback.message.edit_text(
        product_card_text(product, stock=stock),
        reply_markup=product_card_kb(product, in_stock=stock > 0),
    )
    await callback.answer()


@router.callback_query(CatalogCB.filter(F.action == "buy"))
async def buy_product(
    callback: CallbackQuery,
    callback_data: CatalogCB,
    user: User,
    services: ServiceContainer,
) -> None:
    """Купить товар: списать баланс и выдать содержимое позиции."""
    # Защита от двойного нажатия (Replay/двойной клик).
    if not await services.idempotency.acquire(f"buy:{user.id}:{callback_data.id}", ttl=5):
        await callback.answer("Обрабатываем предыдущий запрос…", show_alert=False)
        return

    product_id = uuid.UUID(callback_data.id)
    result = await services.orders.purchase(user, product_id)
    await services.audit.record(
        "order.purchase",
        actor=user,
        channel="payments",
        entity_type="order",
        entity_id=result.order.id,
        new_data={"amount": str(result.order.amount), "product": str(product_id)},
    )

    await callback.message.answer(
        f"✅ Оплачено {money(result.order.amount)}.\n"
        f"Заказ <b>{result.order.number}</b>.\n\n"
        f"<b>Ваш товар:</b>\n<code>{result.content}</code>"
    )
    await callback.answer("Покупка совершена!")

    # Уведомление сотрудников о новом заказе.
    staff = await services.users.staff_with_permission(Permission.ORDERS_VIEW.value)
    await services.notifications.broadcast(
        staff, f"🆕 Новый заказ {result.order.number} на {money(result.order.amount)}."
    )


@router.callback_query(CatalogCB.filter(F.action == "search"))
async def ask_search(callback: CallbackQuery, state: FSMContext) -> None:
    """Запросить поисковый запрос."""
    await state.set_state(CatalogSearch.query)
    await callback.message.answer("🔍 Введите название товара:")
    await callback.answer()


@router.message(CatalogSearch.query)
async def do_search(message: Message, state: FSMContext, services: ServiceContainer) -> None:
    """Выполнить поиск товаров по запросу."""
    await state.clear()
    products = await services.catalog.search_products(message.text or "")
    if not products:
        await message.answer("Ничего не найдено.")
        return
    await message.answer("Результаты поиска:", reply_markup=products_kb(products))
