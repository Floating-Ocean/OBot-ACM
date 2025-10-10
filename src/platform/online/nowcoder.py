import json
import re
import time
from datetime import datetime
from html import unescape
from urllib.parse import quote_plus

import pixie
from lxml.etree import Element

from src.core.util.tools import fetch_url_element, fetch_url_json, format_int_delta, check_intersect, \
    get_today_timestamp_range, format_timestamp, format_seconds
from src.platform.model import CompetitivePlatform, Contest
from src.render.pixie.render_user_card import UserCardRenderer


class NowCoder(CompetitivePlatform):
    platform_name = "NowCoder"
    rated_rks = {
        (-float('inf'), 700): '#灰',
        (700, 1100): '#紫',
        (1100, 1500): '#蓝',
        (1500, 2000): '#青',
        (2000, 2400): '#黄',
        (2400, 2800): '#橙',
        (2800, float('inf')): '#红'
    }
    rks_color = {
        '#灰': '#b4b4b4',
        '#紫': '#c177e7',
        '#蓝': '#5ea1f4',
        '#青': '#25bb9b',
        '#黄': '#ffd700',
        '#橙': '#ff8800',
        '#红': '#ff020a'
    }
    contest_category = {
        (13, 1): '提高训练营',
        (13, 2): '挑战赛',
        (13, 3): 'OI赛前训练营',
        (13, 4): '提高组',
        (13, 5): '普及组',
        (13, 6): '练习赛',
        (13, 7): '基础训练营',
        (13, 9): '小白月赛',
        (13, 10): '其他',
        (13, 19): '周赛',
        (13, 20): '暑期多校',
        (13, 21): '寒假集训营',
        (13, 22): '比赛真题',
        (13, 23): '课程配套题',
        (13, 24): '娱乐赛',
        (14, -1): '高校比赛',
    }

    @classmethod
    def _api(cls, url: str) -> list[dict]:
        json_data = fetch_url_json(url, method='get')

        if json_data['msg'] != "OK":
            raise ValueError("Invalid response for nowcoder api")

        data_list = json_data['data']['dataList']
        all_data = list(data_list)

        # 爬取所有页
        page_count = json_data['data']['pageInfo']['pageCount']
        for page in range(2, page_count + 1):
            json_data = fetch_url_json(f"{url}&page={page}", method='get')
            if json_data['msg'] != "OK":
                raise ValueError("Invalid response for nowcoder api")
            all_data.extend(list(json_data['data']['dataList']))

        return all_data

    @classmethod
    def _api_standings(cls, contest_id: int, search_name: str) -> tuple[str, list[dict]]:
        """榜单数据格式和其他的不一样，分开写，比普通的多返回一个赛制类型"""
        search_name = quote_plus(str(search_name).strip())
        url = ("https://ac.nowcoder.com/acm-heavy/acm/contest/real-time-rank-data?"
               f"id={contest_id}&searchUserName={search_name}&limit=0")
        json_data = fetch_url_json(url, method='get')

        if json_data['msg'] != "OK":
            raise ValueError("Invalid response for nowcoder api")

        data_list = json_data['data']['rankData']
        all_data = list(data_list)
        rank_type = json_data['data']['basicInfo']['rankType']

        # 爬取所有页
        page_count = json_data['data']['basicInfo']['pageCount']
        for page in range(2, page_count + 1):
            json_data = fetch_url_json(f"{url}&page={page}", method='get')
            if json_data['msg'] != "OK":
                raise ValueError("Invalid response for nowcoder api")
            all_data.extend(list(json_data['data']['rankData']))

        return rank_type, all_data

    @classmethod
    def _extract_timestamp(cls, time_str: str) -> int:
        return int(datetime.strptime(time_str, "%Y-%m-%d %H:%M").timestamp())

    @classmethod
    def _extract_duration(cls, time_str: str) -> int:
        units_in_seconds = {
            '天': 24 * 3600,
            '小时': 3600,
            '分钟': 60,
            '秒': 1
        }
        matches = re.findall(r'(\d+)(天|小时|分钟|秒)', time_str)
        total_seconds = 0
        for val, unit in matches:
            total_seconds += int(val) * units_in_seconds[unit]

        return total_seconds

    @classmethod
    def _decode_contest_time_set(cls, contest: Element) -> list[str]:
        return re.split(r' {4}|\n ', contest.xpath(".//li[@class='match-time-icon']/text()")[0])

    @classmethod
    def _decode_rated(cls, contest: Element) -> str:
        rated_icon = contest.xpath(".//span[contains(@class, 'tag-rating')]")
        if len(rated_icon) == 0:
            return "不计分"

        unrated_range_li = contest.xpath(".//li[@class='icon-nc-flash2']/text()")
        if len(unrated_range_li) == 0:
            return "为所有人计分"

        unrated_range = int(unrated_range_li[0].split('＞')[1])
        return f"为 0-{unrated_range} 计分"

    @classmethod
    def _merge_timestamp_range(cls, time_set: list[str]) -> tuple[int, int]:
        start_timestamp = cls._extract_timestamp(time_set[1])
        duration = cls._extract_duration(time_set[4])
        return start_timestamp, start_timestamp + duration

    @classmethod
    def _format_rating(cls, rating: int) -> str:
        rk = next((rk for (l, r), rk in cls.rated_rks.items() if l <= rating < r), '#灰')
        return f"{rating} {rk}"

    @classmethod
    def _fetch_user_rating(cls, handle: str) -> str:
        handle = quote_plus(str(handle).strip())
        html = fetch_url_element(f"https://ac.nowcoder.com/acm/contest/profile/{handle}")
        rating = int(html.xpath("//div[contains(@class, 'state-num rate-score')]/text()")[0])
        return cls._format_rating(rating)

    @classmethod
    def _fetch_team_members_info(cls, handle: str, inline: bool = False) -> str:
        handle = quote_plus(str(handle).strip())
        url = f"https://ac.nowcoder.com/acm/team/member-list?token=&teamId={handle}"
        members = cls._api(url)
        member_infos = []

        for member in members:
            member_info = [member['name']]
            if not inline:
                if member['isTeamAdmin']:
                    member_info.append("队长")
                member_info.append(cls._fetch_user_rating(member['uid']))
            member_infos.append(' '.join(member_info))

        return (', ' if inline else '\n').join(member_infos)

    @classmethod
    def _fetch_user_teams_info(cls, handle: str) -> str | None:
        handle = quote_plus(str(handle).strip())
        url = f"https://ac.nowcoder.com/acm/contest/profile/user-team-list?token=&uid={handle}"
        teams = cls._api(url)
        teams_infos = []

        for team in teams:
            team_info = [team['name'], cls._format_rating(int(team['rating']))]
            teams_infos.append(' '.join(team_info))

        if len(teams_infos) == 0:
            return None

        return '\n'.join(teams_infos)

    @classmethod
    def _format_social_info(cls, html: Element, i18n: str = "来自") -> list[str]:
        social_info = []
        edu_span = html.xpath('//a[contains(@class, "edu-item")]//span[@class="coder-edu-txt"]/text()')
        coll_span = html.xpath('//a[contains(@class, "coll-item")]//span[@class="coder-edu-txt"]/text()')
        edu_text = f"{i18n} {edu_span[0]}" if len(edu_span) > 0 else None
        coll_text = f"{coll_span[0]}er" if len(coll_span) > 0 else None
        edu_info = [edu_txt for edu_txt in [coll_text, edu_text] if edu_txt is not None]
        if len(edu_info) > 0:
            social_info.append('. '.join(edu_info))
        return social_info

    @classmethod
    def _format_standing(cls, rank_type: str, standing: dict) -> str:
        participate_type = '团队' if standing['team'] else '个人'
        supplement = (f"罚时 {standing['penaltyTime'] // 60000}" if rank_type == 'ICPC' else
                      f"总分 {standing['totalScore']}")
        standing = (f"#{standing['ranking']} {standing['userName']} @{standing['school']}\n"
                    f"{participate_type}，通过 {standing['acceptedCount']} 题，{supplement}")
        return standing

    @classmethod
    def _get_contest_list(cls) -> tuple[list[Contest], list[Contest], list[Contest]]:
        running_contests: list[Contest] = []
        upcoming_contests: list[Contest] = []
        finished_contests_today: list[Contest] = []
        finished_contests_last: list[Contest] = []

        def _pack_contest(contest: Element, phase: str, current_category_name: str) -> Contest:
            return Contest(
                platform=cls.platform_name,
                abbr=current_category_name,
                name=contest.xpath(".//a/text()")[0],
                phase=phase,
                start_time=cls._extract_timestamp(cls._decode_contest_time_set(contest)[1]),
                duration=cls._extract_duration(cls._decode_contest_time_set(contest)[4]),
                supplement=cls._decode_rated(contest)
            )

        for category, category_name in cls.contest_category.items():
            top_category_id, category_id = category
            html = fetch_url_element("https://ac.nowcoder.com/acm/contest/vip-index?"
                                     f"topCategoryFilter={top_category_id}&"
                                     f"categoryFilter={category_id}")
            js_current = html.xpath("//div[@class='platform-mod js-current']//div[@class='platform-item-cont']")
            js_end = html.xpath("//div[@class='platform-mod js-end']//div[@class='platform-item-cont']")
            running_contests.extend([
                _pack_contest(contest, '正在比赛中', category_name) for contest in js_current
                if contest.xpath(".//span[contains(@class, 'match-status')]/text()")[0].strip() == '比赛中'])
            upcoming_contests.extend([
                _pack_contest(contest, '即将开始', category_name) for contest in js_current
                if contest.xpath(".//span[contains(@class, 'match-status')]/text()")[0].strip() == '报名中'])
            finished_contests_today.extend([
                _pack_contest(contest, '已结束', category_name) for contest in js_end if
                check_intersect(range1=get_today_timestamp_range(),
                                range2=cls._merge_timestamp_range(cls._decode_contest_time_set(contest)))])
            if len(js_current) > 0:
                finished_contests_last.append(_pack_contest(js_end[0], '已结束', category_name))

        finished_contests_last.sort(key=lambda c: -c.start_time)
        if len(finished_contests_today) == 0:
            if len(finished_contests_last) == 0:
                finished_contests = []
            else:
                finished_contests = [finished_contests_last[0]]
        else:
            finished_contests = finished_contests_today

        return running_contests, upcoming_contests, finished_contests

    @classmethod
    def _get_specified_contest(cls, search_name: str) -> tuple[int, str] | None:
        search_name = quote_plus(str(search_name).strip())
        html = fetch_url_element("https://ac.nowcoder.com/acm-heavy/acm/contest/search?"
                                 f"searchName={search_name}")
        tr_elements = html.xpath('//tr[@class="js-nc-wrap-link js-item"]')
        if not tr_elements:
            return None

        # 牛客直接把每个比赛的 json 数据放在了 data-json 里，读即可
        data_json = tr_elements[0].get('data-json')
        unescaped_json = unescape(data_json)
        contest = json.loads(unescaped_json)
        contest_id = contest['contestId']

        phase = "即将开始"
        if time.time() >= contest['contestStartTime'] / 1000:
            phase = "正在比赛中"
        if time.time() >= contest['contestEndTime'] / 1000:
            phase = "已结束"

        rated_info = "为所有人计分" if contest['settingInfo']['ratingStatus'] != 'No' else '不计分'
        if contest['settingInfo']['needRatingUpperLimit']:
            unrated_range = contest['settingInfo']['ratingUpperLimit']
            rated_info = f"为 0-{unrated_range} 计分"

        formatted_contest = (
            f"[{contest_id}] {contest['contestName']}\n"
            f"{phase}, {format_timestamp(contest['contestStartTime'] // 1000)}\n"
            f"持续 {format_seconds(contest['contestDuration'] // 1000)}, {rated_info}"
        )
        return contest_id, formatted_contest

    @classmethod
    def get_user_id_card(cls, handle: str) -> pixie.Image | None:
        handle = quote_plus(str(handle).strip())
        html = fetch_url_element(f"https://ac.nowcoder.com/acm/contest/profile/{handle}")
        if html.xpath("//div[@class='null']"):
            return None

        is_group = len(html.xpath("//a[@class='group-member-btn']")) > 0
        if is_group:
            social = cls._fetch_team_members_info(handle, inline=True)
            if len(social) > 0:
                social = f"Team of {social}."
        else:
            social = '. '.join(cls._format_social_info(html, 'From'))
            if len(social) > 0:
                social = f"{social}."

        rating = int(html.xpath("//div[contains(@class, 'state-num rate-score')]/text()")[0])
        rank = next((rk for (l, r), rk in cls.rated_rks.items() if l <= rating < r), '#灰')
        return UserCardRenderer(handle=html.xpath("//a[contains(@class, 'coder-name')]/text()")[0].strip(),
                                social=social, rank=rank, rank_alias=rank, rating=rating, platform=cls).render()

    @classmethod
    def get_user_info(cls, handle: str) -> tuple[str, str] | None:
        handle = quote_plus(str(handle).strip())
        html = fetch_url_element(f"https://ac.nowcoder.com/acm/contest/profile/{handle}")
        if html.xpath("//div[@class='null']"):
            return None

        sections = []

        social = []
        name = html.xpath("//a[contains(@class, 'coder-name')]/text()")[0].strip()
        social.append(name)
        brief_intro = html.xpath("//div[@class='coder-brief']/text()")[0].strip()
        social.append(brief_intro)
        social.extend(cls._format_social_info(html))

        if len(social) > 0:
            sections.append('\n'.join(social))

        is_group = len(html.xpath("//a[@class='group-member-btn']")) > 0
        if is_group:
            members = cls._fetch_team_members_info(handle)
            sections.append(f"队伍成员:\n{members}")

        platform = []
        rating = int(html.xpath("//div[contains(@class, 'state-num rate-score')]/text()")[0])
        platform.append(f"比赛Rating: {cls._format_rating(rating)}")
        rating_rank = html.xpath('//div[@class="profile-status-box"]//a[contains(@href, "/rating-index")]/text()')
        following = html.xpath('//div[@class="profile-status-box"]//a[contains(@href, "/following")]/text()')
        followers = html.xpath('//div[@class="profile-status-box"]//a[contains(@href, "/followers")]/text()')
        if len(rating_rank) > 0:
            platform.append(f"位次: {rating_rank[0]}")
        if len(following) > 0:
            platform.append(f"关注: {following[0]}")
        if len(followers) > 0:
            platform.append(f"粉丝: {followers[0]}")
        sections.append('\n'.join(platform))

        joined_teams = cls._fetch_user_teams_info(handle)
        if joined_teams is not None:
            sections.append(f"加入的队伍:\n{joined_teams}")

        return '\n\n'.join(sections), html.xpath("//a[contains(@class, 'head-pic')]//img/@src")[0]

    @classmethod
    def get_user_last_contest(cls, handle: str) -> str:
        handle = quote_plus(str(handle).strip())
        url = ("https://ac.nowcoder.com/acm-heavy/acm/contest/profile/contest-joined-history?"
               f"uid={handle}&onlyJoinedFilter=true&onlyRatingFilter=true&contestEndFilter=true")
        rated_contests = cls._api(url)
        contest_count = len(rated_contests)
        if contest_count == 0:
            return "还未参加过 Rated 比赛"

        group_contest_count = len([contest for contest in rated_contests if contest['isTeamSignUp']])
        if group_contest_count > 0:
            contest_count = f"{contest_count}，包含团队赛 {group_contest_count} 场"

        last = rated_contests[0]
        info = (f"Rated 比赛数: {contest_count}\n"
                f"最近一次比赛: {last['contestName']}\n"
                f"位次: {last['rank']}\n"
                f"AC 数量: {last['acceptedCount']}\n"
                f"Rating 变化: {format_int_delta(int(last['changeValue']))}\n")

        return info

    @classmethod
    def get_user_contest_standings(cls, search_name: str, contest_name: str) -> tuple[str, list[str]] | None:
        contest = cls._get_specified_contest(contest_name)
        if not contest:
            return None
        contest_id, contest_info = contest

        rank_type, standing_data = cls._api_standings(contest_id, search_name)
        standings_info = [cls._format_standing(rank_type, standing) for standing in standing_data]

        return contest_info, standings_info
