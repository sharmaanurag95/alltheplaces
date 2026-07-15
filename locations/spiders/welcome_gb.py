from typing import Iterable

from scrapy.http import Response

from locations.categories import Categories, apply_category
from locations.items import Feature
from locations.storefinders.uberall import UberallSpider


class WelcomeGBSpider(UberallSpider):
    name = "welcome_gb"
    item_attributes = {"brand": "Welcome", "brand_wikidata": "Q123004215"}
    # Southern Co-op store locator, which also lists their Co-op branded stores.
    key = "uvMckoaRcAUKR0LkkH03SVNyf7A4Lk"

    def post_process_item(self, item: Feature, response: Response, location: dict) -> Iterable[Feature]:
        if not location["name"].lower().startswith("welcome"):
            return
        apply_category(Categories.SHOP_CONVENIENCE, item)
        yield item
