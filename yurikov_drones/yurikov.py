from astrobox.core import Drone
from robogame_engine.geometry import Point

import states
from log_config import configure_logger


class SpaceLogger:
    """
    Класс для логгера статистики.

    """

    def __init__(self, data):
        self.logger = configure_logger()
        self.data = data

    def log(self):
        res = 'Run stats:\n'
        for k, v in self.data.items():
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
        self.state_handle = None
        self.task_for_move = None
        self.curr_asteroid = None
        self.need_turn = True
        self.prev_point = None
        self.manager = self
        self.is_manager = True
        self.need_log = True
        self.stats = {
            'empty_range': 0.0,
            'fully_range': 0.0,
            'not_fully_range': 0.0,
        }
        temp_managers_list = [mate for mate in self.teammates if mate.is_manager]
        if temp_managers_list:
            self.manager = temp_managers_list[0]
            self.is_manager = False
            self.need_log = False

    def on_born(self):
        """
        Вызывается при "рождении" дрона.
        Формирует список кортежей (<объект_астероида>, <расстояние_до_астероида>)
        и сортирует его по убыванию.
        Получение астероида в качестве цели для загрузки-выгрузки
        будет происходить через обращение к данному списку.

        :return: None
        """

        self.prev_point = Point(self.coord.x, self.coord.y)

        if self.is_manager:
            for asteroid in self.asteroids:
                asteroid.start_worker = None
        self.task_for_move = states.LOAD_TASK
        self.state_handle = states.MOVE(self)
        self.target = self.state_handle.handle()
        self.move_at(self.target)

    def game_step(self):
        if self._check_for_end():
            if self.manager.need_log:
                self.manager.log_stats()

        self._update_stats(point=self.prev_point)

        self.prev_point = Point(self.coord.x, self.coord.y)

        self.state_handle.on_game_step()

        super().game_step()

    def on_stop_at_asteroid(self, asteroid):
        self.state_handle = self.state_handle.next_state
        self.need_turn = True
        self.load_from(asteroid)

    def on_stop_at_mothership(self, mothership):
        self.state_handle = self.state_handle.next_state
        self.need_turn = True
        self.unload_to(mothership)

    def _update_stats(self, point):
        """
        Вспомогательный метод. Вызывается перед каждом перемещении к цели (метод move_to()).
        Дополняет словарь менеджера по ключам, в зависимости от заполненности трюма.

        :param target: MotherShip or Asteroid object, объект, до которого полетит дрон
        :return: None
        """

        if self.is_empty:
            self.manager.stats['empty_range'] += self.distance_to(point)
        elif self.is_full:
            self.manager.stats['fully_range'] += self.distance_to(point)
        else:
            self.manager.stats['not_fully_range'] += self.distance_to(point)

    def _check_for_end(self):
        """
        Проверяет, закончилась ли "миссия" дронов (можно ли логгировать).
        Формирует список всех дронов и астероидов.
        Проверяет, являются ли все объекты списка пустыми
        (отсутствует ли ресурс в трюмах дронов и недрах астероидов).

        :return: bool, пустые ли все астероиды и все дроны?
        """

        check_list = self.teammates + self.asteroids
        is_empty_for_end = [obj.is_empty for obj in check_list]
        is_empty_for_end.append(self.is_empty)
        return all(is_empty_for_end)

    def log_stats(self):
        """
        Инициализация логгера.
        Метод вызывается лишь раз в конце "миссии" дронов.

        :return: None
        """

        self.need_log = False
        logger = SpaceLogger(data=self.stats)
        logger.log()

