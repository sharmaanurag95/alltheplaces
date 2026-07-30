from typing import Iterable

from scrapy.http import TextResponse
from scrapy.spiders import SitemapSpider

from locations.categories import Categories, Clothes, apply_category, apply_clothes
from locations.items import Feature
from locations.structured_data_spider import StructuredDataSpider


class VictoriassecretSpider(SitemapSpider, StructuredDataSpider):
    name = "victoriassecret"
    item_attributes = {"brand": "Victoria's Secret", "brand_wikidata": "Q332477"}
    allowed_domains = ["stores.victoriassecret.com"]
    sitemap_urls = ["https://stores.victoriassecret.com/sitemap.xml"]
    # Each store is published under up to three URLs, one per marketing specialty
    # ("lingerie", "bra-fitting", "beauty"), all sharing a store id and identical data.
    sitemap_rules = [(r"/[a-z-]+-[a-z]?\d+\.html$", "parse_sd")]
    wanted_types = ["ClothingStore"]
    search_for_facebook = False

    def post_process_item(self, item: Feature, response: TextResponse, ld_data: dict, **kwargs) -> Iterable[Feature]:
        # Delisted stores stay in the sitemap but serve their parent city or region
        # page, which describes the area rather than a store and has no store card.
        if not (card := response.xpath('//div[contains(@class, "location-card-wrap")]')):
            return

        item["ref"] = card.xpath(".//*[@data-fid]/@data-fid").get()

        # The structured data name is marketing copy ("Get a Free Bra Fitting in
        # Albany: Colonie"), so take the branch from the heading above the card. A few
        # stores are headed by the brand instead, leaving no branch to record.
        item.pop("name", None)
        branch = card.xpath("./preceding-sibling::h2[1]/text()").get()
        if not branch.startswith("Victoria's Secret"):
            item["branch"] = branch.removesuffix(" VS")

        # Beauty & Accessories stores are a cosmetics-led format carrying no clothing.
        if "Beauty" in card.xpath("./preceding-sibling::div[1]/text()").get():
            apply_category(Categories.SHOP_COSMETICS, item)
        else:
            apply_category(Categories.SHOP_CLOTHES, item)
            apply_clothes([Clothes.UNDERWEAR, Clothes.WOMEN], item)

        yield item
