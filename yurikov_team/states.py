from abc import ABC, abstractmethod

from astrobox.core import Asteroid
from robogame_engine.theme import theme

LOAD_TASK = 'load_task'
UNLOAD_TASK = 'unload_task'


class DroneState(ABC):
    """
    Базовый класс состояния дрона.

    """

    def __init__(self, drone):
        self.drone = drone
        self.is_active = False

    def _get_rel_list(self, asteroids_list, drone_free_space):
        """
        Получить список отношений.
        
        Проходится по списку астероидов.
        Высчитывает процентное соотношение координаты x астероида к длине игровой сцены.
        Если астероид находится во второй трети сцены:
            ! астероид добавляется в список координат валидного диапазона;
        Иначе если астероид находится в первой трети сцены:
            ! астероид добавляется в список координат диапазона ниже валидного;
        Иначе:
            ! астероид добавляется в список координат диапазона выше валидного.

        Добавляет в выбранный список кортеж (asteroid, rel),
            где asteroid - Asteroid object,

                                        ВОЗМОЖНОЕ_КОЛВО_РЕСУРСА * РАССТОЯНИЕ_ДО_ВРАЖЕСКОЙ_БАЗЫ
                rel - отношение =           ------------------------------------------
                                    РАССТОЯНИЕ_ДО_АСТЕРОИДА + РАССТОЯНИЕ_ОТ_АСТЕРОИДА_ДО_СВОЕЙ_БАЗЫ

        Если дрон в процессе загрузки ресурса с астероида, возможное кол-во ресурса рассчитывается
            исходя из того, насколько трюм дрона будет загружен по завершении загрузки.

        Если обработка происходит в самом начале игры (is_first_step == True):
            ! приоритет отдаётся астероидам из 2 трети сцены;
        Иначе:
            ! приоритет отдаётся астероидам из 1 и 2 третей сцены.

        Возвращает результирующий список отношений.
        
        :param asteroids_list: список астероидов
        :param drone_free_space: свободное место в трюме астероида
        :return: list, список отношений
        """
        
        in_valid_range = []
        in_under_range = []
        in_over_range = []

        for asteroid in asteroids_list:
            percentage_x = asteroid.coord.x / theme.FIELD_WIDTH
            if .35 <= percentage_x <= .65:
                list_append = in_valid_range.append
            elif percentage_x < .35:
                list_append = in_under_range.append
            else:
                list_append = in_over_range.append

            dist = self.drone.distance_to(asteroid) + self.drone.my_mothership.distance_to(asteroid)

            if asteroid.payload >= drone_free_space:
                payload = drone_free_space
            else:
                payload = asteroid.payload
            if self.drone.enemy_base is not None:
                payload *= asteroid.distance_to(self.drone.enemy_base)
            rel = payload / dist
            list_append((asteroid, rel))

        if self.drone.is_first_step:
            self.drone.is_first_step = False
            in_valid_range.sort(key=lambda k: k[1], reverse=True)
            in_under_range.sort(key=lambda k: k[1], reverse=True)
        else:
            in_valid_range += in_under_range
            in_valid_range.sort(key=lambda k: k[1], reverse=True)
            in_under_range.clear()

        in_over_range.sort(key=lambda k: k[1], reverse=True)
        res_list = in_valid_range + in_under_range + in_over_range

        return res_list

    def handle_action(self, asteroids_list, drone_free_space):
        """
        Метод обработки действия внутри состояния.

        Ищет и возвращает цель для перемещения или поворота.

        Если задача для перемещения "на выгрузку":
            ! возвращает объект базы.

        Если задача для перемещения "на загрузку":
            ! если класс состояния - "перемещение":
                формирует список непустых астероидов;
            ! иначе:
                формирует список непустых астероидов, исключая текущую цель дрона.

            ! получает список отношений, вызывая метод _get_rel_list()
                (подробнее см. docstrings метода);

            ! возвращает самый выгодный для загрузки ресурса астероид:
                чем (больше на астероиде ресурса и больше расстояние от астероида до вражеской базы)
                    и
                    (меньше расстояние от дрона до астероида, а от него до базы),

                тем лучше :)
            ! если дрон не находится в процессе загрузки/выгрузки ресурса:
                присваивает астероиду "рабочего" в лице самого дрона
                    (в процессе загрузки/выгрузки дрон только поворачивается в сторону
                        предполагаемой следующей цели по завершении загрузки/выгрузки
                        цель может поменяться, поэтому "рабочий" не присваивается при
                        выборе цели для поворота);

            ! если же все астероиды пустые (локальный список непустых астероидов пуст),
                устанавливает задачу для перемещения - "на выгрузку";
                возвращает объект базы.

        :param asteroids_list: список астероидов
        :param drone_free_space: свободное место в трюме астероида
        :return: Asteroid or MotherShip object, цель для перемещения или поворота - астероид или база
        """

        if self.drone.task == UNLOAD_TASK:
            return self.drone.my_mothership
        elif self.drone.task == LOAD_TASK:
            relations = self._get_rel_list(asteroids_list=asteroids_list, drone_free_space=drone_free_space)

            for astrd_with_rel in relations:
                asteroid, rel = astrd_with_rel
                if asteroid.worker is None:
                    if not self.drone.is_transition_started:
                        asteroid.worker = self.drone
                    return asteroid
            else:
                self.drone.task = UNLOAD_TASK
                return self.drone.my_mothership

    @abstractmethod
    def on_heartbeat(self):
        """
        Выполняется при каждом шаге игры.

        Реализуется в потомках класса.
        """

        pass


class MoveState(DroneState):
    """
    Класс состояния "перемещения".

    """

    def on_heartbeat(self):
        """
        Выполняется при каждом шаге игры.

        Если состояние активировано (является текущим состоянием дрона):
            ! если завершился процесс загрузки/выгрузки ресурса (is_transition_finished == True):
                удаляет "рабочего" с текущей цели дрона (если цель - астероид);

                если трюм дрона не заполнен:
                    следующая задача - "на загрузку";
                иначе:
                    следующая задача - "на выгрузку".

                получает цель для перемещения из обработки внутри состояния и движется к ней.

            ! если цель во время перемещения к ней осталась без ресурса:
                получает цель для перемещения из обработки внутри состояния и движется к ней.

        :return: None
        """

        if self.is_active:
            if self.drone.is_transition_finished:
                self.drone.is_transition_finished = False
                if self.drone.target != self.drone.my_mothership:
                    self.drone.target.worker = None
                if not self.drone.is_full:
                    self.drone.task = LOAD_TASK
                else:
                    self.drone.task = UNLOAD_TASK
                non_empty_asteroids = [astrd for astrd in self.drone.asteroids if not astrd.is_empty]
                self.drone.target = self.handle_action(asteroids_list=non_empty_asteroids,
                                                       drone_free_space=self.drone.free_space)
                self.drone.move_at(self.drone.target)

            if self.drone.target and self.drone.target.is_empty:
                non_empty_asteroids = [astrd for astrd in self.drone.asteroids if not astrd.is_empty]
                self.drone.target = self.handle_action(asteroids_list=non_empty_asteroids,
                                                       drone_free_space=self.drone.free_space)
                self.drone.move_at(self.drone.target)


class TransitionState(DroneState):
    """
    Класс состояния "загрузки".

    """

    def on_heartbeat(self):
        """
        Выполняется при каждом шаге игры.

        Если состояние активировано (является текущим состоянием дрона):
            ! если начался процесс загрузки/выгрузки ресурса (is_transition_started == True):

                если текущая цель дрона - астероид, а загруженность дрона + кол-во ресурса на астероиде >= 100:
                    следующая задача - "на выгрузку";
                иначе:
                    следующая задача - "на загрузку";

            ! получает следующую предполагаемую цель дрона из обработки внутри состояния и поворачивается к ней.

        :return: None
        """

        if self.is_active:
            if self.drone.is_transition_started:
                if isinstance(self.drone.target, Asteroid) and self.drone.payload + self.drone.target.payload >= 100:
                    self.drone.task = UNLOAD_TASK
                else:
                    self.drone.task = LOAD_TASK
                drone_free_space = self.drone.free_space
                if isinstance(self.drone.target, Asteroid):
                    drone_free_space -= self.drone.target.payload
                non_empty_asteroids = [astrd for astrd in self.drone.asteroids
                                       if not astrd.is_empty and astrd != self.drone.target]

                self.drone.target_to_turn = self.handle_action(asteroids_list=non_empty_asteroids,
                                                               drone_free_space=drone_free_space)
                self.drone.turn_to(self.drone.target_to_turn)
