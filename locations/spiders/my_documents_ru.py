import re
from typing import AsyncIterator, Iterable

from scrapy import Spider
from scrapy.http import JsonRequest, Response

from locations.categories import apply_category
from locations.geo import bbox_split
from locations.hours import DAYS_RU, OpeningHours, day_range
from locations.items import Feature


class MyDocumentsRUSpider(Spider):
    name = "my_documents_ru"
    item_attributes = {"brand": "Мои документы", "brand_wikidata": "Q57449742"}
    requires_proxy = "RU"
    custom_settings = {"ROBOTSTXT_OBEY": False}
    points_url = "https://www.gosuslugi.ru/api/map/v1/layers/mfc/points"
    # The API returns at most 1000 points per request, so saturated boxes are split into quarters
    max_points = 1000

    def make_request(self, bbox: tuple[tuple[float, float], tuple[float, float]]) -> JsonRequest:
        (lat_nw, lon_nw), (lat_se, lon_se) = bbox
        return JsonRequest(
            url=self.points_url,
            data={"bounds": [[lon_nw, lat_se], [lon_se, lat_nw]], "insideBounds": True},
            cb_kwargs={"bbox": bbox},
            dont_filter=True,
        )

    async def start(self) -> AsyncIterator[JsonRequest]:
        yield self.make_request(((82.0, 19.0), (41.0, 180.0)))

    def parse(
        self, response: Response, bbox: tuple[tuple[float, float], tuple[float, float]]
    ) -> Iterable[Feature | JsonRequest]:
        services = response.json()["services"]
        if len(services) >= self.max_points:
            for sub_bbox in bbox_split(bbox, precision=6):
                yield self.make_request(sub_bbox)
            return

        for poi in services:
            item = Feature()
            item["ref"] = poi["oid"]
            item["name"] = poi["orgName"]
            item["addr_full"] = poi["address"]
            item["lon"], item["lat"] = poi["location"]["coordinates"]
            phone = poi["contacts"][1]
            if "null" not in phone:
                item["phone"] = phone
            item["opening_hours"] = self.parse_hours(poi["worktime"])
            apply_category({"office": "government", "government": "public_service"}, item)
            yield item

    def parse_hours(self, worktime: str | None) -> OpeningHours | None:
        if not worktime:
            return None
        oh = OpeningHours()
        for rule in worktime.split(";"):
            day_spec, _, times = rule.partition(":")
            start_day, _, end_day = day_spec.strip().partition("-")
            days = day_range(DAYS_RU[start_day], DAYS_RU[end_day or start_day])
            if "выходной" in times:
                oh.set_closed(days)
                continue
            open_time, close_time, *lunch = re.findall(r"\d\d:\d\d", times)
            if lunch:
                oh.add_days_range(days, open_time, lunch[0])
                oh.add_days_range(days, lunch[1], close_time)
            else:
                oh.add_days_range(days, open_time, close_time)
        return oh
