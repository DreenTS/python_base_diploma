import math
from astrobox.core import MotherShip, Drone
from robogame_engine.geometry import Point, Vector


def get_turret_point(src: Drone) -> Point:
    """
    Получить точку "турели" около своей базы.

    Координаты точки будут меняться в зависимости от положения базы на игровом поле.

    :param src: Drone object, дрон, для которого высчитываем положение точки
    :return: Point, точка "турели"
    """

    team_turret_extra_data = {
        1: [0.0, (0.0, 0.0)],
        2: [90.0, (src.scene.field[0], 0)],
        3: [270.0, (0, src.scene.field[1])],
        4: [180.0, (src.scene.field[0], src.scene.field[1])],
    }

    extra_angle, extra_coords = team_turret_extra_data[src.team_number]
    main_angle = 90 / (len(src.scene.teams[0]) + 1)
    angle_coeff = src.id % len(src.scene.teams[0]) + 1
    radius = (src.radius + src.my_mothership.radius) * 2

    curr_angle = extra_angle + main_angle * angle_coeff

    next_x = extra_coords[0] + radius * math.cos(math.radians(curr_angle))
    next_y = extra_coords[1] + radius * math.sin(math.radians(curr_angle))

    return Point(next_x, next_y)


def get_combat_point(src: Drone, target: Drone or MotherShip) -> Point:
    """
    Получить точку для атаки на цель.

    Координаты точки будут меняться в зависимости от точек атаки союзников.

    :param src: Drone object, дрон, для которого высчитываем положение точки
    :param target: Drone or MotherShip object, цель для атаки
    :return: Point, точка атаки
    """

    center = Point(src.scene.field[0] / 2, src.scene.field[1] / 2)
    direction_to_center = Vector.from_points(src.coord, center).direction
    direction_to_target = Vector.from_points(src.coord, target.coord).direction
    delta = get_delta_angle(direction_to_target, direction_to_center)
    if delta > 0:
        angle_direction = src.id % len(src.scene.teams[0])
    else:
        angle_direction = (src.id % len(src.scene.teams[0])) * -1

    valid_range_radius = src.gun.shot_distance + src.gun.projectile.radius
    range_radius = src.my_mothership.distance_to(target) - (src.my_mothership.radius + src.gun.projectile.radius)
    if range_radius < valid_range_radius:
        radius = range_radius
    else:
        radius = valid_range_radius

    extra_angle = math.degrees(math.atan(src.radius * 2 / radius))
    angle = (direction_to_target + 180) % 360 + extra_angle * angle_direction
    next_x = target.x + radius * math.cos(math.radians(angle))
    next_y = target.y + radius * math.sin(math.radians(angle))

    _point = Point(next_x, next_y)

    res_point = normalize_point(src=src, point=_point, radius=src.radius)

    return res_point


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
    return abs(delta) <= angle


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
            return mate

        angle = get_firing_angle(shooter=src, target=mate)
        direction_to_mate = Vector.from_points(src.coord, mate.coord).direction
        delta = get_delta_angle(a_angle=src.direction, b_angle=direction_to_mate)
        if abs(delta) <= angle:
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
    if shooter.team == target.team:
        a += 0.1
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
        return delta + 2 * 180
    elif delta > 180:
        return delta - 2 * 180
    else:
        return delta


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


def normalize_point(src: Drone, point: Point, radius: float) -> Point:
    """
    Нормализовать точку.
    Если точка выходит за границы игрового поля:
        возвращает ближайшие к границе допустимые значения x и y.

    :param src: Drone, дрон-источник
    :param point: Point, текущая точка
    :param radius: float, радиус объекта, чья точка была передана как параметр point
    :return: Point, нормализованная точка
    """

    x_list = [radius + 2, src.scene.field[0] - radius - 2, point.x]
    y_list = [radius + 2, src.scene.field[1] - radius - 2, point.y]

    x_list.sort()
    y_list.sort()

    _point = Point(x_list[1], y_list[1])

    return _point


def is_base_in_danger(src: Drone, turret_point: Point, target: Drone or MotherShip) -> bool:
    """
    Проверить, находится ли союзная база в опасности.

    :param src: Drone object, дрон-источник
    :param turret_point: Point, точка "турели" для дрона-источника
    :param target: Drone or MotherShip object, текущая цель атаки для дрона-источника
    :return: bool, находится ли текущая цель в опасной близости к союзной базе
    """

    _extra_dist = turret_point.distance_to(src.my_mothership)
    _danger_dist = src.gun.shot_distance
    _from_mother_to_enemy = src.my_mothership.distance_to(target) - _extra_dist
    return _from_mother_to_enemy <= _danger_dist
