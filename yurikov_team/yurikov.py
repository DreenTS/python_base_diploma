from astrobox.core import Drone, Asteroid, MotherShip
from robogame_engine.geometry import Point

import yurikov_team.states as states
from yurikov_team import utils, settings


class YurikovDrone(Drone):
    """
    Класс дрона.
    Если дронам разрешено стрелять - уничтожает всех соперников по карте.
    Собирает ресурс с астероидов и выгружает его на базе.

    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.states_handle_list = None
        self.curr_state = None
        self.turret_point = None
        self.combat_point = None
        self.need_to_regroup = False
        self.in_combat_move = False
        self.is_victory = False
        self.enemy_drones = None
        self.enemy_bases = None
        self.task = None
        self.is_transition_started = False
        self.is_transition_finished = True
        self.target_to_turn = None

        _temp_managers_list = [mate for mate in self.teammates if mate.is_manager]
        if _temp_managers_list:
            self.is_manager = False
            self.manager = _temp_managers_list[0]
        else:
            self.is_manager = True
            self.manager = self

    def on_heartbeat(self) -> None:
        """
        Выполняется при каждом шаге игры.

        Если текущее состояние дрона деактивировано:
            меняет сстояние.

        Если дрону не назначена цель, получает её из обработки внутри состояния.
        Если текущее состояние - "сражение", то выбирает позицию для перемещения и движется к ней.

        Вызывает метод состояния дрона on_heartbeat().

        (подробнее см. docstrings методов состояний в states.py).

        :return: None
        """

        if not self.curr_state.is_active:
            self.switch_state()

        if self.target is None and not self.in_combat_move:
            self.target = self.curr_state.handle_action()

            if isinstance(self.curr_state, states.CombatState):
                self.in_combat_move = True
                _extra_dist = self.turret_point.distance_to(self.my_mothership)
                _danger_dist = self.gun.shot_distance
                _from_mother_to_enemy = self.my_mothership.distance_to(self.target) - _extra_dist
                if _from_mother_to_enemy <= _danger_dist and len(self.manager.enemy_drones) > 3:
                    self.move_at(self.turret_point)
                else:
                    self.combat_point = utils.get_combat_point(self, self.target)
                    self.move_at(self.combat_point)

        self.curr_state.on_heartbeat()

    def on_born(self) -> None:
        """
        Вызывается единожды при "рождении" дрона.

        Если дрон является "менеджером":
            добавляет всем астероидам на сцене атрибут worker
                (в ходе игры распределение следующее: на 1 астероиде может работать 1 дрон);
            формирует два списка: с объектами вражеских дронов и вражеских баз.

        Устанавливает задачу для перемещения - "на загрузку".
        Добавляет в список состояний объекты классов состояний (подробнее о классах см. docstrings классов).
        Вызывает метод переключения состояния switch_state()
        (подробнее см. docstrings метода).

        Получает точку "турели" около своей базы.

        :return: None
        """

        if self.is_manager:
            for asteroid in self.asteroids:
                asteroid.worker = None
            self.enemy_drones = [drone for drone in self.scene.drones if self.team != drone.team]
            self.enemy_bases = [m_ship for m_ship in self.scene.motherships if m_ship != self.my_mothership]

        self.task = states.LOAD_TASK

        if settings.DRONES_AMOUNT > 5:
            for _id in range(6, settings.DRONES_AMOUNT):
                if self.id % _id == 0:
                    self.states_handle_list = [states.MoveState(self), states.TransitionState(self)]
                    break
        else:
            self.states_handle_list = [states.CombatState(self), states.MoveState(self), states.TransitionState(self)]

        self.switch_state()

        self.turret_point = utils.get_turret_point(self)

    def on_stop_at_point(self, target: Point) -> None:
        """
        При остановке у точки пространства.

        Если текущее состояние - "сражение":
            устанавливает флаг "в боевом перемещении" в False.

        :param target: Point, точка, у которой остановился дрон
        :return: None
        """

        if isinstance(self.curr_state, states.CombatState):
            self.in_combat_move = False

    def on_stop_at_asteroid(self, asteroid: Asteroid) -> None:
        """
        При остановке у астероида.

        Если текущее состояние - "сражение":
            устанавливает флаг "в боевом перемещении" в False.
        Иначе:
            деактивирует текущее состояние;
            устанавливает флаг начала загрузки/выгрузки ресурса в значение True;
            начинает загрузку ресурса в трюм.

        :param asteroid: Asteroid object, объект астероида, у которого остановился дрон
        :return: None
        """

        if isinstance(self.curr_state, states.CombatState):
            self.in_combat_move = False
        else:
            self.switch_state()
            self.is_transition_started = True
            self.load_from(asteroid)

    def on_stop_at_mothership(self, mothership: MotherShip) -> None:
        """
        При остановке у базы.

        Если текущее состояние - "сражение":
            устанавливает флаг "в боевом перемещении" в False.
        Иначе:
            деактивирует текущее состояние;
            устанавливает флаг начала загрузки/выгрузки ресурса в значение True;

            если объект базы - союзный:
                начинает выгрузку ресурса на базу;
            иначе:
                начинает загрузку ресурса с базы.

        :param mothership: MotherShip object, объект базы
        :return: None
        """

        if isinstance(self.curr_state, states.CombatState):
            self.in_combat_move = False
        else:
            self.switch_state()
            self.is_transition_started = True
            if mothership == self.my_mothership:
                self.unload_to(mothership)
            else:
                self.load_from(mothership)

    def on_load_complete(self) -> None:
        """
        По завершении загрузки ресурса.

        Вызывает метод завершения "перекачки" ресурса.

        :return: None
        """

        self.on_transition_complete()

    def on_unload_complete(self) -> None:
        """
        По завершении выгрузки ресурса.

        Вызывает метод завершения "перекачки" ресурса.

        :return: None
        """

        self.on_transition_complete()

    def on_transition_complete(self) -> None:
        """
        По завершении "перекачки" ресурса.

        Сменяет текущее состояние.
        Устанавливает флаг начала загрузки/выгрузки ресурса в значение False.
        Устанавливает флаг завершения загрузки/выгрузки ресурса в значение True.

        :return: None
        """

        self.switch_state()
        self.is_transition_started = False
        self.is_transition_finished = True

    def switch_state(self) -> None:
        """
        Метод переключения состояния.

        Если текущее состояние не назначено (начало игры):
            переключает на состояние "сражение" и удаляет
                данное состояние из списка состояний.

        Иначе:
            если переключает текущее состояние на следующее:
                "перекачка ресурса" или "сражение" -> "перемещение";
                "перемещение" -> "перекачка ресурса".

        Активирует текущее состояние.

        :return: None
        """

        if self.curr_state is None:
            self.curr_state = self.states_handle_list[0]
            if isinstance(self.curr_state, states.CombatState):
                self.states_handle_list.pop(0)
        else:
            if isinstance(self.curr_state, states.CombatState) or isinstance(self.curr_state, states.TransitionState):
                self.curr_state = self.states_handle_list[0]
            else:
                self.curr_state = self.states_handle_list[1]
        self.curr_state.is_active = True
