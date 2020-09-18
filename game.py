# -*- coding: utf-8 -*-

# pip install -r requirements.txt

from astrobox.space_field import SpaceField
# TODO класс своего дрона назвать по особенному
#  и вынести в отдельный модуль. Модуль назвать своей фамилией
from vader import VaderDrone


if __name__ == '__main__':
    scene = SpaceField(
        speed=3,
        asteroids_count=5,
    )
    d = VaderDrone()
    scene.go()

