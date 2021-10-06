from astrobox.core import Drone

from log_config import configure_logger

LOAD = 'load'
UNLOAD = 'unload'


class SpaceLogger:

    def __init__(self, data):
        self.logger = configure_logger()
        self.data = data

    def log(self):
        res = 'Run stats:\n'
        for k, v in self.data.items():
            res += f'{k} = {v}\n'
        self.logger.info(res)
        print('\nLOGGING COMPLETED SUCCESSFULLY!\n')


class YurikovDrone(Drone):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.action = LOAD
        self.asteroids_with_distance = None
        self.role = 'manager'
        self.stats = {
            'empty_range': 0,
            'fully_range': 0,
            'not_fully_range': 0,
        }
        temp_managers_list = [mate for mate in self.teammates if mate.role == 'manager']
        if temp_managers_list:
            self.role = 'worker'
            self.manager = temp_managers_list[0]
            self.need_log = False
        else:

            self.manager = self
            self.need_log = True

    def move_at(self, *args, **kwargs):
        self._update_stats(*args)
        super().move_at(*args, **kwargs)

    def on_born(self):
        if self.ROLE == 'manager':
            self._add_worker_field()
        self.target = self._get_my_asteroid(mode_func=FAR)
        self.move_at(self.target)

    def _get_my_asteroid(self, mode_func):
        res_target = (0, self.my_mothership)
        curr_asteroid_distance_list = []

        for astr in self.asteroids:
            if not astr.is_empty and astr.worker is None:
                curr_asteroid_distance_list.append((self.distance_to(astr), astr))

        if curr_asteroid_distance_list:
            res_target = mode_func(curr_asteroid_distance_list)
            res_target[1].worker = self

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
        if self._check_for_end():
            if self.manager.need_log:
                self.manager._log_stats()
        else:
            if self.target.is_empty:
                self.target = self._get_my_asteroid(mode_func=FAR)
            self.move_at(self.target)

    def _add_worker_field(self):
        for astr in self.asteroids:
            astr.worker = None

    def _update_stats(self, target):
        if self.is_empty:
            self.manager.stats['empty_range'] += self.distance_to(target)
        elif self.is_full:
            self.manager.stats['fully_range'] += self.distance_to(target)
        else:
            self.manager.stats['not_fully_range'] += self.distance_to(target)

    def _check_for_end(self):
        check_list = self.teammates + self.asteroids
        is_empty_for_end = [obj.is_empty for obj in check_list]
        is_empty_for_end.append(self.is_empty)
        return all(is_empty_for_end)

    def _log_stats(self):
        self.need_log = False
        logger = SpaceLogger(data=self.stats)
        logger.log()

