import asyncio

from app.services.local_parser import LocalExpenseParser, determine_category


def test_online_order_keywords_map_to_online_order() -> None:
    assert determine_category("Blinkit") == "Online Order"
    assert determine_category("Zomato") == "Online Order"
    assert determine_category("Swiggy") == "Online Order"
    assert determine_category("Online Order") == "Online Order"


def test_online_order_keywords_take_precedence_over_other_categories() -> None:
    assert determine_category("Blinkit Food") == "Online Order"
    assert determine_category("Blinkit Online Order") == "Online Order"
    assert determine_category("Zomato Lunch") == "Online Order"
    assert determine_category("Zepto") == "Online Order"


def test_parser_preserves_online_order_category_for_expenses() -> None:
    parser = LocalExpenseParser()

    parsed = asyncio.run(parser.parse("Swiggy 249"))

    assert parsed is not None
    assert parsed.category == "Online Order"
    assert parsed.item == "Swiggy"