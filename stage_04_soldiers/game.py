# -*- coding: utf-8 -*-

# pip install -r requirements.txt

from astrobox.space_field import SpaceField
from stage_03_harvesters.driller import DrillerDrone
from stage_03_harvesters.reaper import ReaperDrone
from stage_04_soldiers.devastator import DevastatorDrone
from yurikov_team.yurikov import YurikovDrone

import yurikov_team.settings as settings


if __name__ == '__main__':
    scene = SpaceField(
        field=settings.FIELD_SIZE,
        speed=settings.DRONES_SPEED,
        asteroids_count=settings.ASTEROIDS_AMOUNT,
        can_fight=True,
    )

    team_1 = [YurikovDrone() for _ in range(settings.DRONES_AMOUNT)]

    team_2 = [ReaperDrone() for _ in range(settings.DRONES_AMOUNT)]
    team_3 = [DrillerDrone() for _ in range(settings.DRONES_AMOUNT)]
    team_4 = [DevastatorDrone() for _ in range(settings.DRONES_AMOUNT)]

    scene.go()

# TODO - Пока ваши дроны не выигрывают. Кроме того, время игры ограничено 17000 шагами
#  Победитель определяется из живых баз по количеству элериума
