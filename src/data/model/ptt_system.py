from dataclasses import dataclass


@dataclass
class DuelUser:
    ptt: int
    contest_history: list[int]


class PttSystem:
    """潜力值系统，基于ELO机制修改"""
    MIN_PTT = -500
    MAX_PTT = 6000
    BASE_RATING = 1400
    BASE_K = 128

    # 前6次比赛的额外奖励值（总和1400）
    BONUSES = [500, 350, 250, 150, 100, 50]

    @classmethod
    def _get_calc_ptt(cls, user: DuelUser) -> int:
        calc_ptt = user.ptt + 1400
        for count, bonus in enumerate(cls.BONUSES):
            if len(user.contest_history) == count:
                break
            calc_ptt -= bonus
        return calc_ptt

    @classmethod
    def calculate_ptt_change(cls, r_a: int, r_b: int, outcome: int, difficulty: int) -> tuple:
        """
        计算duel后的ptt变化
        :param r_a: 用户A当前计算ptt
        :param r_b: 用户B当前计算ptt
        :param outcome: 比赛结果 (0=A赢, 1=B赢, 2=平局)
        :param difficulty: 题目难度(800~3000)
        :return: (delta_a, delta_b)
        """
        # 题难，加多扣少
        difficulty_factor = difficulty / 3000
        inc_k = 2 * (difficulty_factor ** 0.9)
        dec_k = difficulty_factor ** 1.6

        # ptt越高，加少扣多
        ptt_factor_a = (r_a - cls.MIN_PTT) / (cls.MAX_PTT - cls.MIN_PTT)
        ptt_factor_b = (r_b - cls.MIN_PTT) / (cls.MAX_PTT - cls.MIN_PTT)

        # 预期胜率，胜率越高变化越小
        exp_a = 1.0 / (1 + 10 ** ((r_b - r_a) / 400.0))
        exp_b = 1.0 - exp_a

        # 确定实际得分
        if outcome == 0:  # A胜利
            delta_a = cls.BASE_K * inc_k * (1.0 - exp_a) * (1 - ptt_factor_a)
            delta_b = cls.BASE_K * dec_k * (0.0 - exp_b) * ptt_factor_b
        elif outcome == 1:  # B胜利
            delta_a = cls.BASE_K * dec_k * (0.0 - exp_a) * ptt_factor_a
            delta_b = cls.BASE_K * inc_k * (1.0 - exp_b) * (1 - ptt_factor_b)
        else:  # 平局，根据难度给奖励分
            delta_a = cls.BASE_K * 0.08 * max(0.0, difficulty_factor - ptt_factor_a)
            delta_b = cls.BASE_K * 0.08 * max(0.0, difficulty_factor - ptt_factor_b)

        return int(round(delta_a)), int(round(delta_b))

    @classmethod
    def update_user_ptt(cls, user: DuelUser, delta: int):
        """
        更新用户ptt状态
        :param user: DuelUser
        :param delta: 本次比赛变化值
        """
        # 计算新ptt（边界保护）
        calc_ptt = cls._get_calc_ptt(user)
        new_calc_ptt = max(cls.MIN_PTT, min(calc_ptt + delta, cls.MAX_PTT))

        # 新用户冷启动处理
        contest_count = len(user.contest_history)
        if contest_count < len(cls.BONUSES):
            delta += cls.BONUSES[contest_count]
        else:
            delta = new_calc_ptt - calc_ptt

        user.ptt += delta
        user.contest_history.append(user.ptt)

    @classmethod
    def process_duel(cls, user_a: DuelUser, user_b: DuelUser, outcome: int, difficulty: int):
        """
        处理一次duel并更新双方ptt
        """
        delta_a, delta_b = cls.calculate_ptt_change(
            cls._get_calc_ptt(user_a),
            cls._get_calc_ptt(user_b),
            outcome,
            difficulty
        )
        cls.update_user_ptt(user_a, delta_a)
        cls.update_user_ptt(user_b, delta_b)

