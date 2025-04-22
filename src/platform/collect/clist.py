from urllib.parse import quote

from src.core.constants import Constants
from src.core.util.tools import fetch_url_json


class Clist:
    _api_key = Constants.config["clist_apikey"]

    @classmethod
    def api(cls, api: str, **kwargs) -> list[dict] | int:
        """传递参数构造payload，添加首尾下划线可避免与关键词冲突"""
        route = f"/api/v4/{api}"
        objects = []
        kwargs['limit'] = 1000  # 单页最大值，减少请求次数
        while route is not None:
            if len(kwargs) > 0:
                payload = '&'.join([f'{key.strip("_")}='
                                    f'{quote(str(val))}' for key, val in kwargs.items()])
                route += f"?{payload}"
            json_data = fetch_url_json(f"https://clist.by{route}", throw=False, method='get',
                                       inject_headers={"Authorization": f"{cls._api_key}"})

            if isinstance(json_data, int):
                return -1

            objects.extend(json_data['objects'])
            route = json_data['meta']['next']
            kwargs.clear()  # next地址里会自带原参数

        return objects
