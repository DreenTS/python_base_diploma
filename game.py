# -*- coding: utf-8 -*-

from astrobox.space_field import SpaceField

from yurikov_drone_files.yurikov import YurikovDrone
from yurikov_drone_files import settings

if __name__ == '__main__':
    scene = SpaceField(
        speed=settings.DRONES_SPEED,
        asteroids_count=settings.ASTEROIDS_AMOUNT,
    )
    drones = [YurikovDrone() for _ in range(settings.DRONES_AMOUNT)]
    scene.go()

# Второй этап: зачёт!
