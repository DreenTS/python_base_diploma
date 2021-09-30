# -*- coding: utf-8 -*-

from astrobox.space_field import SpaceField
# TODO - Переименуйте класс своего дрона по шаблону [Фамилия]Drone
from yurikov import CollectorXXI


if __name__ == '__main__':
    scene = SpaceField(
        speed=3,
        asteroids_count=5,
    )
    d = CollectorXXI()
    scene.go()

