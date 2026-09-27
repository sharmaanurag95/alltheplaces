import json
import re
from collections import Counter
from typing import Iterable

from scrapy import Request, Spider
from scrapy.http import Response
from twisted.python.failure import Failure

from locations.categories import Categories, apply_category
from locations.items import Feature
from locations.linked_data_parser import LinkedDataParser


class ArqlineUSSpider(Spider):
    """Arqline is the 2025 merger of Quarterra Living, RKW Residential and Alfred."""

    name = "arqline_us"
    item_attributes = {"operator": "Arqline"}
    start_urls = ["https://arqline.com/"]

    def parse(self, response: Response) -> Iterable[Request]:
        yield response.follow(response.xpath('//script[@type="module"]/@src').get(), callback=self.parse_bundle)

    def parse_bundle(self, response: Response) -> Iterable[Feature | Request]:
        properties = json.loads(re.search(r"JSON\.parse\(`(\[\{\"id\".+?\])`\)", response.text).group(1))
        site_counts = Counter(prop["marketingSite"] for prop in properties)
        for prop in properties:
            item = Feature()
            item["ref"] = prop["id"]
            item["name"] = prop["title"]
            item["city"] = prop["city"]
            item["state"] = prop["state"]
            item["website"] = prop["marketingSite"]
            item["image"] = response.urljoin(prop["images"][0])
            apply_category(Categories.RESIDENTIAL_APARTMENTS, item)
            # A site shared by several buildings only describes one of them
            if site_counts[prop["marketingSite"]] > 1:
                yield item
            else:
                yield Request(
                    prop["marketingSite"],
                    callback=self.parse_property,
                    errback=self.errback_property,
                    cb_kwargs={"item": item},
                )

    def parse_property(self, response: Response, item: Feature) -> Iterable[Feature]:
        # Most sites serve a JS bot check instead of the page; keep the listing data for those
        if ld := LinkedDataParser.find_linked_data(response, "LocalBusiness"):
            ld_item = LinkedDataParser.parse_ld(ld)
            for key in ("lat", "lon", "street_address", "postcode", "phone"):
                if ld_item.get(key):
                    item[key] = ld_item[key]
        yield item

    def errback_property(self, failure: Failure) -> Iterable[Feature]:
        yield failure.request.cb_kwargs["item"]
