# -*- coding: utf-8 -*-

from astrobox.space_field import SpaceField
from stage_03_harvesters.driller import DrillerDrone

from yurikov_drone_files.yurikov import YurikovDrone
import yurikov_drone_files.settings as settings


if __name__ == '__main__':
    scene = SpaceField(
        speed=settings.DRONES_SPEED,
        asteroids_count=settings.ASTEROIDS_AMOUNT,
    )

    team_1 = [YurikovDrone() for _ in range(settings.DRONES_AMOUNT)]

    # team_2 = [ReaperDrone() for _ in range(settings.DRONES_AMOUNT)]

    team_3 = [DrillerDrone() for _ in range(settings.DRONES_AMOUNT)]

    scene.go()

# Победы 3/10 - недостаточно для зачета
# TODO - Улучшить алгоритм
#  Начинать сбор с астеройдов из средней полосы
#  Пытаться собирать так, чтобы можно было загружиться с одного раза

