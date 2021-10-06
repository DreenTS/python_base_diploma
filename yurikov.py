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
        self.asteroids_with_distance = [(astr, self.my_mothership.distance_to(astr)) for astr in self.asteroids]
        self.asteroids_with_distance.sort(key=lambda k: k[1], reverse=True)
        self.target = self.asteroids_with_distance[0][0]
        self.move_at(self.target)

    def _get_point_to_act(self, action):
        res_target = self.my_mothership

        if action == UNLOAD:
            loc_distance = self.my_mothership.distance_to(self.target)
            index = self.asteroids_with_distance.index((self.target, loc_distance)) + 1
        else:
            index = 0

        for astrd_with_dist in self.asteroids_with_distance[index:]:
            astrd = astrd_with_dist[0]
            if action == LOAD:
                if not astrd.is_empty:
                    res_target = astrd
                    break
            if action == UNLOAD:
                if not astrd.is_full:
                    res_target = astrd
                    break

        return res_target

    def on_stop_at_asteroid(self, asteroid):
        if self.action == LOAD:
            self.load_from(asteroid)
        else:
            self.unload_to(asteroid)

    def on_load_complete(self):
        if self.is_full:
            self.action = UNLOAD
            self.target = self._get_point_to_act(action=self.action)
            self.move_at(self.target)
        else:
            self.action = LOAD
            self.target = self._get_point_to_act(action=self.action)
            self.move_at(self.target)

    def on_stop_at_mothership(self, mothership):
        self.unload_to(mothership)

    def on_unload_complete(self):
        if self._check_for_end():
            if self.manager.need_log:
                self.manager._log_stats()
        else:
            if self.is_empty:
                self.action = LOAD
                self.target = self._get_point_to_act(action=self.action)
            else:
                self.action = UNLOAD
                self.target = self._get_point_to_act(action=self.action)
            self.move_at(self.target)

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

