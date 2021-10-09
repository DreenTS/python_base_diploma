from abc import ABC, abstractmethod


class DroneState(ABC):
    """
    Базовый класс состояния дрона.

    """

    def __init__(self, drone):
        self.drone = drone
        self.next_state = None

    @abstractmethod
    def handle(self):
        pass

    def on_game_step(self):
        """
        Выполняется при каждом шаге игры.

        Если дрон находится в процессе загрузки/выгрузки ресурса:
            ! получает следующую предполагаемую цель для перемещения
                и поворачивается в её сторону.

        По окончании процесса загрузки/выгрузки ресурса:
            ! вызывает метод обработки текущего состояния (загрузки или выгрузки);
            ! присваивает следующее состояние - из атрибута next_state текущего состояния;
            ! получает цель для перемещения из обработки внутри состояния и движется к цели.

        :return: None
        """

        # TODO - Префикс "_" в имени поля внешнего класса говорит о том, что не нужно его юзать в своих целях
        if self.drone._transition is None:
            if self.drone.state_handle.__class__ in [LOAD, UNLOAD]:
                self.drone.state_handle.handle()
                self.drone.state_handle = self.drone.state_handle.next_state
                self.drone.target = self.drone.state_handle.handle()
                self.drone.move_at(self.drone.target)
        else:
            if self.drone.need_turn:
                if self.drone.free_space > self.drone.target.payload:
                    self.drone.task_for_move = LOAD_TASK
                else:
                    self.drone.task_for_move = UNLOAD_TASK
                loc_state = MOVE(self.drone)
                turn_target = loc_state.handle()
                self.drone.turn_to(turn_target)


class MoveState(DroneState):
    """
    Класс состояния "перемещения".

    """

    def handle(self):
        # TODO - Нейминг! М.б. как обозначить действие в имени? Например, action?
        """
        Метод обработки внутри состояния.

        Ищет и возвращает цель для перемещения.

        Если задача для перемещения "на выгрузку":
            ! присваивает атрибуту  next_state следующее состояние - "выгрузка";
            ! возвращает объект базы.

        Если задача для перемещения "на загрузку":
            ! присваивает атрибуту  next_state следующее состояние - "загрузка";
            ! формирует локальный список с непустыми астероидами;

            ! если текущее состояние == "перемещение", а текущий астероид дрона до сих пор не пустой:
                возвращает текущий астероид из атрибута curr_asteroid;

            ! иначе:
                формирует список кортежей (asteroid, rel),

                где asteroid - Asteroid object,
                    rel - отношение = ВОЗМОЖНОЕ_КОЛВО_РЕСУРСА / (1 + РАССТОЯНИЕ_ДО_АСТЕРОИДА);

                сортирует список кортежей по значению отношения;
                если обработка происходит в самом начале игры (curr_state is None),
                    вызывается метод _get_start_asteroid() (подробнее см. docstrings метода);

                иначе возвращается самый выгодный для загрузки ресурса астероид
                    (чем больше на астероиде ресурса и меньше расстояние до него - тем лучше).

            ! если же все астероиды пустые (локальный список непустых астероидов пуст),
                устанавливает задачу для перемещения - "на выгрузку";
                присваивает атрибуту  next_state следующее состояние - "выгрузка";
                возвращает объект базы.

        :return: Asteroid or MotherShip object, цель для перемещения - астероид или база
        """

        if self.drone.task_for_move == UNLOAD_TASK:
            self.next_state = UNLOAD(self.drone)
            return self.drone.my_mothership

        elif self.drone.task_for_move == LOAD_TASK:
            self.next_state = LOAD(self.drone)

            asteroids = [astrd for astrd in self.drone.asteroids if not astrd.is_empty]
            if self.drone.state_handle.__class__ == MOVE:
                if self.drone.curr_asteroid in asteroids:
                    return self.drone.curr_asteroid

            relations = []
            for asteroid in asteroids:
                if self.drone.free_space >= asteroid.payload:
                    payload_to_load = asteroid.payload
                else:
                    payload_to_load = self.drone.free_space
                rel = payload_to_load / (1.0 + self.drone.distance_to(asteroid))
                relations.append((asteroid, rel))
            relations.sort(key=lambda k: k[1], reverse=True)

            if self.drone.curr_asteroid is None:
                return self._get_start_asteroid(relations=relations)

            for astrd_with_rel in relations:
                asteroid, rel = astrd_with_rel
                if self.drone.state_handle.__class__ == MOVE:
                    self.drone.curr_asteroid = asteroid
                return asteroid
            else:
                self.drone.task_for_move = UNLOAD_TASK
                self.next_state = UNLOAD(self.drone)
                return self.drone.my_mothership

    def _get_start_asteroid(self, relations):
        """
        Получить начальный астероид.
        В начале игры распределение следующее: на 1 дрона - 1 астероид.

        :param relations: list, список отношений
        :return: Asteroid object, выбранный астероид
        """

        for astrd_with_rel in relations:
            asteroid, rel = astrd_with_rel
            if asteroid.start_worker is None:
                asteroid.start_worker = self.drone
                self.drone.curr_asteroid = asteroid
                return asteroid

    def on_game_step(self):
        """
        Выполняется при каждом шаге игры.

        Получает цель для перемещения из обработки внутри состояния и движется к цели
        (на случай, если цель во время перемещения к ней осталась без ресурса
        или если все астероиды пустые).

        :return: None
        """

        super().on_game_step()
        self.drone.target = self.handle()
        self.drone.move_at(self.drone.target)


class LoadState(DroneState):
    """
    Класс состояния "загрузки".

    """

    def handle(self):
        """
        Метод обработки внутри состояния.
        Выполняется по окончании загрузки ресурса с астероида в трюм.


        Запрещает поворот к следующей цели во время загрузки ресурса
        Присваивает атрибуту  next_state следующее состояние - "перемещение".

        Если трюм дрона заполнен не до предела, устанавливает задачу
        для перемещения - "на загрузку", иначе - "на выгрузку".

        :return: None
        """

        self.drone.need_turn = False
        self.next_state = MOVE(self.drone)
        if not self.drone.is_full:
            self.drone.task_for_move = LOAD_TASK
        else:
            self.drone.task_for_move = UNLOAD_TASK


class UnloadState(DroneState):
    """
    Класс состояния "выгрузки".

    """

    def handle(self):
        """
        Метод обработки внутри состояния.
        Выполняется по окончании выгрузки ресурса на базу.

        Запрещает поворот к следующей цели во время загрузки ресурса
        Присваивает атрибуту  next_state следующее состояние - "перемещение".

        Устанавливает задачу для перемещения - "на загрузку".

        :return: None
        """

        self.drone.need_turn = False
        self.next_state = MOVE(self.drone)
        self.drone.task_for_move = LOAD_TASK


# TODO - Константы принято размещать сразу после импортов
MOVE = MoveState
LOAD_TASK = 'load_task'
UNLOAD_TASK = 'unload_task'

LOAD = LoadState
UNLOAD = UnloadState

# TODO - Ни разу не сталкиался с тем, чтобы константой указывать на класс. Это запутывает код, т.е. программисту
#  требуется остледить все эти указатели и держать в голове настоящее название класса.
#  Не думаю, что это хорошая практика. Классами надо пользоваться как классами, это логично. Не логично иное.
