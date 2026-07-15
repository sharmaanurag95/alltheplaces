import json
from typing import Iterable

from scrapy.http import Response, TextResponse

from locations.hours import OpeningHours
from locations.items import Feature
from locations.json_blob_spider import JSONBlobSpider
from locations.pipelines.address_clean_up import merge_address_lines
from locations.playwright_spider import PlaywrightSpider
from locations.settings import DEFAULT_PLAYWRIGHT_SETTINGS
from locations.user_agents import FIREFOX_LATEST


class TheEntertainerGBSpider(JSONBlobSpider, PlaywrightSpider):
    name = "the_entertainer_gb"
    item_attributes = {"brand": "The Entertainer", "brand_wikidata": "Q7732289"}
    start_urls = [
        "https://www.thetoyshop.com/api/occ/v2/thetoyshop/stores?accuracy=0&currentPage=0&fields=FULL&pageSize=1200&query=doncaster&storeType=ALL&radius=10000000&sort=asc&format=json"
    ]
    locations_key = ["stores"]
    # Akamai blocks non-browser TLS fingerprints with a 403.
    custom_settings = DEFAULT_PLAYWRIGHT_SETTINGS | {"ROBOTSTXT_OBEY": False, "USER_AGENT": FIREFOX_LATEST}

    def extract_json(self, response: TextResponse) -> dict | list[dict]:
        return json.loads(response.xpath("//pre/text()").get())["stores"]

    def post_process_item(self, item: Feature, response: Response, feature: dict) -> Iterable[Feature]:
        item["ref"] = feature["address"]["id"]
        item["website"] = "https://www.thetoyshop.com/store/" + feature["name"].lower().replace(" ", "-")
        item["street_address"] = merge_address_lines([feature["address"].get("line1"), feature["address"].get("line2")])
        item["phone"] = feature["address"].get("phone")
        item["branch"] = item.pop("name")
        item["opening_hours"] = self.parse_opening_hours(feature["openingHours"]["weekDayOpeningList"])
        if "tesco" in item["website"]:
            return
            # item["located_in"] = "Tesco"
            # item["located_in_wikidata"] = "Q487494"
        yield item

    def parse_opening_hours(self, rules: list[dict]) -> OpeningHours:
        opening_hours = OpeningHours()
        for rule in rules:
            if rule.get("closed") is True:
                opening_hours.set_closed(rule["weekDay"])
            else:
                opening_hours.add_range(
                    rule["weekDay"], rule["openingTime"]["formattedHour"], rule["closingTime"]["formattedHour"]
                )
        return opening_hours
