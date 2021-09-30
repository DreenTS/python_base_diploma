# -*- coding: utf-8 -*-

from astrobox.space_field import SpaceField

from yurikov import CollectorXXI


if __name__ == '__main__':
    scene = SpaceField(
        speed=6,
        asteroids_count=5,
    )
    d = CollectorXXI()
    scene.go()

