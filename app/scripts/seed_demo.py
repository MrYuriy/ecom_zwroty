"""Fill a dev database with demo SKUs and returns: python -m app.scripts.seed_demo [--force].

Includes the rows of the sample returns report, so an export can be compared against it.
Never run against production.
"""

import argparse
import asyncio
import random
from datetime import date, datetime, timedelta

from sqlalchemy import func, select

from app.database.postgres import async_session
from app.enums.return_order import CarrierType, GoodsCondition, ReturnStatus
from app.enums.user import RoleEnum
from app.models import OrderLine, ReturnOrder, Sku, SkuEan, User

P, L = CarrierType.PARCEL, CarrierType.PALLET
D, F = GoodsCondition.DAMAGED, GoodsCondition.FULL_VALUE

# (trade_reference, product_name, is_parametrized)
SKUS = [
    ("45783276", "Lampa stołowa LED Nordic", True),
    ("45779783", "Lampa wisząca Loft 3-pkt", True),
    ("82376357", "Dysk zewnętrzny 1TB USB-C", True),
    ("92716869", "Krzesło biurowe Ergo Pro", True),
    ("82369118", "Szklany blat stolika 80x80", True),
    ("80053071", "Umywalka ceramiczna 60 cm", True),
    ("89322996", "Szafa przesuwna 180 cm", True),
    ("45302250", "Regał metalowy 5 półek", True),
    ("92586564", "Panel podłogowy dąb (op.)", True),
    ("95485998", "Płytka gresowa 60x60 (op.)", True),
    ("45603124", "Zestaw śrub montażowych", False),
    ("89082264", "Bateria umywalkowa chrom", True),
    ("91506593", "Deska sedesowa wolnoopadająca", True),
    ("91506633", "Kabina prysznicowa 90x90", True),
    ("93998031", "Blat kuchenny 240 cm", True),
    ("45824821", "Lustro łazienkowe LED 60 cm", True),
    ("47110001", "Wiertarko-wkrętarka 18V", True),
    ("47110002", "Farba ścienna biała 10 l", False),
    ("47110003", "Klej do płytek 25 kg", False),
    ("47110004", "Drzwi wewnętrzne 80 prawe", True),
    ("47110005", "Grzejnik łazienkowy drabinka", True),
    ("47110006", "Taśma malarska 48 mm", False),
]

# Rows of the sample report: (date, BO/WMS, Tempo, reference, remarks, qty, carrier, condition, damage)
SAMPLE_ROWS = [
    ("2026-01-02", None, None, "45783276", "etykieta na @", 1, P, D, "rogi"),
    ("2026-01-02", None, None, "45779783", "etykieta na @", 1, P, D, "rogi"),
    ("2026-01-02", "356902", "25343L5901", "82376357", "dysk", 1, P, D, "rogi"),
    ("2026-01-02", "361852", "25354L20536", "92716869", None, 1, P, D, "złamane"),
    ("2026-01-02", "359048", "25348L2938", "82369118", None, 1, P, D, "pęknięta"),
    ("2026-01-02", "500341", None, "80053071", "odstąpienie na @", 1, P, D, "pęknięty"),
    ("2026-01-05", "361957", "25355L36", "89322996", None, 1, L, F, None),
    ("2026-01-05", None, None, "45302250", None, 1, L, F, None),
    ("2026-01-05", "363775", "25363L21171", "92586564", None, 15, L, F, None),
    ("2026-01-05", "363901", "25363L35945", "95485998", None, 3, L, F, None),
    ("2026-01-05", None, None, "45603124", "odstąpienie na @", 1, P, F, None),
    ("2026-01-05", "358680", "25347L2114", "89082264", None, 1, P, F, None),
    ("2026-01-05", "353370", "25334L63070", "91506593", "odstąpienie na @", 1, P, F, None),
    ("2026-01-05", "362147", "25355L28017", "91506633", "odstąpienie na @", 1, P, D, "używane"),
    ("2026-01-05", "363121", "25361L30047", "93998031", None, 1, P, D, "porysowane"),
    ("2026-01-05", None, None, "45824821", None, 1, P, D, "porysowane"),
]

DAMAGES = ["rogi", "pęknięte", "porysowane", "złamane", "wgniecione", "używane", "brak elementów"]
REMARKS = ["etykieta na @", "odstąpienie na @", "reklamacja", "brak paragonu"]


def ean13(reference: str) -> str:
    """Fake but valid EAN-13 (Polish 590 prefix + reference + check digit)."""
    body = ("590" + reference)[:12].ljust(12, "0")
    total = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(body))
    return body + str((10 - total % 10) % 10)


async def seed(force: bool) -> None:
    rng = random.Random(42)
    async with async_session() as session:
        operator = (
            await session.execute(select(User).where(User.role == RoleEnum.ADMIN).order_by(User.id).limit(1))
        ).scalar_one_or_none()
        if not operator:
            raise SystemExit("No ADMIN user — run app.scripts.create_admin first.")

        existing_orders = (await session.execute(select(func.count()).select_from(ReturnOrder))).scalar()
        if existing_orders and not force:
            raise SystemExit(f"{existing_orders} return orders already exist — pass --force to add demo data anyway.")

        skus: dict[str, Sku] = {}
        for reference, name, parametrized in SKUS:
            sku = (await session.execute(select(Sku).where(Sku.trade_reference == reference))).scalar_one_or_none()
            if not sku:
                sku = Sku(
                    trade_reference=reference,
                    eans=[SkuEan(ean=ean13(reference))],
                    product_name=name,
                    is_parametrized=parametrized,
                )
                session.add(sku)
            skus[reference] = sku
        await session.flush()

        def add_order(return_date: date, bo: str | None, tempo: str | None) -> ReturnOrder:
            # Past returns are finished (closed, ready for the report); today's are still being received.
            closed = return_date < date.today()
            order = ReturnOrder(
                bo_wms_number=bo,
                tempo_number=tempo,
                return_date=return_date,
                operator_id=operator.id,
                status=ReturnStatus.CLOSED if closed else ReturnStatus.OPEN,
                closed_at=datetime.now() if closed else None,
            )
            session.add(order)
            return order

        for day, bo, tempo, reference, remarks, qty, carrier, condition, damage in SAMPLE_ROWS:
            order = add_order(date.fromisoformat(day), bo, tempo)
            order.lines.append(
                OrderLine(
                    sku=skus[reference],
                    quantity=qty,
                    carrier_type=carrier,
                    goods_condition=condition,
                    damage_description=damage,
                    remarks=remarks,
                )
            )

        references = list(skus)
        today = date.today()
        for _ in range(25):
            has_numbers = rng.random() > 0.2
            order = add_order(
                today - timedelta(days=rng.randint(0, 13)),
                str(rng.randint(350000, 369999)) if has_numbers else None,
                f"25{rng.randint(300, 365)}L{rng.randint(1, 40000)}" if has_numbers and rng.random() > 0.15 else None,
            )
            carrier = L if rng.random() < 0.2 else P
            for reference in rng.sample(references, rng.randint(1, 4)):
                damaged = rng.random() < 0.45
                order.lines.append(
                    OrderLine(
                        sku=skus[reference],
                        quantity=rng.randint(2, 12) if carrier is L else 1,
                        carrier_type=carrier,
                        goods_condition=D if damaged else F,
                        damage_description=rng.choice(DAMAGES) if damaged else None,
                        remarks=rng.choice(REMARKS) if rng.random() < 0.3 else None,
                    )
                )

        await session.commit()

    print(f"Seeded {len(SKUS)} SKUs, {len(SAMPLE_ROWS)} sample-report returns and 25 random returns.")
    print("EANs to try in the scanner field:")
    for reference in ("82376357", "92716869", "45603124"):
        print(f"  {ean13(reference)}  ({reference})")
    print("Unknown EAN (opens the new-product form): 5909999999993")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fill a dev database with demo returns.")
    parser.add_argument("--force", action="store_true", help="add demo data even if returns already exist")
    asyncio.run(seed(parser.parse_args().force))


if __name__ == "__main__":
    main()
