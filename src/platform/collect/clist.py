from urllib.parse import urljoin, urlencode

from src.core.constants import Constants
from src.core.util.tools import fetch_url_json


class Clist:
    _api_key = Constants.modules_conf.clist["apikey"]

    @classmethod
    def api(cls, api: str, **kwargs) -> list[dict]:
        """传递参数构造payload，添加首尾下划线可避免与关键词冲突"""
        route = f"/api/v4/{api}"
        objects = []
        kwargs.setdefault('limit', 1000)  # 单页最大值，减少请求次数
        while route is not None:
            if kwargs:
                payload = urlencode({k.strip("_"): v for k, v in kwargs.items()}, doseq=True)
                route = f"{route}?{payload}"
            url = urljoin("https://clist.by", route)
            json_data = fetch_url_json(url, method='get',
                                       inject_headers={"Authorization": f"{cls._api_key}"})
            objects.extend(json_data['objects'])
            route = json_data['meta']['next']
            kwargs.clear()  # next地址里会自带原参数

        return objects
