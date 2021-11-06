from abc import ABC, abstractmethod

from astrobox.core import MotherShip, Asteroid, Drone

from yurikov_team import utils

LOAD_TASK = 'load_task'
UNLOAD_TASK = 'unload_task'


class DroneState(ABC):
    """
    Базовый класс состояния дрона.

    """

    def __init__(self, drone):
        self.drone = drone
        self.is_active = False

    def handle_action(self) -> Asteroid or MotherShip:
        """
        Метод обработки действия внутри состояния.

        Ищет и возвращает цель для перемещения или поворота.

        Если задача для перемещения "на выгрузку":
            ! возвращает объект союзной базы.

        Если задача для перемещения "на загрузку":
            ! если список вражеских баз для дрона не пустой:
                возвращает объект первой непустой и разрушенной базы.
            ! иначе:
                формирует список отношений (для каждого астероида) и возвращает самый "выгодный" астероид.
            ! если же все астероиды пустые:
                устанавливает задачу для перемещения - "на выгрузку";
                возвращает объект союзной базы.

        :return: Asteroid or MotherShip object, цель для перемещения или поворота - астероид или база
        """

        if self.drone.task == UNLOAD_TASK:
            return self.drone.my_mothership

        elif self.drone.task == LOAD_TASK:
            for base in self.drone.enemy_bases:
                if not base.is_empty and not base.is_alive:
                    return base

            relations = []
            for obj in self.drone.asteroids:
                if not obj.is_empty:
                    rel = obj.payload / self.drone.my_mothership.distance_to(obj)
                    relations.append((obj, rel))

            relations.sort(key=lambda k: k[1], reverse=True)

            for asteroid, rel in relations:
                if len(relations) >= 5:
                    if asteroid.worker is None:
                        if not self.drone.is_transition_started:
                            asteroid.worker = self.drone
                        return asteroid
                else:
                    return asteroid

            else:
                self.drone.task = UNLOAD_TASK
                return self.drone.my_mothership

    @abstractmethod
    def on_heartbeat(self) -> None:
        """
        Выполняется при каждом шаге игры.

        Реализуется в потомках класса.
        """

        pass


class MoveState(DroneState):
    """
    Класс состояния "перемещения".

    """

    def on_heartbeat(self) -> None:
        """
        Выполняется при каждом шаге игры.

        Если состояние активировано (является текущим состоянием дрона):
            ! если цель во время перемещения к ней осталась без ресурса:
                получает цель для перемещения из обработки внутри состояния и движется к ней.

            ! если завершился процесс загрузки/выгрузки ресурса:
                удаляет "рабочего" с текущей цели дрона (если цель - астероид);

                если трюм дрона не заполнен:
                    следующая задача - "на загрузку";
                иначе:
                    следующая задача - "на выгрузку";

                получает цель для перемещения из обработки внутри состояния и движется к ней.

        :return: None
        """

        if self.is_active:
            if self.drone.target and self.drone.target.is_empty:
                self.drone.target = self.handle_action()
                self.drone.move_at(self.drone.target)

            if self.drone.is_transition_finished:
                self.drone.is_transition_finished = False

                if isinstance(self.drone.target, Asteroid):
                    self.drone.target.worker = None

                if not self.drone.is_full:
                    self.drone.task = LOAD_TASK
                else:
                    self.drone.task = UNLOAD_TASK

                self.drone.target = self.handle_action()
                self.drone.move_at(self.drone.target)


class TransitionState(DroneState):
    """
    Класс состояния "перекачки ресурса".

    """

    def on_heartbeat(self) -> None:
        """
        Выполняется при каждом шаге игры.

        Если состояние активировано (является текущим состоянием дрона):
            ! если текущая цель дрона не является объектом союзной базы,
            ! а загруженность дрона + кол-во ресурса на астероиде >= 100:
                следующая задача - "на выгрузку";
            ! иначе:
                следующая задача - "на загрузку";

            ! получает следующую предполагаемую цель дрона из обработки внутри состояния и поворачивается к ней.

        :return: None
        """

        if self.is_active:
            _res_payload = self.drone.payload + self.drone.target.payload

            if self.drone.target != self.drone.my_mothership and _res_payload >= 100:
                self.drone.task = UNLOAD_TASK
            else:
                self.drone.task = LOAD_TASK

            self.drone.target_to_turn = self.handle_action()
            self.drone.turn_to(self.drone.target_to_turn)


class TurretState(DroneState):
    """
    Класс состояния "турель".

    """

    def handle_action(self) -> Drone or MotherShip:
        """
        Метод обработки действия внутри состояния.

        Ищет и возвращает ближайшую к союзной базе цель для атаки.

        :return: Drone or MotherShip object, объект для атаки
        """

        relations = []

        for i, drone in enumerate(self.drone.enemy_drones):
            rel = self.drone.my_mothership.distance_to(drone)
            relations.append((drone, rel))

        relations.sort(key=lambda k: k[1])

        enemy_targets = [enemy[0] for enemy in relations] + self.drone.enemy_bases
        if enemy_targets:
            return enemy_targets[0]
        else:
            self.is_active = False
            return None

    def on_heartbeat(self) -> None:
        """
        Выполняется при каждом шаге игры.

        Если состояние активировано (является текущим состоянием дрона)
        и дрон не находится в процессе перегруппировки:

            ! если прочность щита дрона упала ниже 40%:
                сбрасывает свою текущую цель для атаки;
                возвращается на базу;

            ! если цель дрона уничтожена:
                удаляет цель из списка вражеских дронов/баз для дрона;
                сбрасывает свою текущую цель для атаки;

                если списки вражеских дронов и баз пустые:
                    деактивирует состояние;
                    заново формирует списки вражеских баз;
                иначе:
                    возвращается в точку "турели";

            ! если дрон нацелен на врага:

                если на линии огня есть союзник:
                    выполняет "перегруппировку";
                иначе:
                    стреляет во врага;

            ! иначе:
                поворачивается к врагу



        :return: None
        """

        if self.is_active and not self.drone.in_regroup_move:

            if self.drone.meter_2 < .4:
                self.drone.in_regroup_move = True
                self.drone.target = None
                self.drone.move_at(self.drone.my_mothership)

            elif not self.drone.target.is_alive:

                if isinstance(self.drone.target, MotherShip):
                    self.drone.enemy_bases.clear()
                else:
                    self.drone.enemy_drones.remove(self.drone.target)

                self.drone.target = None

                if not self.drone.enemy_drones:
                    if not self.drone.enemy_bases:
                        self.is_active = False
                        self.drone.enemy_bases = [m_ship for m_ship in self.drone.scene.motherships
                                                  if m_ship != self.drone.my_mothership]

                    self.drone.enemy_bases.sort(key=lambda b: b.payload, reverse=True)

                elif self.drone.distance_to(self.drone.turret_point) > 1.0 and self.drone.enemy_drones:
                    self.drone.in_regroup_move = True
                    self.drone.move_at(self.drone.turret_point)

            else:
                _is_enemy = utils.check_for_enemy(self.drone, self.drone.target)
                _teammate_on_firing_line = utils.check_for_teammates(self.drone)

                if _is_enemy:
                    _delta_l = self.drone.distance_to(self.drone.target) - self.drone.gun.shot_distance

                    if _delta_l > 0:
                        self.drone.in_regroup_move = True
                        _length = 1.0 if self.drone.enemy_drones else _delta_l
                        _fire_point = utils.get_next_point(self.drone.coord, self.drone.direction, _length)
                        self.drone.move_at(_fire_point)

                    elif _teammate_on_firing_line != self.drone:
                        self.drone.in_regroup_move = True
                        _regroup_point = utils.get_regroup_point(self.drone, _teammate_on_firing_line)
                        _objects = self.drone.scene.motherships
                        res_point = utils.normalize_point(_regroup_point, self.drone.my_mothership,
                                                          self.drone.radius, _objects)
                        if self.drone.distance_to(res_point) > 1.0:
                            self.drone.move_at(res_point)
                        else:
                            self.drone.move_at(self.drone.my_mothership)

                    else:
                        self.drone.gun.shot(self.drone.target)
                else:
                    self.drone.turn_to(self.drone.target)