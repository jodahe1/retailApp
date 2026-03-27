import logging
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import transactional_session
from app.exceptions.base import ConflictException, NotFoundException, SecurityException, ValidationException
from app.models.identity import User
from app.models.product import Product
from app.schemas.product import (
    AddToCartRequest,
    PreCheckoutItem,
    ProductCreateRequest,
    ProductQuickMatchItem,
    ProductSearchResponse,
    ProductStatusUpdateRequest,
)
from app.security.product_policy import ProductPolicy, ProductScopeContext

logger = logging.getLogger(__name__)


class FailedScanReason:
    INVALID_QUERY = "invalid_query"
    PRODUCT_NOT_FOUND = "product_not_found"
    INACTIVE_PRODUCT = "inactive_product"
    UNAVAILABLE_PRODUCT = "unavailable_product"
    SCOPE_DENIED = "scope_denied"



def _normalize(value: str) -> str:
    return value.strip()


def _permission_codes(actor: User) -> set[str]:
    return {perm.code for role in actor.roles for perm in role.permissions}


def _scope_context(actor: User) -> ProductScopeContext:
    return ProductScopeContext(
        actor_user_id=actor.id,
        actor_is_superuser=actor.is_superuser,
        actor_permissions=_permission_codes(actor),
    )


def _to_response(product: Product) -> ProductSearchResponse:
    return ProductSearchResponse(
        id=product.id,
        name=product.name,
        name_pinyin=product.name_pinyin,
        barcode=product.barcode,
        internal_code=product.internal_code,
        unit_price=product.unit_price,
        is_active=product.is_active,
        is_available_for_sale=product.is_available_for_sale,
        is_pos_visible=product.is_pos_visible,
    )


def create_product(db: Session, payload: ProductCreateRequest, actor: User) -> Product:
    product = Product(
        name=payload.name.strip(),
        name_pinyin=payload.name_pinyin.strip().lower(),
        barcode=payload.barcode.strip(),
        internal_code=payload.internal_code.strip(),
        unit_price=payload.unit_price,
        is_active=True,
        is_deleted=False,
        is_available_for_sale=payload.is_available_for_sale,
        is_pos_visible=payload.is_pos_visible,
    )

    try:
        with transactional_session(db):
            db.add(product)
            db.flush()
    except IntegrityError as exc:
        logger.warning("product_create_conflict actor_user_id=%s", actor.id)
        raise ConflictException("Product barcode or internal code already exists") from exc

    return product


def _log_failed_scan(*, actor: User | None, query: str, reason: str) -> None:
    logger.warning(
        "product_scan_failed actor_user_id=%s reason=%s query=%s",
        actor.id if actor else None,
        reason,
        query,
    )


def find_product_by_query(
    db: Session,
    *,
    query: str,
    actor: User | None = None,
    allow_inactive: bool = False,
) -> Product:
    cleaned = _normalize(query)
    if not cleaned:
        _log_failed_scan(actor=actor, query=query, reason=FailedScanReason.INVALID_QUERY)
        raise ValidationException("Product query cannot be empty")

    product = db.scalar(
        select(Product).where(
            or_(
                Product.barcode == cleaned,
                Product.internal_code == cleaned,
                Product.name_pinyin == cleaned.lower(),
            )
        )
    )

    if product is None:
        _log_failed_scan(actor=actor, query=cleaned, reason=FailedScanReason.PRODUCT_NOT_FOUND)
        raise NotFoundException("Product not found")

    if not allow_inactive and (not product.is_active or product.is_deleted):
        _log_failed_scan(actor=actor, query=cleaned, reason=FailedScanReason.INACTIVE_PRODUCT)
        raise SecurityException("Product is inactive and cannot be used")

    return product


def quick_match_products(db: Session, *, query: str, limit: int = 10) -> list[ProductQuickMatchItem]:
    cleaned = _normalize(query)
    if not cleaned:
        raise ValidationException("Query cannot be empty")

    pattern = f"%{cleaned.lower()}%"
    stmt = (
        select(Product)
        .where(
            Product.is_active.is_(True),
            Product.is_deleted.is_(False),
            Product.is_pos_visible.is_(True),
            or_(
                Product.barcode == cleaned,
                Product.internal_code == cleaned,
                Product.name_pinyin.like(pattern),
            ),
        )
        .order_by(Product.name.asc())
        .limit(limit)
    )

    products = db.scalars(stmt).all()
    return [
        ProductQuickMatchItem(
            id=p.id,
            name=p.name,
            barcode=p.barcode,
            internal_code=p.internal_code,
            unit_price=p.unit_price,
        )
        for p in products
    ]


def retrieve_product(db: Session, *, query: str, actor: User) -> ProductSearchResponse:
    product = find_product_by_query(db, query=query, actor=actor)

    context = _scope_context(actor)
    if not ProductPolicy.can_access_store_product(context, store_id=None):
        _log_failed_scan(actor=actor, query=query, reason=FailedScanReason.SCOPE_DENIED)
        raise SecurityException("Product access denied by scope policy")

    return _to_response(product)


def build_precheckout_item(db: Session, *, actor: User, payload: AddToCartRequest) -> PreCheckoutItem:
    product = find_product_by_query(db, query=payload.query, actor=actor)

    context = _scope_context(actor)
    if not ProductPolicy.can_access_store_product(context, store_id=None):
        _log_failed_scan(actor=actor, query=payload.query, reason=FailedScanReason.SCOPE_DENIED)
        raise SecurityException("Product access denied by scope policy")

    if not product.is_available_for_sale:
        _log_failed_scan(actor=actor, query=payload.query, reason=FailedScanReason.UNAVAILABLE_PRODUCT)
        raise SecurityException("Product is not available for sale")

    if not product.is_pos_visible:
        _log_failed_scan(actor=actor, query=payload.query, reason=FailedScanReason.UNAVAILABLE_PRODUCT)
        raise SecurityException("Product is not visible in POS")

    line_total = Decimal(product.unit_price) * Decimal(payload.quantity)
    return PreCheckoutItem(
        product_id=product.id,
        barcode=product.barcode,
        internal_code=product.internal_code,
        name=product.name,
        quantity=payload.quantity,
        unit_price=product.unit_price,
        line_total=line_total,
    )


def update_product_status(
    db: Session,
    *,
    product_id: int,
    payload: ProductStatusUpdateRequest,
) -> ProductSearchResponse:
    product = db.get(Product, product_id)
    if product is None:
        raise NotFoundException("Product not found")

    with transactional_session(db):
        if payload.is_active is not None:
            product.is_active = payload.is_active
            if not payload.is_active:
                product.is_deleted = False
        if payload.is_available_for_sale is not None:
            product.is_available_for_sale = payload.is_available_for_sale
        if payload.is_pos_visible is not None:
            product.is_pos_visible = payload.is_pos_visible

    return _to_response(product)
