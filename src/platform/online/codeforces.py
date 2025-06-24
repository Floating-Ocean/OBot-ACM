import random
import re
import time

import pixie
from thefuzz import process

from src.core.lib.cf_rating_calc import PredictResult, Contestant, predict
from src.core.util.tools import fetch_url_json, format_timestamp, get_week_start_timestamp, get_today_start_timestamp, \
    format_timestamp_diff, format_seconds, format_int_delta, decode_range, check_intersect, get_today_timestamp_range
from src.platform.model import CompetitivePlatform, Contest
from src.render.pixie.render_user_card import UserCardRenderer


class Codeforces(CompetitivePlatform):
    platform_name = "Codeforces"
    logo_url = "https://codeforces.org/s/24321/images/codeforces-sponsored-by-ton.png"
    rated_rks = {
        (-float('inf'), 1200): 'N',  # Newbie
        (1200, 1400): 'P',  # Pupil
        (1400, 1600): 'S',  # Specialist
        (1600, 1900): 'E',  # Expert
        (1900, 2100): 'CM',  # Candidate Master
        (2100, 2300): 'M',  # Master
        (2300, 2400): 'IM',  # International Master
        (2400, 2600): 'GM',  # Grandmaster
        (2600, 3000): 'IGM',  # International Grandmaster
        (3000, 4000): 'LGM',  # Legendary Grandmaster
        (4000, float('inf')): 'T'  # The Ones Who Reach 4000
    }
    rks_color = {
        'N': '#808080',
        'P': '#008000',
        'S': '#03a89e',
        'E': '#0000ff',
        'CM': '#aa00aa',
        'M': '#ff8c00',
        'IM': '#bbbb00',
        'GM': '#ff0000',
        'IGM': '#ff0000',
        'LGM': '#ff0000',
        'T': '#ff0000'
    }

    @classmethod
    def _api(cls, api: str, **kwargs) -> dict | int:
        """传递参数构造payload，添加首尾下划线可避免与关键词冲突"""
        url = f"https://codeforces.com/api/{api}"
        if len(kwargs) > 0:
            payload = '&'.join([f'{key.strip("_")}={val}' for key, val in kwargs.items()])
            url += f"?{payload}"
        json_data = fetch_url_json(url, throw=False)

        if isinstance(json_data, int) or json_data['status'] != "OK":
            if isinstance(json_data, int) and json_data != 400:
                return -1
            return 0

        return json_data['result']

    @classmethod
    def _format_verdict(cls, verdict: str, passed_count: int) -> str:
        verdict = verdict.replace("_", " ").capitalize()
        if verdict == "Ok":
            return "Accepted"
        elif verdict == "Skipped" or verdict == "Compilation error":
            return verdict
        elif verdict == "Challenged":
            return "Hacked"
        elif verdict == "Testing":
            return f"Running on test {passed_count + 1}"
        else:
            return f"{verdict} on test {passed_count + 1}"

    @classmethod
    def _format_contest_name(cls, name: str) -> str:
        """aaa.bbb -> aaaBbb"""
        return re.sub(r'(\w+)\.(\w+)', lambda m: m.group(1) + m.group(2).capitalize(), name)

    @classmethod
    def _format_rank_delta(cls, old_rating: int, delta: int) -> str:
        old_rk = next((rk for (l, r), rk in cls.rated_rks.items() if l <= old_rating < r), 'N')
        new_rk = next((rk for (l, r), rk in cls.rated_rks.items() if l <= old_rating + delta < r), 'N')
        if old_rk == new_rk:
            return "段位无变化"
        else:
            return f"段位变化 {old_rk}->{new_rk}"

    @classmethod
    def _format_standing(cls, standing: dict, contest_id: str) -> str:
        participant_types = {
            "CONTESTANT": "参赛",
            "PRACTICE": "练习",
            "VIRTUAL": "虚拟参赛",
            "MANAGER": "管理比赛",
            "OUT_OF_COMPETITION": "打星参赛"
        }
        member_info = "以个人为单位"
        if 'teamId' in standing['party']:
            member_info = f"作为团队 {standing['party']['teamName']} 的一员"
        member_info += participant_types[standing['party']['participantType']]
        if standing['party']['ghost']:
            member_info += " (Ghost)"

        accepted_prob_count = len([prob for prob in standing['problemResults'] if 'bestSubmissionTimeSeconds' in prob])
        rejected_attempt_count = sum(prob['rejectedAttemptCount'] for prob in standing['problemResults'])
        submission_info = f"通过 {accepted_prob_count} 题" if accepted_prob_count > 0 else "暂无题目通过"
        submission_info += f"，包含 {rejected_attempt_count} 次失败尝试" if rejected_attempt_count > 0 else "，无失败尝试"

        real_rank = standing['rank']
        contestant_predictions = ""
        if standing['party']['participantType'] == 'CONTESTANT':
            all_predictions = cls._fetch_contest_predict(contest_id)
            if not isinstance(all_predictions, int) and (standing['party']['members'][0]['handle'] in all_predictions):
                prediction = all_predictions[standing['party']['members'][0]['handle']]
                real_rank = prediction.rank
                contestant_predictions = (f'\n表现分 {prediction.performance}，'
                                          f'预测变化 {format_int_delta(prediction.delta)}，'
                                          f'{cls._format_rank_delta(prediction.rating, prediction.delta)}')

        striped_points = f"{standing['points']}".rstrip('0').rstrip('.')
        contestant_info = f"位次 {real_rank}，总分 {striped_points}，总罚时 {standing['penalty']}"
        hack_info = "Hack "
        hack_prop = []
        if standing['successfulHackCount'] > 0:
            hack_prop.append(format_int_delta(standing['successfulHackCount']))
        if standing['unsuccessfulHackCount'] > 0:
            hack_prop.append(format_int_delta(standing['unsuccessfulHackCount']))
        if len(hack_prop) > 0:
            hack_info += ':'.join(hack_prop)
            contestant_info += f"，{hack_info}"
        contestant_info += contestant_predictions

        if standing['party']['participantType'] == 'PRACTICE':
            contestant_info = None

        return '\n'.join([section for section in [member_info, submission_info, contestant_info]
                          if section is not None])

    @classmethod
    def _format_phase(cls, phase: str) -> str:
        formatter = {
            'BEFORE': '即将开始',
            'CODING': '正在比赛中',
            'PENDING_SYSTEM_TEST': '正在等待重测',
            'SYSTEM_TEST': '正在重测中',
            'FINISHED': '已结束'
        }
        if phase in formatter:
            return formatter[phase]
        else:
            raise ValueError(f'Invalid phase: {phase}')

    @classmethod
    def _format_contest(cls, contest: dict) -> str:
        phase = format_timestamp_diff(contest['relativeTimeSeconds'])
        if contest['phase'] in ['CODING', 'PENDING_SYSTEM_TEST', 'SYSTEM_TEST']:
            phase = cls._format_phase(contest['phase'])
        return (f"[{contest['id']}] {cls._format_contest_name(contest['name'])}\n"
                f"{phase}, "
                f"{format_timestamp(contest['startTimeSeconds'])}\n"
                f"持续 {format_seconds(contest['durationSeconds'])}, {contest['type']} 赛制")

    @classmethod
    def _adjust_old_ratings(cls, contest_id: int, rating_changes: list) -> dict:
        """
        Adapted from carrot at
        https://github.com/meooow25/carrot/blob/master/carrot/src/background/cache/contests-complete.js

        Note: This a band-aid for CF's fake ratings (see GitHub #18).
        If CF tells us that a user had rating 0, we consider that the user is in fact unrated.
        This unfortunately means that a user who truly has rating 0 will be considered to have
        DEFAULT_RATING, but such cases are unlikely compared to the regular presence of unrated
        users.
        """
        if contest_id < 1360:  # FAKE_RATINGS_SINCE_CONTEST
            return {change['handle']: {'oldRating': change['oldRating'],
                                       'realChange': (change['oldRating'], change['newRating'])}
                    for change in rating_changes}
        else:
            def _adjust(old: int) -> int:
                return 1400 if old == 0 else old  # NEW_DEFAULT_RATING

            return {change['handle']: {'oldRating': _adjust(change['oldRating']),
                                       'realChange': (change['oldRating'], change['newRating'])}
                    for change in rating_changes}

    @classmethod
    def _is_old_contest(cls, contest: dict) -> bool:
        """
        Adapted from carrot at
        https://github.com/meooow25/carrot/blob/master/carrot/src/background/cache/contests-complete.js
        """
        days_since_contest_end = ((time.time() - contest['startTimeSeconds'] - contest['durationSeconds'])
                                  / (60 * 60 * 24))
        return days_since_contest_end > 3  # RATING_PENDING_MAX_DAYS

    @classmethod
    def _get_predicted_prefs(cls, standings: dict) -> dict[str, PredictResult] | None:
        """
        Adapted from carrot at
        https://github.com/meooow25/carrot/blob/master/carrot/src/background/cache/contests-complete.js
        """
        ratings = cls._api('user.ratedList', activeOnly=False, contestId=standings['contest']['id'])
        if isinstance(ratings, int):
            return None
        ratings = {user['handle']: user['rating'] for user in ratings}

        is_edu_round = 'educational' in standings['contest']['name'].lower()
        rows = standings['rows']
        if is_edu_round:
            # For educational rounds, standings include contestants for whom the contest is not rated.
            rows = [row for row in standings['rows'] if
                    row['party']['members'][0]['handle'] in ratings and
                    row['party']['members'][0]['handle'] < 2100]  # EDU_ROUND_RATED_THRESHOLD

        contestants = [Contestant(
            handle=row['party']['members'][0]['handle'],
            points=row['points'],
            penalty=row['penalty'],
            rating=(1400 if row['party']['members'][0]['handle'] not in ratings
                    else ratings[row['party']['members'][0]['handle']])
        ) for row in rows]

        return predict(contestants, True)

    @classmethod
    def _get_final_prefs(cls, standings: dict, old_ratings: dict) -> dict[str, PredictResult] | None:
        """
        Adapted from carrot at
        https://github.com/meooow25/carrot/blob/master/carrot/src/background/cache/contests-complete.js
        """
        rows = [row for row in standings['rows'] if
                row['party']['members'][0]['handle'] in old_ratings]

        contestants = [Contestant(
            handle=row['party']['members'][0]['handle'],
            points=row['points'],
            penalty=row['penalty'],
            rating=old_ratings[row['party']['members'][0]['handle']]['oldRating'],
            real_change=old_ratings[row['party']['members'][0]['handle']]['realChange']
        ) for row in rows]

        return predict(contestants, True)

    @classmethod
    def _fetch_contest_list_all(cls) -> list[dict] | None:
        contest_list = cls._api('contest.list')

        if isinstance(contest_list, int):
            return None

        contest_list = list(contest_list)
        if len(contest_list) == 0:
            return []

        return contest_list

    @classmethod
    def _fetch_contest_predict(cls, contest_id: str) -> dict[str, PredictResult] | int:
        """
        Adapted from carrot at
        https://github.com/meooow25/carrot/blob/master/carrot/src/background/cache/contests-complete.js
        and
        https://github.com/meooow25/carrot/blob/master/carrot/src/background/background.js
        """
        standings = cls._api('contest.standings', contestId=contest_id, showUnofficial=False)

        if standings == -1:
            return -1
        if standings == 0:
            return 0

        rated, old_ratings = None, None

        if standings['contest']['phase'] == 'FINISHED':
            rating_changes = cls._api('contest.ratingChanges', contestId=contest_id)
            if rating_changes == -1:
                return -2
            if rating_changes == 0:
                rated = False
            else:
                rating_changes = list(rating_changes)
                if len(rating_changes) == 0:
                    return -2
                rated = True
                old_ratings = cls._adjust_old_ratings(int(contest_id), rating_changes)

        if rated is None and cls._is_old_contest(standings['contest']):
            rated = False

        contest_finished = rated is not None

        if contest_finished:
            if not rated:
                return 1

            # We can ensure that old_ratings is not None
            result = cls._get_final_prefs(standings, old_ratings)
            if result is None:
                return -3
            return result

        if (standings['contest']['name'].lower()
                in ['unrated', 'fools', 'q#', 'kotlin', 'marathon', 'teams']):  # UNRATED_HINTS
            return 1

        if any('teamId' in standing for standing in standings['rows']):
            return 1

        result = cls._get_predicted_prefs(standings)
        if result is None:
            return -3
        return result

    @classmethod
    def _format_social_info(cls, info: dict, i18n: tuple[str, str] = ("来自", "地球")) -> list[str]:
        social_info, identity, name = [], [], []
        if 'firstName' in info:
            name.append(info['firstName'])
        if 'lastName' in info:
            name.append(info['lastName'])
        if len(name) > 0:
            identity.append(' '.join(name))
        if 'city' in info:
            identity.append(info['city'])
        if 'country' in info:
            identity.append(info['country'])
        if len(identity) > 0:
            social_info.append(', '.join(identity))
        if 'organization' in info:
            if len(info['organization']) == 0:  # meme
                info['organization'] = i18n[1]
            social_info.append(f"{i18n[0]} {info['organization']}")
        return social_info

    @classmethod
    def _get_contest_list(cls) -> tuple[list[Contest], list[Contest], list[Contest]] | None:
        contest_list = cls._fetch_contest_list_all()

        if contest_list is None:
            return None

        def _pack_contest(contest: dict) -> Contest:
            return Contest(
                platform=cls.platform_name,
                abbr=f"CF{contest['id']}",
                name=contest['name'],
                phase=cls._format_phase(contest['phase']),
                start_time=contest['startTimeSeconds'],
                duration=contest['durationSeconds'],
                supplement=f"{contest['type']} 赛制"
            )

        running_contests = [_pack_contest(contest) for contest in contest_list
                            if contest['phase'] not in ['BEFORE', 'FINISHED']
                            and contest['startTimeSeconds'] + contest['durationSeconds']
                            >= get_today_start_timestamp() - 7 * 24 * 60 * 60]  # 不考虑结束后一周还不重测的比赛
        upcoming_contests = [_pack_contest(contest) for contest in contest_list if contest['phase'] == 'BEFORE']
        finished_contests = [_pack_contest(contest) for contest in contest_list if contest['phase'] == 'FINISHED'
                             and check_intersect(range1=get_today_timestamp_range(),
                                                 range2=(contest['startTimeSeconds'],
                                                         contest['startTimeSeconds'] + contest['durationSeconds']))
                             ]  # 所有和今天有交集的已结束比赛

        if len(finished_contests) == 0:
            finished_contests = [_pack_contest(next(contest for contest in contest_list
                                                    if contest['phase'] == 'FINISHED'))]

        return running_contests, upcoming_contests, finished_contests

    @classmethod
    def get_prob_tags_all(cls) -> list[str] | None:
        problems = cls._api('problemset.problems')
        if isinstance(problems, int):
            return None

        tags = []
        for problem in problems['problems']:
            for tag in problem['tags']:
                tags.append(tag.replace(" ", "-"))
        tags = list(set(tags))
        return tags

    @classmethod
    def get_prob_filtered(cls, tag_needed: str, limit: str = None, newer: bool = False,
                          on_tag_chosen=None) -> dict | int:
        if tag_needed == "all":
            problems = cls._api('problemset.problems')
        else:
            all_tags = cls.get_prob_tags_all()
            if all_tags is None:
                return -2
            if tag_needed not in all_tags:  # 模糊匹配
                closet_tag = process.extract(tag_needed, all_tags, limit=1)[0]
                if closet_tag[1] < 60:
                    return -3
                tag_needed = closet_tag[0]
                if on_tag_chosen is not None:
                    on_tag_chosen(f"标签最佳匹配: {tag_needed}")
            problems = cls._api('problemset.problems', tags=tag_needed.replace("-", " "))

        if isinstance(problems, int) or len(problems) == 0:
            return -1

        filtered_data = problems['problems']
        if limit is not None:
            min_point, max_point = decode_range(limit, length=(3, 4))
            if min_point == -2:
                return -1
            elif min_point == -3:
                return 0
            filtered_data = [prob for prob in problems['problems']
                             if 'rating' in prob and min_point <= prob['rating'] <= max_point]
        if newer:
            filtered_data = [prob for prob in filtered_data if prob['contestId'] >= 1000]

        return random.choice(filtered_data) if len(filtered_data) > 0 else 0

    @classmethod
    def get_user_rank(cls, handle: str) -> str | None:
        info = cls._api('user.info', handles=handle)

        if info == -1:
            return None
        if info == 0 or len(info) == 0:
            return None

        info = info[-1]

        return (f"{info['rating']} "
                f"{next((rk for (l, r), rk in cls.rated_rks.items() if l <= info['rating'] < r), 'N')}")

    @classmethod
    def get_user_id_card(cls, handle: str) -> pixie.Image | str:
        info = cls._api('user.info', handles=handle)

        if info == -1:
            return "查询异常"
        if info == 0 or len(info) == 0:
            return "用户不存在"

        info = info[-1]

        social = '. '.join(cls._format_social_info(info, ('From', 'Earth')))
        if len(social) > 0:
            social = f"{social}."

        rating = 0
        rank = "Unrated"
        if 'rating' in info:
            rating = info['rating']
            rank = info['rank'].title()

        rank_alias = next((rk for (l, r), rk in cls.rated_rks.items() if l <= rating < r), 'N')
        return UserCardRenderer(handle=info['handle'], social=social,
                                rank=rank, rank_alias=rank_alias, rating=rating, platform=cls).render()

    @classmethod
    def get_user_info(cls, handle: str) -> tuple[str, str | None]:
        info = cls._api('user.info', handles=handle)

        if info == -1:
            return "查询异常", None
        if info == 0 or len(info) == 0:
            return "用户不存在", None

        info = info[-1]
        sections = []

        # 社交信息
        social = cls._format_social_info(info)
        if len(social) > 0:
            sections.append('\n'.join(social))

        # 平台上的信息
        rating = "0 Unrated"
        if 'rating' in info:
            rating = (f"{info['rating']} {info['rank'].title()} "
                      f"(max. {info['maxRating']} {info['maxRank']})")
        platform = (f"比赛Rating: {rating}\n"
                    f"贡献: {info['contribution']}\n"
                    f"粉丝: {info['friendOfCount']}")
        sections.append(platform)

        return '\n\n'.join(sections), info.get('titlePhoto')

    @classmethod
    def get_user_last_contest(cls, handle: str) -> str:
        rating = cls._api('user.rating', handle=handle)

        if rating == -1:
            return "查询异常"
        if rating == 0:
            return "用户不存在"

        rated_contests = list(rating)
        contest_count = len(rated_contests)
        if contest_count == 0:
            return "还未参加过 Rated 比赛"

        last = rated_contests[-1]
        info = (f"Rated 比赛数: {contest_count}\n"
                f"最近一次比赛: {cls._format_contest_name(last['contestName'])}\n"
                f"比赛编号: {last['contestId']}\n"
                f"位次: {last['rank']}\n"
                f"Rating 变化: {format_int_delta(last['newRating'] - last['oldRating'])}")

        return info

    @classmethod
    def get_user_last_submit(cls, handle: str, count: int = 5) -> str:
        status = cls._api('user.status', handle=handle, _from_=1, count=count)

        if status == -1:
            return "查询异常"
        if status == 0:
            return "用户不存在"

        status = list(status)
        if len(status) == 0:
            return "还未提交过题目"

        info = f"最近{count}发提交:"
        for submit in status:
            verdict = (cls._format_verdict(submit['verdict'], submit['passedTestCount'])
                       if 'verdict' in submit else "In queue")
            points = f" *{int(submit['problem']['rating'])}" if 'rating' in submit['problem'] else ""
            time_consumed = f" {submit['timeConsumedMillis']}ms" if 'timeConsumedMillis' in submit else ""
            info += (f"\n[{submit['id']}] {verdict} "
                     f"P{submit['problem']['contestId']}{submit['problem']['index']}{points}{time_consumed} "
                     f"{format_timestamp(submit['creationTimeSeconds'])}")

        return info

    @classmethod
    def get_user_submit_counts(cls, handle: str) -> tuple[int, int, int]:
        status = cls._api('user.status', handle=handle)

        if isinstance(status, int):
            return -1, -1, -1

        status = list(status)
        submit_len = len(status)
        if submit_len == 0:
            return 0, 0, 0

        total_set, weekly_set, daily_set = set(), set(), set()
        week_start_time, today_start_time = get_week_start_timestamp(), get_today_start_timestamp()
        for submit in status:
            if submit['verdict'] != "OK":
                continue
            current_prob = f"{submit['problem'].get('contestId')}-{submit['problem'].get('index')}"
            total_set.add(current_prob)
            if submit['creationTimeSeconds'] >= week_start_time:
                weekly_set.add(current_prob)
            if submit['creationTimeSeconds'] >= today_start_time:
                daily_set.add(current_prob)

        return len(total_set), len(weekly_set), len(daily_set)

    @classmethod
    def get_user_contest_standings(cls, handle: str, contest_id: str) -> tuple[str, list[str] | None]:
        standings = cls._api('contest.standings', handles=handle, contestId=contest_id, showUnofficial=True)

        if standings == -1:
            return "查询异常", None
        if standings == 0:
            return "比赛不存在", None

        contest_info = cls._format_contest(standings['contest'])
        standings_info = [cls._format_standing(standing, contest_id) for standing in standings['rows']]

        return contest_info, standings_info
