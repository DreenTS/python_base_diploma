import math
import random

from typing import List

from astrobox.core import MotherShip, Drone
from robogame_engine.geometry import Point, Vector

from yurikov_team import settings


def get_turret_point(src: Drone, index: int) -> Point:
    """
    Получить точку "турели" около своей базы.

    Координаты точки будут меняться в зависимости от положения базы на игровом поле.

    :param src: Drone object, дрон, для которого высчитываем положение точки
    :param index: int, индекс дрона на игровом поле (его ID)
    :return: Point, точка "турели"
    """

    extra_angle, extra_coords = settings.TEAM_TURRET_EXTRA_DATA[src.team_number]
    main_angle = 90 / (len(src.teammates) + 2)
    angle_coeff = index % settings.DRONES_AMOUNT + 1
    radius = (src.radius + src.my_mothership.radius) * 2

    curr_angle = extra_angle + main_angle * angle_coeff

    next_x = extra_coords[0] + radius * math.cos(math.radians(curr_angle))
    next_y = extra_coords[1] + radius * math.sin(math.radians(curr_angle))

    return Point(next_x, next_y)


def check_for_enemy(src: Drone, enemy: Drone or MotherShip) -> bool:
    """
    Проверить, нацелен ли в данный момент дрон на врага.

    :param src: Drone object, дрон-источник
    :param enemy: Drone or MotherShip object, объект вражеского дрона или базы, на который нацелен дрон-источник
    :return: bool, находится ли враг на линии огня (попадает в угол)
    """

    angle = get_firing_angle(shooter=src, target=enemy)
    direction_to_enemy = Vector.from_points(src.coord, enemy.coord).direction
    delta = get_delta_angle(a_angle=src.direction, b_angle=direction_to_enemy)
    return delta <= angle


def check_for_teammates(src: Drone) -> Drone or MotherShip:
    """
    Проверить, находится ли какой-либо союзник на линии огня.

    :param src: Drone object, дрон-источник
    :return: Drone or MotherShip object, объект союзного дрона или базы, находящийся на линии огня дрона-источника
    """

    my_mates = [mate for mate in src.teammates + [src.my_mothership] if mate.is_alive]

    for mate in my_mates:
        _mate_to_base = mate.distance_to(src.my_mothership)
        _src_to_base = src.distance_to(src.my_mothership)
        if src.distance_to(mate) <= mate.radius + src.gun.projectile.radius:
            if _mate_to_base > _src_to_base:
                return mate

        angle = get_firing_angle(shooter=src, target=mate)
        direction_to_mate = Vector.from_points(src.coord, mate.coord).direction
        delta = get_delta_angle(a_angle=src.direction, b_angle=direction_to_mate)
        if delta <= angle:
            return mate

    return src


def get_firing_angle(shooter: Drone, target: Drone or MotherShip) -> float:
    """
    Получить угол "линии огня".

    :param shooter: Drone object, дрон-стрелок
    :param target: Drone or MotherShip object, дрон- или база-цель
    :return: float, угол "линии огня"
    """

    a = shooter.distance_to(target)
    b = shooter.gun.projectile.radius + target.radius
    return math.degrees(math.atan(b / a))


def get_delta_angle(a_angle: float, b_angle: float) -> float:
    """
    Получить разницу между двумя углами (в градусах).

    :param a_angle: float, первый угол (альфа)
    :param b_angle: float, второй угол (бета)
    :return: float, разница между углами
    """

    delta = a_angle - b_angle

    if delta < -180:
        return abs(delta + 2 * 180)
    elif delta > 180:
        return abs(delta - 2 * 180)
    else:
        return abs(delta)


def get_next_point(point: Point, angle: float, length: float) -> Point:
    """
    Получить следующую точку для перемещения
    (откладывание отрезка заданной длины на заданный угол).

    :param point: Point, текущая точка
    :param angle: float, угол поворота отрезка
    :param length: float, длина отрезка
    :return: Point, следующая точка для перемещения
    """

    _angle = math.radians(angle)
    next_x = point.x + math.cos(_angle) * length
    next_y = point.y + math.sin(_angle) * length
    return Point(next_x, next_y)


def get_regroup_point(src: Drone, mate: Drone or MotherShip) -> Point:
    """
    Получить точку "регруппировки".

    :param src: Drone object, дрон-источник
    :param mate: Drone or MotherShip object, объект союзного дрона или базы
    :return: Point, точка "регруппировки"
    """

    _angle = 90 * random.choice([-1, 1])
    _length = mate.radius * 2
    return get_next_point(src.coord, _angle, _length)


def normalize_point(point: Point, mother: MotherShip, radius: float, objects: List[MotherShip] = None) -> Point:
    """
    Нормализовать точку.

    Если точка выходит за границы игрового поля:
        ! возвращает ближайшие к границе допустимые значения x и y.
    Если передан параметр objects:
        ! проходится по списку объектов;
        ! если расстояние от текущей точки до объекта меньше суммы их радиусов:
            возращает координаты базы;

    :param point: Point, текущая точка
    :param mother: MotherShip object, объект союзной базы
    :param radius: float, радиус объекта, чья точка была передана как параметр point
    :param objects: list, список всех баз, находящихся на игровом поле
    :return: Point, нормализованная точка
    """

    objects = objects or []

    x_list = [radius + 2, settings.FIELD_SIZE[0] - radius - 2, point.x]
    y_list = [radius + 2, settings.FIELD_SIZE[1] - radius - 2, point.y]

    x_list.sort()
    y_list.sort()

    _point = Point(x_list[1], y_list[1])

    for obj in objects:
        if _point.distance_to(obj) <= obj.radius + radius:
            return mother.coord

    return _point

