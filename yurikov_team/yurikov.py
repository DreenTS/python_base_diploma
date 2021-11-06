from astrobox.core import Drone, Asteroid, MotherShip
from robogame_engine.geometry import Point

import yurikov_team.states as states
from yurikov_team import utils
from yurikov_team.log_config import configure_logger


class SpaceLogger:
    """
    Класс для логгера статистики.

    """

    def __init__(self, data):
        self.logger = configure_logger()
        self.data = data

    def log(self):
        res = 'Run stats:\n'
        winner = list(self.data['teams'].keys())[0]
        for name, score in self.data['teams'].items():
            res += f'{name}: {score}\n'
            if score > self.data['teams'][winner]:
                winner = name

        res += f'\nWINNER: {winner}\n\n'

        for k, v in self.data.items():
            if k != 'teams':
                res += f'{k} = {v}\n'

        self.logger.info(res)
        print('\nLOGGING COMPLETED SUCCESSFULLY!\n')


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
        self.prev_point = None
        self.turret_point = None
        self.in_regroup_move = True
        self.enemy_drones = None
        self.enemy_bases = None
        self.task = None
        self.is_transition_started = False
        self.is_transition_finished = True
        self.target_to_turn = None
        self.stats = None

        _temp_managers_list = [mate for mate in self.teammates if mate.is_manager]
        if _temp_managers_list:
            self.manager = _temp_managers_list[0]
            self.is_manager = False
            self.need_log = False
        else:
            self.manager = self
            self.is_manager = True
            self.need_log = True

    def on_heartbeat(self) -> None:
        """
        Выполняется при каждом шаге игры.

        #TODO Проверяет, закончилась ли "миссия" дронов (можно ли логгировать).

        Есл текущее состояние дрона деактивировано:
            ! меняет сстояние.

        Обновляет значение признаков оптимальности перемещения дрона.

        Вызывает метод состояния дрона on_heartbeat()
        (подробнее см. docstrings методов состояний в states.py).

        :return: None
        """

        # if self.scene.get_game_result()[0]:
        #     if self.manager.need_log:
        #         self.manager.log_stats()

        if not self.curr_state.is_active:
            self.switch_state()

        if self.target is None:
            self.target = self.curr_state.handle_action()

        self.update_stats(point=self.prev_point)

        self.prev_point = Point(self.coord.x, self.coord.y)

        self.curr_state.on_heartbeat()

    def on_born(self) -> None:
        """
        Вызывается единожды при "рождении" дрона.

        Если дрон является "менеджером",
        то добавляет всем астероидам на сцене атрибут worker.
        В ходе игры распределение следующее: на 1 астероиде может работать 1 дрон.

        Формирует два списка: с объектами вражеских дронов и вражеских баз.

        Устанавливает задачу для перемещения - "на загрузку".
        Добавляет в список состояний объекты классов состояний (подробнее о классах см. docstrings классов).
        Вызывает метод переключения состояния switch_state()
        (подробнее см. docstrings метода).

        Получает точку "турели" около своей базы и движется к ней.

        :return: None
        """

        self.prev_point = Point(self.coord.x, self.coord.y)

        if self.is_manager:
            for asteroid in self.asteroids:
                asteroid.worker = None

        self.stats = {
            'empty_range': 0.0,
            'fully_range': 0.0,
            'not_fully_range': 0.0,
        }

        self.enemy_drones = [drone for drone in self.scene.drones if self.team != drone.team]
        self.enemy_bases = [m_ship for m_ship in self.scene.motherships if m_ship != self.my_mothership]
        self.task = states.LOAD_TASK
        if len(self.scene.teams) <= 2 and self.is_manager:
            self.states_handle_list = [states.MoveState(self), states.TransitionState(self)]
        else:
            self.states_handle_list = [states.TurretState(self), states.MoveState(self), states.TransitionState(self)]
        self.switch_state()
        self.turret_point = utils.get_turret_point(self, self.id)
        self.move_at(self.turret_point)

    def on_stop_at_point(self, target: Point) -> None:
        """
        При остановке у точки пространства.

        Если текущее состояние - "турель":
            ! устанавливает флаг "в процессе перегруппировки" в False.

        :param target: Point, точка, у которой остановился дрон
        :return: None
        """

        if isinstance(self.curr_state, states.TurretState):
            self.in_regroup_move = False

    def on_stop_at_asteroid(self, asteroid: Asteroid) -> None:
        """
        При остановке у астероида.

        Если текущее состояние - "турель":
            ! устанавливает флаг "в процессе перегруппировки" в False.
        Иначе:
            ! деактивирует текущее состояние;
            ! устанавливает флаг начала загрузки/выгрузки ресурса в значение True;
            ! начинает загрузку ресурса в трюм.

        :param asteroid: Asteroid object, объект астероида, у которого остановился дрон
        :return: None
        """

        if isinstance(self.curr_state, states.TurretState):
            self.in_regroup_move = False
        else:
            self.switch_state()
            self.is_transition_started = True
            self.load_from(asteroid)

    def on_stop_at_mothership(self, mothership: MotherShip) -> None:
        """
        При остановке у базы.

        Если текущее состояние - "турель":
            ! движется к точки "турели".
        Иначе:
            ! деактивирует текущее состояние;
            ! устанавливает флаг начала загрузки/выгрузки ресурса в значение True;

            ! если объект базы - союзный:
                начинает выгрузку ресурса на базу;
            ! иначе:
                начинает загрузку ресурса с базы.

        :param mothership: MotherShip object, объект базы
        :return: None
        """

        if isinstance(self.curr_state, states.TurretState):
            self.move_at(self.turret_point)
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
            ! переключает на состояние "турель" и удаляет
                данное состояние из списка состояний.

        Иначе:
            ! если переключает текущее состояние на следующее:
                "перекачка ресурса" или "турель" -> "перемещение";
                "перемещение" -> "перекачка ресурса".

        Активирует текущее состояние.

        :return: None
        """

        if self.curr_state is None:
            self.curr_state = self.states_handle_list[0]
            if isinstance(self.curr_state, states.TurretState):
                self.states_handle_list.pop(0)
        else:
            self.curr_state.is_active = False
            if isinstance(self.curr_state, states.TurretState) or isinstance(self.curr_state, states.TransitionState):
                self.curr_state = self.states_handle_list[0]
            else:
                self.curr_state = self.states_handle_list[1]
        self.curr_state.is_active = True

    def update_stats(self, point: Point) -> None:
        """
        Вспомогательный метод. Вызывается при каждом шаге игры.
        Дополняет словарь менеджера по ключам, в зависимости от заполненности трюма,
        если дрон перемещался по сцене.

        :param point: Point object, предыдущая точка на сцене, где находился дрон
        :return: None
        """

        if self.is_empty:
            self.manager.stats['empty_range'] += self.distance_to(point)
        elif self.is_full:
            self.manager.stats['fully_range'] += self.distance_to(point)
        else:
            self.manager.stats['not_fully_range'] += self.distance_to(point)

    def log_stats(self) -> None:
        """
        Инициализация логгера.

        Метод вызывается лишь раз в конце "миссии" дронов.
        Формирует словарь с результатами команд и передаёт данные логгеру.

        :return: None
        """

        game_result = {'teams': {}}
        for team_name, mates in self.scene.teams.items():
            team_resources = mates[0].my_mothership.payload
            for drone in mates:
                team_resources += drone.payload
            game_result['teams'][team_name] = team_resources
        game_result.update(self.stats)
        self.need_log = False
        logger = SpaceLogger(game_result)
        logger.log()
