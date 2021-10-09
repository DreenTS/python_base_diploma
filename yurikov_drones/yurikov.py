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

    def _get_target_to_act(self, action):
        """
        Получить цель для загрузки-выгрузки ресурса.
        Проходится по срезу списка asteroids_with_distance с индекса.

        При действии загрузки (action == LOAD), индекс = 0:
        дрон ищет любой непустой астероид, начиная с самого дальнего от базы.

        При действии выгрузки (action == UNLOAD), индекс = object_index - 1
        (object_index - индекс объекта, у которого сейчас находится дрон):
        дрон ищет любой неполный астероид, находящийся ближе к базе (чем текущий объект)
        по списку asteroids_with_distance.

        Если подходящего астероида для загрузки-выгрузки не нашлось, возвращает объект базы.

        :param action: str, действие, загрузить ресурс с астероида или выгрузить на астероид/базу
        :return: MotherShip or Asteroid object, объект, до которого полетит дрон
        """

        res_target = self.my_mothership

        if action == UNLOAD:
            loc_distance = self.my_mothership.distance_to(self.target)
            index = self.asteroids_with_distance.index((self.target, loc_distance)) + 1
        else:
            index = 0

        for astrd_with_dist in self.asteroids_with_distance[index:]:
            astrd = astrd_with_dist[0]
            if action == LOAD:
                if not astrd.is_empty:
                    res_target = astrd
                    break
            if action == UNLOAD:
                if not astrd.is_full:
                    res_target = astrd
                    break

        return res_target

    def on_stop_at_asteroid(self, asteroid):
        """
        В зависимости от аргумента дрона action, выполняет загрузку или выгрузку ресурса.

        :param asteroid: Asteroid object, объект астероида, у которого остановился дрон
        :return: None
        """

        if self.action == LOAD:
            self.load_from(asteroid)
        else:
            self.unload_to(asteroid)

    def on_load_complete(self):
        """
        Вызывается по окончанию загрузки.
        Если трюм дрона заполнен, меняет action на выгрузку, ищет цель для выгрузки, летит к ней.
        Иначе, меняет action на загрузку, ищет цель для загрузку, летит к ней.

        :return: None
        """

        if self.is_full:
            self.action = UNLOAD
            self.target = self._get_target_to_act(action=self.action)
            self.move_at(self.target)
        else:
            self.action = LOAD
            self.target = self._get_target_to_act(action=self.action)
            self.move_at(self.target)

    def on_stop_at_mothership(self, mothership):
        self.unload_to(mothership)

    def on_unload_complete(self):
        """
        Вызывается по окончанию выгрузки.
        Вызывает метод, проверяющий, закончилась ли "миссия" дронов (можно ли логгировать).
        Если вернулось True:
            вызывает метод логгирования у менеджера команды (чтобы было единственное логгирование).
        Если вернулось False:
            при пустом трюме дрона ищет астероид для загрузки;
            иначе ищет астероид для выгрузки.
        Отправляется к цели для загрузки-выгрузки.

        :return: None
        """

        if self._check_for_end():
            if self.manager.need_log:
                self.manager.log_stats()
        else:
            if self.is_empty:
                self.action = LOAD
                self.target = self._get_target_to_act(action=self.action)
            else:
                self.action = UNLOAD
                self.target = self._get_target_to_act(action=self.action)
            self.move_at(self.target)

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

