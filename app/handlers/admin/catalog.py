"""Админ: управление категориями и товарами."""

from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.states import CategoryForm, ProductForm
from app.handlers.admin.common import edit
from app.keyboards.callbacks import AdminCB, MenuCB
from app.models import User
from app.permissions import Permission
from app.services import ServiceContainer
from app.utils.formatting import money

router = Router(name="admin_catalog")


# =========================== Категории ======================================
@router.callback_query(AdminCB.filter((F.section == "categories") & (F.action == "open")))
async def categories_list(callback: CallbackQuery, user: User, services: ServiceContainer) -> None:
    """Список категорий."""
    services.permissions.require(user, Permission.CATEGORIES_VIEW)
    categories = await services.catalog.root_categories(admin=True)
    builder = InlineKeyboardBuilder()
    for cat in categories:
        mark = "🟢" if cat.is_enabled else "🔴"
        builder.button(
            text=f"{mark} {cat.name}",
            callback_data=AdminCB(section="categories", action="view", id=str(cat.id)),
        )
    if services.permissions.has_permission(user, Permission.CATEGORIES_CREATE):
        builder.button(
            text="➕ Создать", callback_data=AdminCB(section="categories", action="create")
        )
    builder.button(text="⬅️ Админ-панель", callback_data=MenuCB(action="admin"))
    builder.adjust(1)
    await edit(callback, "📂 <b>Категории</b>", builder.as_markup())


@router.callback_query(AdminCB.filter((F.section == "categories") & (F.action == "create")))
async def category_create_start(
    callback: CallbackQuery, user: User, services: ServiceContainer, state: FSMContext
) -> None:
    """Начать создание категории."""
    services.permissions.require(user, Permission.CATEGORIES_CREATE)
    await state.set_state(CategoryForm.name)
    await callback.message.answer("Название категории:")
    await callback.answer()


@router.message(CategoryForm.name)
async def category_create_finish(
    message: Message, state: FSMContext, user: User, services: ServiceContainer
) -> None:
    """Создать категорию."""
    services.permissions.require(user, Permission.CATEGORIES_CREATE)
    await state.clear()
    category = await services.catalog.create_category(message.text or "")
    await services.audit.record(
        "category.create", actor=user, entity_type="category", entity_id=category.id
    )
    await message.answer(f"✅ Категория «{category.name}» создана.")


@router.callback_query(AdminCB.filter((F.section == "categories") & (F.action == "view")))
async def category_view(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Карточка категории."""
    services.permissions.require(user, Permission.CATEGORIES_VIEW)
    category = await services.catalog.get_category(uuid.UUID(callback_data.id))
    builder = InlineKeyboardBuilder()
    if category.is_enabled:
        builder.button(
            text="🔴 Отключить",
            callback_data=AdminCB(section="categories", action="disable", id=str(category.id)),
        )
    else:
        builder.button(
            text="🟢 Включить",
            callback_data=AdminCB(section="categories", action="enable", id=str(category.id)),
        )
    builder.button(
        text="➕ Товар", callback_data=AdminCB(section="catalog", action="add", id=str(category.id))
    )
    builder.button(
        text="🗑 Удалить",
        callback_data=AdminCB(section="categories", action="delete", id=str(category.id)),
    )
    builder.button(text="⬅️ К категориям", callback_data=AdminCB(section="categories"))
    builder.adjust(2, 1, 1)
    await edit(
        callback,
        f"📂 <b>{category.name}</b>\nВключена: {'да' if category.is_enabled else 'нет'}",
        builder.as_markup(),
    )


@router.callback_query(
    AdminCB.filter((F.section == "categories") & (F.action.in_({"enable", "disable"})))
)
async def category_toggle(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Включить/отключить категорию."""
    enable = callback_data.action == "enable"
    services.permissions.require(
        user, Permission.CATEGORIES_ENABLE if enable else Permission.CATEGORIES_DISABLE
    )
    await services.catalog.set_category_enabled(uuid.UUID(callback_data.id), enable)
    await services.audit.record(
        f"category.{callback_data.action}",
        actor=user,
        entity_type="category",
        entity_id=callback_data.id,
    )
    await category_view(callback, callback_data, user, services)


@router.callback_query(AdminCB.filter((F.section == "categories") & (F.action == "delete")))
async def category_delete(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Удалить категорию."""
    services.permissions.require(user, Permission.CATEGORIES_DELETE)
    await services.catalog.delete_category(uuid.UUID(callback_data.id))
    await services.audit.record(
        "category.delete", actor=user, entity_type="category", entity_id=callback_data.id
    )
    await callback.answer("Категория удалена.", show_alert=True)
    await categories_list(callback, user, services)


# =========================== Товары =========================================
@router.callback_query(AdminCB.filter((F.section == "catalog") & (F.action == "open")))
async def products_list(callback: CallbackQuery, user: User, services: ServiceContainer) -> None:
    """Список всех товаров."""
    services.permissions.require(user, Permission.PRODUCTS_VIEW)
    products = await services.catalog.all_products()
    builder = InlineKeyboardBuilder()
    for product in products:
        builder.button(
            text=f"🛒 {product.name} · {money(product.price)}",
            callback_data=AdminCB(section="catalog", action="view", id=str(product.id)),
        )
    builder.button(text="⬅️ Админ-панель", callback_data=MenuCB(action="admin"))
    builder.adjust(1)
    await edit(callback, "🛍 <b>Товары</b>", builder.as_markup())


@router.callback_query(AdminCB.filter((F.section == "catalog") & (F.action == "add")))
async def product_add_start(
    callback: CallbackQuery,
    callback_data: AdminCB,
    user: User,
    services: ServiceContainer,
    state: FSMContext,
) -> None:
    """Начать создание товара в категории."""
    services.permissions.require(user, Permission.PRODUCTS_CREATE)
    await state.set_state(ProductForm.name)
    await state.update_data(category_id=callback_data.id or None)
    await callback.message.answer("Название товара:")
    await callback.answer()


@router.message(ProductForm.name)
async def product_name(message: Message, state: FSMContext) -> None:
    """Принять название товара."""
    await state.update_data(name=message.text or "")
    await state.set_state(ProductForm.price)
    await message.answer("Цена товара:")


@router.message(ProductForm.price)
async def product_price(message: Message, state: FSMContext) -> None:
    """Принять цену товара."""
    try:
        price = Decimal((message.text or "").replace(",", ".").strip())
    except (InvalidOperation, ValueError):
        await message.answer("Введите корректную цену числом.")
        return
    await state.update_data(price=str(price))
    await state.set_state(ProductForm.description)
    await message.answer("Описание товара (или «-»):")


@router.message(ProductForm.description)
async def product_finish(
    message: Message, state: FSMContext, user: User, services: ServiceContainer
) -> None:
    """Создать товар."""
    services.permissions.require(user, Permission.PRODUCTS_CREATE)
    data = await state.get_data()
    await state.clear()
    description = (message.text or "").strip()
    category_id = uuid.UUID(data["category_id"]) if data.get("category_id") else None
    product = await services.catalog.create_product(
        data["name"],
        Decimal(data["price"]),
        category_id=category_id,
        description=None if description in {"", "-"} else description,
    )
    await services.audit.record(
        "product.create", actor=user, entity_type="product", entity_id=product.id
    )
    await message.answer(f"✅ Товар «{product.name}» создан.")


@router.callback_query(AdminCB.filter((F.section == "catalog") & (F.action == "view")))
async def product_view(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Карточка товара с действиями."""
    services.permissions.require(user, Permission.PRODUCTS_VIEW)
    product = await services.catalog.get_product(uuid.UUID(callback_data.id))
    stock = await services.catalog.product_stock(product.id)
    builder = InlineKeyboardBuilder()
    builder.button(
        text=("👁 Показать" if product.is_hidden else "🙈 Скрыть"),
        callback_data=AdminCB(section="catalog", action="hide", id=str(product.id)),
    )
    builder.button(
        text=("📦 Разархив." if product.is_archived else "🗄 Архив"),
        callback_data=AdminCB(section="catalog", action="archive", id=str(product.id)),
    )
    builder.button(
        text="🗑 Удалить",
        callback_data=AdminCB(section="catalog", action="delete", id=str(product.id)),
    )
    builder.button(text="⬅️ К товарам", callback_data=AdminCB(section="catalog"))
    builder.adjust(2, 1, 1)
    text = (
        f"🛒 <b>{product.name}</b>\nЦена: {money(product.price)}\n"
        f"Наличие: {stock}\nСкрыт: {'да' if product.is_hidden else 'нет'}\n"
        f"В архиве: {'да' if product.is_archived else 'нет'}"
    )
    await edit(callback, text, builder.as_markup())


@router.callback_query(AdminCB.filter((F.section == "catalog") & (F.action == "hide")))
async def product_hide(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Скрыть/показать товар."""
    services.permissions.require(user, Permission.PRODUCTS_HIDE)
    product = await services.catalog.get_product(uuid.UUID(callback_data.id))
    await services.catalog.update_product(product.id, is_hidden=not product.is_hidden)
    await services.audit.record(
        "product.hide", actor=user, entity_type="product", entity_id=product.id
    )
    await product_view(callback, callback_data, user, services)


@router.callback_query(AdminCB.filter((F.section == "catalog") & (F.action == "archive")))
async def product_archive(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Архивировать/разархивировать товар."""
    services.permissions.require(user, Permission.PRODUCTS_ARCHIVE)
    product = await services.catalog.get_product(uuid.UUID(callback_data.id))
    await services.catalog.update_product(product.id, is_archived=not product.is_archived)
    await services.audit.record(
        "product.archive", actor=user, entity_type="product", entity_id=product.id
    )
    await product_view(callback, callback_data, user, services)


@router.callback_query(AdminCB.filter((F.section == "catalog") & (F.action == "delete")))
async def product_delete(
    callback: CallbackQuery, callback_data: AdminCB, user: User, services: ServiceContainer
) -> None:
    """Удалить товар."""
    services.permissions.require(user, Permission.PRODUCTS_DELETE)
    await services.catalog.delete_product(uuid.UUID(callback_data.id))
    await services.audit.record(
        "product.delete", actor=user, entity_type="product", entity_id=callback_data.id
    )
    await callback.answer("Товар удалён.", show_alert=True)
    await products_list(callback, user, services)
