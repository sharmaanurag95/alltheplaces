from typing import Iterable

from chompjs import parse_js_object
from scrapy import Spider
from scrapy.http import Response

from locations.dict_parser import DictParser
from locations.items import Feature
from locations.user_agents import BROWSER_DEFAULT


class SweetfrogUSSpider(Spider):
    name = "sweetfrog_us"
    item_attributes = {"brand": "sweetFrog", "brand_wikidata": "Q16952110"}
    allowed_domains = ["locator.kahalamgmt.com"]
    start_urls = ["https://locator.kahalamgmt.com/locator/index.php?mode=desktop&brand=38"]
    custom_settings = {"ROBOTSTXT_OBEY": False, "USER_AGENT": BROWSER_DEFAULT}

    def parse(self, response: Response) -> Iterable[Feature]:
        locator_js_blob = response.xpath('//script[contains(text(), "Locator.stores[0] = ")]/text()').get()
        for location_js_blob in filter(lambda x: "Locator.stores" in x, locator_js_blob.splitlines()):
            location = parse_js_object(location_js_blob.split(" = ", 1)[1])
            if location["StoreStatusId"] != "O":  # Skip locations not currently open
                continue
            item = DictParser.parse(location)
            item["branch"] = item.pop("name")
            item["street_address"] = item.pop("addr_full")
            item["website"] = "https://www.sweetfrog.com/stores/frozen-yogurt-{}/{}".format(
                location["cleanCity"], location["StoreId"]
            )
            yield item
