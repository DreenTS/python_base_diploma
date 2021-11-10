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
            возвращает объект союзной базы.

        Если задача для перемещения "на загрузку":
            если список вражеских баз для менеджера не пустой:
                возвращает объект первой непустой и разрушенной базы.
            иначе:
                формирует список отношений (для каждого астероида) и возвращает самый "выгодный" астероид.

            если все астероиды пустые:
                устанавливает задачу для перемещения - "на выгрузку";
                возвращает объект союзной базы.

        :return: Asteroid or MotherShip object, цель для перемещения или поворота - астероид или база
        """

        if self.drone.task == UNLOAD_TASK:
            return self.drone.my_mothership

        elif self.drone.task == LOAD_TASK:
            for base in self.drone.manager.enemy_bases:
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
    Класс состояния "перемещение".

    """

    def on_heartbeat(self) -> None:
        """
        Выполняется при каждом шаге игры.

        Если цель во время перемещения к ней осталась без ресурса:
            получает цель для перемещения из обработки внутри состояния и движется к ней.

        Если завершился процесс загрузки/выгрузки ресурса:
            удаляет "рабочего" с текущей цели дрона (если цель - астероид);

            если трюм дрона не заполнен:
                следующая задача - "на загрузку";
            иначе:
                следующая задача - "на выгрузку";

            получает цель для перемещения из обработки внутри состояния и движется к ней.

        :return: None
        """

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
    Класс состояния "перекачка ресурса".

    """

    def on_heartbeat(self) -> None:
        """
        Выполняется при каждом шаге игры.

        Если текущая цель дрона не является объектом союзной базы,
        а загруженность дрона + кол-во ресурса на астероиде >= 100:
            следующая задача - "на выгрузку".
        Иначе:
            следующая задача - "на загрузку".

        Получает следующую предполагаемую цель дрона из обработки внутри состояния и поворачивается к ней.

        :return: None
        """

        _res_payload = self.drone.payload + self.drone.target.payload

        if self.drone.target != self.drone.my_mothership and _res_payload >= 100:
            self.drone.task = UNLOAD_TASK
        else:
            self.drone.task = LOAD_TASK

        self.drone.target_to_turn = self.handle_action()
        self.drone.turn_to(self.drone.target_to_turn)


class CombatState(DroneState):
    """
    Класс состояния "сражение".

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shots = 0

    def handle_action(self) -> Drone or MotherShip or None:
        """
        Метод обработки действия внутри состояния.

        Ищет и возвращает ближайшую к союзной базе цель для атаки.

        :return: Drone or MotherShip object, объект для атаки
        """

        relations = []
        enemy_is_near = []
        manager = self.drone.manager
        extra_dist = manager.turret_point.distance_to(manager.my_mothership)
        danger_dist = manager.gun.shot_distance

        for i, drone in enumerate(manager.enemy_drones):
            from_mother_to_enemy = manager.my_mothership.distance_to(drone) - extra_dist
            if from_mother_to_enemy <= danger_dist:
                enemy_is_near.append((drone, from_mother_to_enemy))
            else:
                rel = manager.my_mothership.distance_to(drone)
                relations.append((drone, rel))

        relations.sort(key=lambda k: k[1])
        enemy_is_near.sort(key=lambda k: k[1])

        enemy_targets = [enemy[0] for enemy in enemy_is_near + relations] + manager.enemy_bases
        if enemy_targets:
            return enemy_targets[0]
        else:
            self.drone.is_victory = True
            return

    def on_heartbeat(self) -> None:
        """
        Выполняется при каждом шаге игры.

        Проверяет, победила ли команда дрона (уничтожены все вражеские дроны и базы).
        Если дрон не находится "в боевом перемещении":

            если всем союзным дронам необходимо перегруппироваться:
                вызывает метод regroup();

            ! если прочность щита дрона упала ниже 40%:
                вызывает метод regroup();

            ! если цель дрона уничтожена:
                удаляет цель из списка вражеских дронов/баз для менеджера;
                сообщает всем союзникам, что необходимо перегруппироваться;

                если списки вражеских дронов и баз пустые:
                    сообщает всем союзникам, что команда победила;
                    заново формирует списки вражеских баз;

            !если было сделано 10 выстрелов подряд и (кол-во живых вражеских дронов) >= 3:
                вызывает метод regroup();

            ! если дрон нацелен на врага:

                если расстояние до врага меньше дистанции выстрела:
                    движется к врагу;

                ! если на линии огня есть союзник и дрон не находится в точке "турели":
                    вызывает метод regroup();
                иначе:
                    стреляет во врага;

            иначе:
                поворачивается к врагу



        :return: None
        """

        _is_victory = [mate.is_victory for mate in self.drone.teammates + [self.drone] if mate.is_alive]
        _all_need_regroup = [mate.need_to_regroup for mate in self.drone.teammates + [self.drone] if mate.is_alive]

        if any(_is_victory):
            self.drone.target = None
            self.drone.in_combat_move = False
            self.drone.is_victory = True
            self.is_active = False

        elif not self.drone.in_combat_move:
            if any(_all_need_regroup):
                self.drone.need_to_regroup = False
                self.regroup()

            elif self.drone.meter_2 < .4:
                if len(self.drone.manager.enemy_drones) <= 2:
                    self.regroup()
                else:
                    self.drone.need_to_regroup = True

            elif self.drone.target and not self.drone.target.is_alive:
                manager = self.drone.manager
                if isinstance(self.drone.target, MotherShip):
                    manager.enemy_bases.clear()
                else:
                    manager.enemy_drones = [drone for drone in manager.scene.drones
                                            if manager.team != drone.team and drone.is_alive]

                if not manager.enemy_drones:
                    if not manager.enemy_bases:
                        self.drone.is_victory = True
                        manager.enemy_bases = [m_ship for m_ship in manager.scene.motherships
                                               if m_ship != manager.my_mothership]
                    else:
                        self.drone.target = None
                    manager.enemy_bases.sort(key=lambda b: b.payload, reverse=True)
                else:
                    self.drone.need_to_regroup = True

            else:
                _is_enemy = utils.check_for_enemy(self.drone, self.drone.target)

                if self.shots == 10 and len(self.drone.manager.enemy_drones) > 3:
                    self.regroup()

                elif _is_enemy:
                    _delta_l = self.drone.distance_to(self.drone.target) - self.drone.gun.shot_distance
                    _teammate_on_firing_line = utils.check_for_teammates(self.drone)
                    _is_on_turret_point = self.drone.distance_to(self.drone.turret_point) < 1.0

                    if _delta_l > 0:
                        if _is_on_turret_point:
                            self.regroup()
                        else:
                            self.drone.combat_point = utils.get_next_point(self.drone.coord,
                                                                           self.drone.direction,
                                                                           _delta_l)
                            self.drone.move_at(self.drone.combat_point)

                    elif _teammate_on_firing_line != self.drone:
                        if _is_on_turret_point:
                            if self.drone.gun.can_shot:
                                self.shots += 1
                            self.drone.gun.shot(self.drone.target)
                        else:
                            self.regroup()

                    elif self.drone.gun.can_shot:
                        self.shots += 1
                        self.drone.gun.shot(self.drone.target)
                else:
                    self.drone.turn_to(self.drone.target)

    def regroup(self) -> None:
        """
        Метод подготовки и запуска перегруппировки.

        :return: None
        """

        self.shots = 0
        self.drone.target = None
        self.drone.combat_point = None
        if self.drone.curr_game_step > 400:
            self.drone.in_combat_move = True
            self.drone.move_at(self.drone.my_mothership)