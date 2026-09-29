import re
from copy import deepcopy
from typing import AsyncIterator, Iterable

from scrapy.http import JsonRequest, Response

from locations.categories import Categories, apply_category
from locations.hours import DAYS, OpeningHours
from locations.items import Feature
from locations.json_blob_spider import JSONBlobSpider


class RednersUSSpider(JSONBlobSpider):
    name = "redners_us"
    item_attributes = {"brand": "Redner's", "brand_wikidata": "Q7306166"}
    allowed_domains = ["rednersmarkets.alwaysongrocery.net"]
    start_urls = ["https://rednersmarkets.alwaysongrocery.net/cms/api/v1/AogGetStoreList"]
    locations_key = "data"

    async def start(self) -> AsyncIterator[JsonRequest]:
        yield JsonRequest(url=self.start_urls[0], data={"RSAClientId": "323"})

    def post_process_item(self, item: Feature, response: Response, feature: dict) -> Iterable[Feature]:
        item["ref"] = feature["store_id"]
        item["branch"] = re.sub(r"\s*#\s*\d+$", "", feature["ClientStoreName"])
        item["phone"] = feature["StorePhoneNumber"]

        item["opening_hours"] = OpeningHours()
        if "24 HOURS" in feature["StoreTimings"].upper():
            item["opening_hours"].add_days_range(DAYS, "00:00", "23:59")
        else:
            item["opening_hours"].add_ranges_from_string(feature["StoreTimings"])

        if "Quick" in feature["ClientStoreName"]:
            item["brand"] = item["name"] = "Redner's Quick Shoppe"
            item["brand_wikidata"] = "Q125102841"
            convenience_store = deepcopy(item)
            convenience_store["ref"] += "-convenience"
            apply_category(Categories.SHOP_CONVENIENCE, convenience_store)
            yield convenience_store
            item["ref"] += "-fuel"
            apply_category(Categories.FUEL_STATION, item)
        else:
            apply_category(Categories.SHOP_SUPERMARKET, item)

        yield item
