import unittest
from copy import deepcopy
from unittest.mock import Mock

from robogame_engine.geometry import Point

import yurikov_team.utils as utils
from astrobox.core import MotherShip, Drone
from astrobox.guns import PlasmaProjectile


class UtilsTest(unittest.TestCase):

    # Координаты написаны только под разрешение игрового поля 1200x1200
    TURRET_COORDS = {
        1: [(232.1, 134.0), (189.5, 189.5), (134.0, 232.1), (69.4, 258.9), (258.9, 69.4), ],
        2: [(1066.0, 232.1), (1010.5, 189.5), (967.9, 134.0), (941.1, 69.4), (1130.6, 258.9), ],
        3: [(134.0, 967.9), (189.5, 1010.5), (232.1, 1066.0), (258.9, 1130.6), (69.4, 941.1), ],
        4: [(967.9, 1066.0), (1010.5, 1010.5), (1066.0, 967.9), (1130.6, 941.1), (941.1, 1130.6), ],
    }

    def setUp(self) -> None:
        self.drone_mock = Mock()
        self.drone_mock.radius = Drone.radius
        self.drone_mock.team = 'mock_team'
        self.drone_mock.my_mothership = Mock()
        self.mothership_mock = self.drone_mock.my_mothership
        self.mothership_mock.radius = MotherShip.radius
        self.drone_mock.gun = Mock()
        self.drone_mock.gun.shot_distance = PlasmaProjectile.max_distance
        self.drone_mock.gun.projectile.radius = PlasmaProjectile.radius
        self.drone_mock.scene = Mock()
        self.drone_mock.scene.field = (1200, 1200)

    def test_get_turret_point(self) -> None:
        self.drone_mock.scene.teams = {'mock_team': [0] * 5}
        self.drone_mock.id = 0
        result_list = []
        for team in range(4):
            self.drone_mock.team_number = team + 1
            for _ in range(5):
                self.drone_mock.id += 1
                result = utils.get_turret_point(src=self.drone_mock)
                temp_tuple = (round(result.x, 1), round(result.y, 1))
                result_list.append(temp_tuple)
            self.assertEqual(result_list, self.TURRET_COORDS[self.drone_mock.team_number])
            result_list.clear()

    def test_get_delta_angle(self) -> None:
        a, b = 90.0, 90.0
        result = utils.get_delta_angle(a_angle=a, b_angle=b)
        self.assertEqual(result, 0.0)
        a, b = 120.0, 90.0
        result = utils.get_delta_angle(a_angle=a, b_angle=b)
        self.assertEqual(result, 30.0)
        a, b = 90.0, 120.0
        result = utils.get_delta_angle(a_angle=a, b_angle=b)
        self.assertEqual(result, -30.0)
        a, b = 120.0, 1200.0
        result = utils.get_delta_angle(a_angle=a, b_angle=b)
        self.assertEqual(result, -720.0)
        a, b = 1200.0, 120.0
        result = utils.get_delta_angle(a_angle=a, b_angle=b)
        self.assertEqual(result, 720.0)

    def test_normalize_point(self) -> None:
        ok_x, ok_y = self.drone_mock.radius * 2, self.drone_mock.radius * 2

        # Точка входит в поле
        prev_point = Point(ok_x, ok_y)
        result = utils.normalize_point(src=self.drone_mock, point=prev_point, radius=self.drone_mock.radius)
        self.assertEqual(result.distance_to(prev_point), 0)

        # Точка за границами поля (x больше допустимого)
        prev_point = Point(self.drone_mock.scene.field[0], ok_y)
        new_point = Point(self.drone_mock.scene.field[0] - self.drone_mock.radius - 2, ok_y)
        result = utils.normalize_point(src=self.drone_mock, point=prev_point, radius=self.drone_mock.radius)
        self.assertEqual(result.distance_to(new_point), 0)

        # Точка за границами поля (x меньше допустимого)
        prev_point = Point(-3, ok_y)
        new_point = Point(self.drone_mock.radius + 2, ok_y)
        result = utils.normalize_point(src=self.drone_mock, point=prev_point, radius=self.drone_mock.radius)
        self.assertEqual(result.distance_to(new_point), 0)

        # Точка за границами поля (y больше допустимого)
        prev_point = Point(ok_x, self.drone_mock.scene.field[1])
        new_point = Point(ok_x, self.drone_mock.scene.field[1] - self.drone_mock.radius - 2)
        result = utils.normalize_point(src=self.drone_mock, point=prev_point, radius=self.drone_mock.radius)
        self.assertEqual(result.distance_to(new_point), 0)

        # Точка за границами поля (y меньше допустимого)
        prev_point = Point(ok_x, -3)
        new_point = Point(ok_x, self.drone_mock.radius + 2)
        result = utils.normalize_point(src=self.drone_mock, point=prev_point, radius=self.drone_mock.radius)
        self.assertEqual(result.distance_to(new_point), 0)

    def test_get_combat_point(self) -> None:
        self.drone_mock.scene.teams = {'mock_team': [0] * 5}
        self.drone_mock.id = 1
        self.drone_mock.coord = Point(200, 250)
        self.mothership_mock.coord = Point(90, 90)
        self.mothership_mock.distance_to = self.mothership_mock.coord.distance_to
        target_clone = Point(365, 340)
        target_clone.coord = Point(365, 340)
        result = utils.get_combat_point(src=self.drone_mock, target=target_clone)
        new_point = (round(result.x, 1), round(result.y, 1))
        self.assertEqual(new_point, (102.7, 292.1))

        # При выходе за границу игрового поля
        self.drone_mock.id = 2
        self.drone_mock.coord = Point(90, 90)
        self.mothership_mock.coord = Point(1110, 90)
        self.mothership_mock.distance_to = self.mothership_mock.coord.distance_to
        target_clone = Point(100, 100)
        target_clone.coord = Point(100, 100)
        result = utils.get_combat_point(src=self.drone_mock, target=target_clone)
        new_point = (round(result.x, 1), round(result.y, 1))
        self.assertEqual(new_point, (46, 46))

    def test_get_firing_angle(self) -> None:
        self.drone_mock.coord = Point(200, 100)
        self.drone_mock.distance_to = self.drone_mock.coord.distance_to

        # Угол "линии огня" с вражеским юнитом
        mock_enemy = Point(300, 200)
        mock_enemy.coord = Point(300, 200)
        mock_enemy.team = 'mock_enemy_team'
        mock_enemy.radius = Drone.radius
        result = utils.get_firing_angle(shooter=self.drone_mock, target=mock_enemy)
        self.assertEqual(result, 22.64555582103878)

        # Угол "линии огня" с союзным юнитом
        mock_enemy.team = 'mock_team'
        result = utils.get_firing_angle(shooter=self.drone_mock, target=mock_enemy)
        self.assertEqual(result, 22.631167949279153)


if __name__ == '__main__':
    unittest.main()
