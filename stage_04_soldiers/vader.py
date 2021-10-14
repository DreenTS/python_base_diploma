# -*- coding: utf-8 -*-

from astrobox.core import Drone


class VaderDrone(Drone):
    my_team = []

    def on_born(self):
        self.target = self._get_my_asteroid()
        self.move_at(self.target)
        self.my_team.append(self)

    def _get_my_asteroid(self):
        asteroids_with_elerium = set(aster for aster in self.asteroids if aster.payload)
        asteroids_as_targets = set(drone.target for drone in self.my_team)
        free_asteroids = asteroids_with_elerium - asteroids_as_targets
        if free_asteroids:
            return free_asteroids.pop()

    def on_stop_at_asteroid(self, asteroid):
        self.load_from(asteroid)

    def on_load_complete(self):
        self.move_at(self.my_mothership)

    def on_stop_at_mothership(self, mothership):
        self.unload_to(mothership)

    def on_unload_complete(self):
        self.move_at(self.target)

    def on_wake_up(self):
        self.target = self._get_my_asteroid()
        if self.target:
            self.move_at(self.target)


