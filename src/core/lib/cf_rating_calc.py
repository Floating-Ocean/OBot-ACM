"""
Improved rating calculation code adapted from carrot at
https://github.com/meooow25/carrot/blob/master/carrot/src/background/predict.js

rating calculation code adapted from TLE at
https://github.com/cheran-senthil/TLE/blob/master/tle/util/ranklist/rating_calculator.py

originally adapted from Codeforces code to recalculate ratings
by Mike Mirzayanov (mirzayanovmr@gmail.com) at https://codeforces.com/contest/1/submission/13861109
"""
from dataclasses import dataclass

import numpy as np


class Contestant:
    def __init__(self, handle: str, points: float, penalty: int, rating: int, real_change: tuple[int, int] = None):
        self.handle = handle
        self.points = points
        self.penalty = penalty
        self.rating = rating
        self.real_change = real_change

        self.rank = None
        self.delta = None
        self.performance = None


@dataclass
class PredictResult:
    rank: int
    rating: int
    delta: int
    performance: int


MAX_RATING_LIMIT: int = 6000
MIN_RATING_LIMIT: int = -500
RATING_RANGE_LEN: int = MAX_RATING_LIMIT - MIN_RATING_LIMIT

# The probability of contestant with rating x winning versus contestant with rating y
# is given by ELO_WIN_PROB[y - x].
ELO_WIN_PROB = np.roll(1 / (1 + np.power(10, np.arange(-RATING_RANGE_LEN, RATING_RANGE_LEN) / 400)), -RATING_RANGE_LEN)


def binary_search(low, high, condition):
    while high - low > 1:
        mid = (low + high) // 2
        if condition(mid):
            high = mid
        else:
            low = mid
    return low


class RatingCalculator:
    def __init__(self, contestants: list[Contestant]):
        self.contestants = contestants
        self.seed = None
        self.adjustment = None

    def calculate_deltas(self, calc_perfs: bool = False):
        self.calc_seed()
        self.reassign_ranks()
        self.calc_deltas()
        self.adjust_deltas()
        if calc_perfs:
            self.calc_perfs()

    def calc_seed(self):
        """
        Expected rank for a contestant x is 1 + sum of ELO win probabilities of every other
        contestant versus x.
        seed[r] is the expected rank of a contestant with rating r, who did not participate in the
        contest, if he had participated.
        """
        count = np.zeros(2 * RATING_RANGE_LEN)
        for c in self.contestants:
            count[c.rating] += 1

        self.seed = 1 + np.fft.ifft(np.fft.fft(count) * np.fft.fft(ELO_WIN_PROB)).real

    def get_seed(self, r: int, exclude: int) -> float:
        """
        This returns the expected rank of a contestant with rating r who did not participate in the
        contest, leaving a single contestant out of the contest whose rating is exclude.
        Equivalently this is the expected rank of a contestant with true rating exclude, who did
        participate in the contest, assuming his rating had been r.
        """
        return self.seed[r] - ELO_WIN_PROB[r - exclude]

    def reassign_ranks(self):
        self.contestants.sort(key=lambda x: (-x.points, x.penalty))
        last_points = last_penalty = rank = None
        for idx in reversed(range(len(self.contestants))):
            c = self.contestants[idx]
            if c.points != last_points or c.penalty != last_penalty:
                last_points, last_penalty, rank = c.points, c.penalty, idx + 1
            c.rank = rank

    def calc_delta(self, contestant: Contestant, assumed_rating: int) -> int:
        seed = self.get_seed(assumed_rating, contestant.rating)
        mid_rank = np.sqrt(contestant.rank * seed)
        need_rating = self.rank_to_rating(mid_rank, contestant.rating)
        delta = int(np.trunc((need_rating - assumed_rating) / 2))
        return delta

    def calc_deltas(self):
        for c in self.contestants:
            c.delta = self.calc_delta(c, c.rating)

    def rank_to_rating(self, rank: int, self_rating: int) -> int:
        """Finds last rating at which seed >= rank."""
        return binary_search(2, MAX_RATING_LIMIT,
                             lambda x: self.get_seed(x, self_rating) < rank) - 1

    def adjust_deltas(self):
        self.contestants.sort(key=lambda x: -x.rating)
        n = len(self.contestants)

        correction = int(np.trunc(-sum(c.delta for c in self.contestants) / n)) - 1
        self.adjustment = correction
        for c in self.contestants:
            c.delta += correction

        zero_sum_count = min(4 * int(np.round(np.sqrt(n))), n)
        delta_sum = sum(self.contestants[i].delta for i in range(zero_sum_count))
        correction = min(max(int(np.trunc(-delta_sum / zero_sum_count)), -10), 0)
        self.adjustment += correction
        for c in self.contestants:
            c.delta += correction

    def calc_perfs(self):
        """
        This is not perfect, but close enough. The difference is caused by the adjustment value,
        which can change slightly when the rating of a single user, the user for whom we're
        calculating performance, varies.
        Tests on some selected contests show (this perf - true perf) lie in [0, 4].
        """
        for c in self.contestants:
            if c.rank == 1:
                c.performance = float('inf')  # Rank 1 always gains rating
            else:
                c.performance = binary_search(MIN_RATING_LIMIT, MAX_RATING_LIMIT,
                                              lambda x: self.calc_delta(c, x) + self.adjustment <= 0)


def predict(contestants: list[Contestant], calc_perfs: bool = False) -> dict[str, PredictResult]:
    calculator = RatingCalculator(contestants)
    calculator.calculate_deltas(calc_perfs)
    return {c.handle: PredictResult(c.rank,
                                    c.real_change[0] if c.real_change is not None else c.rating,
                                    c.real_change[1] - c.real_change[0] if c.real_change is not None else c.delta,
                                    c.performance)
            for c in contestants}
