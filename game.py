# -*- coding: utf-8 -*-

from astrobox.space_field import SpaceField

from yurikov import YurikovDrone

if __name__ == '__main__':
    scene = SpaceField(
        speed=3,
        asteroids_count=5,
    )
    d = YurikovDrone()
    scene.go()

