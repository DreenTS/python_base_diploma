from astrobox.core import Drone

from log_config import configure_logger

FAR = max
NEAR = min


class YurikovDrone(Drone):

    STATS = {
        'empty_range': 0,
        'fully_range': 0,
        'not_fully_range': 0,
    }

    ROLE = 'manager'

    def move_at(self, *args, **kwargs):
        self._update_stats(*args)
        super().move_at(*args, **kwargs)

    def on_born(self):
        if 'manager' in [mate.ROLE for mate in self.teammates]:
            self.ROLE = 'worker'
        self.target = self._get_my_asteroid(mode_func=FAR)
        self.move_at(self.target)

    def _get_my_asteroid(self, mode_func):
        res_target = (0, self.my_mothership)
        curr_asteroid_distance_list = []

        for astr in self.asteroids:
            if not astr.is_empty:
                curr_asteroid_distance_list.append((self.distance_to(astr), astr))

        if curr_asteroid_distance_list:
            res_target = mode_func(curr_asteroid_distance_list)
        elif self.ROLE == 'manager':
            self.drone_logger = configure_logger()
            self._log_stats()

        return res_target[1]

    def on_stop_at_asteroid(self, asteroid):
        self.load_from(asteroid)

    def on_load_complete(self):
        if not self.is_full:
            self.target = self._get_my_asteroid(mode_func=NEAR)
            self.move_at(self.target)
        else:
            self.move_at(self.my_mothership)

    def on_stop_at_mothership(self, mothership):
        self.unload_to(mothership)

    def on_unload_complete(self):
        if self.target.is_empty:
            self.target = self._get_my_asteroid(mode_func=FAR)
        self.move_at(self.target)

    def _update_stats(self, target):
        if self.is_empty:
            self.STATS['empty_range'] += self.distance_to(target)
        elif self.is_full:
            self.STATS['fully_range'] += self.distance_to(target)
        else:
            self.STATS['not_fully_range'] += self.distance_to(target)

    def _log_stats(self):
        for mate in self.teammates:
            for k, v in mate.STATS.items():
                self.STATS[k] += v
        self._update_stats(target=self.my_mothership)
        res = 'Run stats:\n'
        for k, v in self.STATS.items():
            res += f'{k} = {v}\n'
        self.drone_logger.info(res)
