import json
import os

import pixie

from src.core.constants import Constants
from src.core.util.tools import check_intersect, get_today_timestamp_range
from src.platform.model import CompetitivePlatform, Contest, DynamicContest, DynamicContestPhase

_lib_path = os.path.join(Constants.config["lib_path"], "Contest-List-Renderer")


class ManualPlatform(CompetitivePlatform):
    """
    本类平台用于手动配置的比赛列表获取
    注意其他方法和成员均未被实现
    """
    platform_name = "手动配置的"
    rks_color = {}

    @classmethod
    def _get_contest_list(cls) -> tuple[list[Contest], list[Contest], list[Contest]] | None:
        running_contests, upcoming_contests, finished_contests = [], [], []

        manual_contests_path = os.path.join(_lib_path, 'manual_contests.json')
        if not os.path.exists(manual_contests_path):
            return [], [], []

        try:
            with open(manual_contests_path, 'r', encoding='utf-8') as f:
                manual_contests = json.load(f)
                for raw_contest in manual_contests:
                    contest = DynamicContest(**raw_contest)
                    current_phase = contest.get_phase()
                    if current_phase == DynamicContestPhase.RUNNING:
                        running_contests.append(contest)
                    elif current_phase == DynamicContestPhase.UPCOMING:
                        upcoming_contests.append(contest)
                    elif check_intersect(range1=get_today_timestamp_range(),
                                         range2=(contest.start_time,
                                                 contest.start_time + contest.duration)):
                        finished_contests.append(contest)
        except (json.JSONDecodeError, KeyError) as e:
            Constants.log.error(f"Decode manual_contests.json failed: {e}")
            return [], [], []

        return running_contests, upcoming_contests, finished_contests

    @classmethod
    def get_user_id_card(cls, handle: str) -> pixie.Image | str:
        return "手动配置平台不支持此操作"

    @classmethod
    def get_user_info(cls, handle: str) -> tuple[str, str | None]:
        return "手动配置平台不支持此操作", None
