from astrobox.core import Drone

FAR = max
NEAR = min


class YurikovDrone(Drone):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.my_team = []

    def on_born(self):
        self.target = self._get_my_asteroid(mode_func=FAR)
        self.move_at(self.target)
        self.my_team.append(self)

    def _get_my_asteroid(self, mode_func):
        res_target = (0, self.my_mothership)
        curr_asteroid_distance_list = []

        for astr in self.asteroids:
            if not astr.is_empty:
                curr_asteroid_distance_list.append((self.distance_to(astr), astr))

        if curr_asteroid_distance_list:
            res_target = mode_func(curr_asteroid_distance_list)

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
