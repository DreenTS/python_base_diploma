from astrobox.core import Drone
from robogame_engine.geometry import Point

import yurikov_team.states as states
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
        first_team, second_team = self.data['teams'].items()
        res += f'{first_team[0]}: {first_team[1]}\n{second_team[0]}: {second_team[1]}\n'
        if first_team[1] > second_team[1]:
            res += f'\nWINNER: {first_team[0]}\n\n'
        else:
            res += f'\nWINNER: {second_team[0]}\n\n'
        for k, v in self.data.items():
            if k != 'teams':
                res += f'{k} = {v}\n'
        self.logger.info(res)
        print('\nLOGGING COMPLETED SUCCESSFULLY!\n')


class YurikovDrone(Drone):
    """
    Класс дрона.
    Собирает ресурс с астероидов и выгружает его на базе.

    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.states_handle_list = None
        self.curr_state = None
        self.task = None
        self.is_transition_started = False
        self.is_transition_finished = False
        self.target_to_turn = None
        self.is_first_step = True
        self.enemy_base = None
        self.prev_point = None
        self.manager = self
        self.is_manager = True
        self.need_log = True
        self.stats = None
        temp_managers_list = [mate for mate in self.teammates if mate.is_manager]
        if temp_managers_list:
            self.manager = temp_managers_list[0]
            self.is_manager = False
            self.need_log = False

    def on_heartbeat(self):
        """
        Выполняется при каждом шаге игры.

        Проверяет, закончилась ли "миссия" дронов (можно ли логгировать).
        Обновляет значение признаков оптимальности перемещения дрона.

        Вызывает метод состояния дрона on_heartbeat()
        (подробнее см. docstrings методов состояний в states.py).

        :return: None
        """

        if self.check_for_end():
            if self.manager.need_log:
                self.manager.log_stats()

        self.update_stats(point=self.prev_point)

        self.prev_point = Point(self.coord.x, self.coord.y)

        self.curr_state.on_heartbeat()

    def on_born(self):
        """
        Вызывается единожды при "рождении" дрона.

        Если дрон является "менеджером",
        то добавляет всем астероидам на сцене атрибут worker.
        В ходе игры распределение следующее: на 1 астероиде может работать 1 дрон.

        Устанавливает задачу для перемещения - "на загрузку".
        Добавляет в список состояний два объекта классов состояний - "перемещение" и "перекачка ресурса".
        Вызывает метод переключения состояния switch_state()
        (подробнее см. docstrings метода).

        Получает цель для перемещения из обработки внутри состояния и движется к ней.

        :return: None
        """

        self.prev_point = Point(self.coord.x, self.coord.y)

        if self.is_manager:
            for asteroid in self.asteroids:
                asteroid.worker = None
        if len(self.scene.motherships) > 1:
            self.enemy_base = [m_ship for m_ship in self.scene.motherships if m_ship != self.my_mothership][0]
        self.states_handle_list = [states.MoveState(self), states.TransitionState(self)]
        self.stats = {
            'empty_range': 0.0,
            'fully_range': 0.0,
            'not_fully_range': 0.0,
        }
        self.task = states.LOAD_TASK
        self.switch_state()
        non_empty_asteroids = [astrd for astrd in self.asteroids if not astrd.is_empty]
        self.target = self.curr_state.handle_action(asteroids_list=non_empty_asteroids, drone_free_space=self.free_space)
        self.move_at(self.target)

    def on_stop_at_asteroid(self, asteroid):
        """
        При остановке у астероида.

        Переключает состояние.
        Устанавливает флаг начала загрузки/выгрузки ресурса в значение True.
        Начинает загрузку ресурса в трюм.

        :param asteroid: Asteroid object, объект астероида, у которого остановился дрон
        :return: None
        """

        self.switch_state()
        self.is_transition_started = True
        self.load_from(asteroid)

    def on_stop_at_mothership(self, mothership):
        """
        При остановке у базы.

        Переключает состояние.
        Устанавливает флаг начала загрузки/выгрузки ресурса в значение True.
        Начинает выгрузку ресурса на базу.

        :param mothership: MotherShip object, объект базы
        :return: None
        """

        self.switch_state()
        self.is_transition_started = True
        self.unload_to(mothership)

    def on_load_complete(self):
        """
        По завершении загрузки ресурса.

        Переключает состояние.
        Устанавливает флаг начала загрузки/выгрузки ресурса в значение False.
        Устанавливает флаг окончания загрузки/выгрузки ресурса в значение True.


        :return: None
        """

        self.switch_state()
        self.is_transition_started = False
        self.is_transition_finished = True

    def on_unload_complete(self):
        """
        По завершении выгрузки ресурса.

        Переключает состояние.
        Устанавливает флаг начала загрузки/выгрузки ресурса в значение False.
        Устанавливает флаг окончания загрузки/выгрузки ресурса в значение True.


        :return: None
        """

        self.switch_state()
        self.is_transition_started = False
        self.is_transition_finished = True

    def switch_state(self):
        """
        Метод переключения состояния.

        Если текущее состояние не назначено (начало игры):
            ! переключает на состояние "перемещение".

        Иначе:
            ! диактивирует текущее состояние;
            ! если переключает текущее состояние на следующее
                ("перемещение" -> "перекачка ресурса" и наоборот).

        Активирует текущее состояние.

        :return: None
        """

        if self.curr_state is None:
            self.curr_state = self.states_handle_list[0]
        else:
            self.curr_state.is_active = False
            if isinstance(self.curr_state, states.TransitionState):
                self.curr_state = self.states_handle_list[0]
            else:
                self.curr_state = self.states_handle_list[1]
        self.curr_state.is_active = True

    def update_stats(self, point):
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

    def check_for_end(self):
        """
        Проверяет, закончилась ли "миссия" дронов (можно ли логгировать).
        Формирует список всех дронов и астероидов.
        Проверяет, являются ли все объекты списка пустыми
        (отсутствует ли ресурс в трюмах дронов и недрах астероидов).

        :return: bool, пустые ли все астероиды и все дроны
        """

        check_list = self.teammates + self.asteroids
        is_empty_for_end = [obj.is_empty for obj in check_list]
        is_empty_for_end.append(self.is_empty)
        return all(is_empty_for_end)

    def log_stats(self):
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
        logger = SpaceLogger(data=game_result)
        logger.log()