import random
from datetime import datetime
from urllib.parse import quote_plus

import pixie
from lxml.etree import Element

from src.core.util.tools import fetch_url_element, fetch_url_json, format_int_delta, \
    patch_https_url, decode_range, check_intersect, get_today_timestamp_range, check_is_int
from src.platform.collect.clist import Clist
from src.platform.model import CompetitivePlatform, Contest, UserLastContest
from src.platform.online.codeforces import Codeforces
from src.render.pixie.render_user_card import UserCardInfo, UserCardRenderer, UserCardSection


class AtCoder(CompetitivePlatform):
    platform_name = "AtCoder"
    rks_color = {
        '10 Kyu': '#808080', '9 Kyu': '#808080',
        '8 Kyu': '#804000', '7 Kyu': '#804000',
        '6 Kyu': '#008000', '5 Kyu': '#008000',
        '4 Kyu': '#00c0c0', '3 Kyu': '#00c0c0',
        '2 Kyu': '#0000ff', '1 Kyu': '#0000ff',
        '1 Dan': '#c0c000', '2 Dan': '#c0c000',
        '3 Dan': '#ff8000', '4 Dan': '#ff8000',
        '5 Dan': '#ff0000', '6 Dan': '#ff0000',
        '7 Dan': '#ff0000', '8 Dan': '#ff0000',
        '9 Dan': '#ff0000', '10 Dan': '#ff0000',
        'King': '#ff0000'
    }

    @classmethod
    def _extract_timestamp(cls, time_str: str) -> int:
        return int(datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S%z").timestamp())

    @classmethod
    def _extract_duration(cls, time_str: str) -> int:
        hour, minute = map(int, time_str.split(":"))
        return hour * 3600 + minute * 60

    @classmethod
    def _merge_timestamp_range(cls, time_set: list[str]) -> tuple[int, int]:
        start_timestamp = cls._extract_timestamp(time_set[0])
        duration = cls._extract_duration(time_set[1])
        return start_timestamp, start_timestamp + duration

    @classmethod
    def _format_rated_range(cls, rating_str: str) -> str:
        rating_str = rating_str.replace(' ', '')
        if rating_str == '-':
            return "不计分"
        if rating_str[0] == '-':
            return f"为 0{rating_str} 计分"
        if rating_str[-1] == '-':
            return f"为 {rating_str}∞ 计分"
        if rating_str == 'All':
            return "为所有人计分"
        return f"为 {rating_str} 计分"

    @classmethod
    def _format_social_info(cls, info: dict,
                            i18n: tuple[str, str, str] = ("国家/地区", "出生年份", "来自")) -> list[str]:
        social_info = []
        tag_trans = {
            "Country/Region": i18n[0],
            "Birth Year": i18n[1],
            "Affiliation": i18n[2]
        }
        for tag, trans in tag_trans.items():
            if tag in info:
                social_info.append(f"{trans} {info[tag]}")
        return social_info

    @classmethod
    def _get_contest_list(cls) -> tuple[list[Contest], list[Contest], list[Contest]]:
        html = fetch_url_element("https://atcoder.jp/contests/")
        contest_table_active = html.xpath("//div[@id='contest-table-active']//tbody/tr")
        contest_table_upcoming = html.xpath("//div[@id='contest-table-upcoming']//tbody/tr")
        contest_table_recent = html.xpath("//div[@id='contest-table-recent']//tbody/tr")

        def _pack_contest(contest: Element, phase: str) -> Contest:
            return Contest(
                platform=cls.platform_name,
                abbr=contest.xpath(".//td[2]/a/@href")[0].split('/')[-1].upper(),
                name=contest.xpath(".//td[2]/a/text()")[0],
                phase=phase,
                start_time=cls._extract_timestamp(contest.xpath(".//td[1]/a/time/text()")[0]),
                duration=cls._extract_duration(contest.xpath(".//td[3]/text()")[0]),
                supplement=cls._format_rated_range(contest.xpath(".//td[4]/text()")[0])
            )

        running_contests = [_pack_contest(contest, '正在比赛中') for contest in contest_table_active]
        upcoming_contests = [_pack_contest(contest, '即将开始') for contest in contest_table_upcoming]
        finished_contests = [_pack_contest(contest, '已结束') for contest in contest_table_recent if
                             check_intersect(range1=get_today_timestamp_range(),
                                             range2=cls._merge_timestamp_range([
                                                 contest.xpath(".//td[1]/a/time/text()")[0],
                                                 contest.xpath(".//td[3]/text()")[0]]))
                             ]

        if len(finished_contests) == 0 and len(contest_table_recent) > 0:
            finished_contests = [_pack_contest(contest_table_recent[0], '已结束')]

        return running_contests, upcoming_contests, finished_contests

    @classmethod
    def get_prob_filtered(cls, contest_type: str = 'common', limit: str = None) -> dict | int:
        filter_regex = ''
        if contest_type == 'common':
            filter_regex = r'^https:\/\/atcoder\.jp\/contests\/(abc|arc|agc|ahc)'
        elif contest_type in ['abc', 'arc', 'agc', 'ahc']:
            filter_regex = rf'^https:\/\/atcoder\.jp\/contests\/{contest_type}'
        elif contest_type == 'sp':
            filter_regex = r'^(?!https:\/\/atcoder\.jp\/contests\/(abc|arc|agc|ahc)).*'
        elif contest_type != 'all':
            return -2

        if limit is not None:
            min_point, max_point = decode_range(limit, length=(3, 4))
            if min_point == -2:
                return -1
            if min_point == -3:
                return 0
            filtered_data = Clist.api("problem", resource_id=93, rating__gte=min_point,
                                      rating__lte=max_point, url__regex=filter_regex)
        else:
            filtered_data = Clist.api("problem", resource_id=93, url__regex=filter_regex)

        return random.choice(filtered_data) if len(filtered_data) > 0 else 0

    @classmethod
    def _fetch_user_profile(cls, handle: str) -> tuple[Element, dict, dict] | None:
        """获取用户主页，返回 (html, 资料表, 比赛状态表)"""
        handle = quote_plus(str(handle).strip())
        html = fetch_url_element(f"https://atcoder.jp/users/{handle}",
                                 accept_codes=[200, 404])
        if html.xpath('//text()[contains(., "404 Not Found")]'):
            return None

        info_table = html.xpath("//table[@class='dl-table']//tr")
        info_dict = {row.xpath('.//th/text()')[0]:
                         row.xpath('.//td//text()')[0].strip() for row in info_table}

        rated_dict = {}
        rated_div = html.xpath("//div[h3[text()='Contest Status']]")
        if len(rated_div) > 0:
            rated_table = rated_div[0].xpath(".//table")[0].xpath(".//tr")
            rated_dict = {row.xpath('.//th/text()')[0].strip():
                              row.xpath('.//td//text()') for row in rated_table}

        return html, info_dict, rated_dict

    @classmethod
    def _extract_rank_alias(cls, rated_dict: dict) -> str:
        """从 Highest Rating 一行里挑出段位，形如 6 Kyu / 3 Dan / King"""
        for token in [token.strip() for token in rated_dict.get('Highest Rating', [])]:
            if token in cls.rks_color:
                return token
        # 从未参加过比赛时没有段位，按最低段位配色
        return '10 Kyu'

    @classmethod
    def get_user_card(cls, handle: str) -> pixie.Image | None:
        profile = cls._fetch_user_profile(handle)
        if profile is None:
            return None
        html, info_dict, rated_dict = profile

        rating = 0
        if len(rated_dict.get('Rating', [])) > 0 and check_is_int(rated_dict['Rating'][0]):
            rating = int(rated_dict['Rating'][0])
        rank_alias = cls._extract_rank_alias(rated_dict)

        social = []
        for tag, prefix in [("Country/Region", ""), ("Birth Year", "生于"),
                            ("Affiliation", "来自")]:
            if tag in info_dict:
                social.append(f"{prefix} {info_dict[tag]}".strip())

        rating_note = ""
        ratings = [token.strip() for token in rated_dict.get('Highest Rating', [])
                   if token.strip()]
        promote = next((token for token in ratings if 'to promote' in token), None)
        if promote is not None:
            rating_note = promote.strip('()')

        metrics = []
        if len(rated_dict.get('Rated Matches', [])) > 0:
            metrics.append(("Rated 比赛数", rated_dict['Rated Matches'][0].strip()))
        if len(rated_dict.get('Rank', [])) > 0:
            metrics.append(("位次", rated_dict['Rank'][0].strip()))
        if len(ratings) > 0:
            metrics.append(("最高 Rating", ratings[0]))

        # 日期过长，放在身份区的补充信息里而不是指标格
        timeline = []
        if len(rated_dict.get('Last Competed', [])) > 0:
            timeline.append(f"最近参赛 {rated_dict['Last Competed'][0].strip()}")

        sections = []
        linked = []
        for tag in ["Twitter ID", "TopCoder ID", "Codeforces ID"]:
            if tag not in info_dict:
                continue
            account = info_dict[tag]
            if tag == "Codeforces ID":
                cf_rank = Codeforces.get_user_rank(account)
                if cf_rank:
                    account = f"{account} ({cf_rank})"
            linked.append(f"{tag[:-3]}: {account}")
        if len(linked) > 0:
            sections.append(UserCardSection("关联账号", linked))

        last_contest = cls.get_user_last_contest(handle)
        if last_contest:
            contest_lines = [last_contest.name]
            if len(last_contest.details) > 0:
                contest_lines.append(' · '.join(last_contest.details))
            sections.append(UserCardSection("最近比赛", contest_lines))

        card_info = UserCardInfo(
            platform_name=cls.platform_name,
            handle=html.xpath("//a[@class='username']//text()")[0],
            accent_color=cls.rks_color.get(rank_alias, '#808080'),
            rating=f"{rating}" if rating > 0 else "Unrated",
            rank=rank_alias,
            rating_note=rating_note,
            avatar_url=patch_https_url(html.xpath("//img[@class='avatar']/@src")[0]),
            social=social,
            timeline=timeline,
            metrics=metrics,
            sections=sections
        )
        return UserCardRenderer(card_info).render()

    @classmethod
    def get_user_last_contest(cls, handle: str) -> UserLastContest | None:
        handle = quote_plus(str(handle).strip())
        url = f"https://atcoder.jp/users/{handle}/history/json"
        json_data = fetch_url_json(url, method='get')

        rated_contests = [contest for contest in json_data if contest['IsRated']]
        contest_count = len(rated_contests)
        if contest_count == 0:
            return UserLastContest("还未参加过 Rated 比赛")

        last = rated_contests[-1]
        return UserLastContest(
            name=last['ContestName'],
            details=[f"位次 {last['Place']}",
                     f"表现分 {last['Performance']} ({last['InnerPerformance']})",
                     f"Rating {format_int_delta(last['NewRating'] - last['OldRating'])}"],
            rated_count=contest_count
        )
