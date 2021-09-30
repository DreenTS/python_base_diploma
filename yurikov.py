from astrobox.core import Drone


class WrongDistanceOperandError(BaseException):

    def __init__(self, op):
        self.op = op

    def __str__(self):
        return f'Wrong value of "distance" argument: "{self.op}". Must be in ["far", "near"].'


class CollectorXXI(Drone):

    def __init__(self):
        # TODO - Неплохо бы проинспектировать используемый метод в супер-классе. там кварги в параметрах
        super().__init__()
        self.my_team = []

    def on_born(self):
        self.target = self._get_my_asteroid(distance='far')
        self.move_at(self.target)
        self.my_team.append(self)

    def _get_my_asteroid(self, distance):
        # TODO - Нейминг! distance - дистанция. Как другой прораммист должен догадаться,
        #  что этот параметр - строковые литералы принимает? Это скорее MODE какой-нибудь.
        #  А возможные варианты вынесите в константы.

        # TODO - Алгоритм получился запутанным.
        #  Сделайте две ветки алгоритма. Общую часть кода вынесите после обоих веток
        #  Код должен читаться как книга, а не как ребус
        if distance == 'far':
            target_asteroid = [0, self.my_mothership]
            operand = '>'
        elif distance == 'near':
            operand = '<'
            target_asteroid = [10000, self.my_mothership]
        else:
            raise WrongDistanceOperandError(op=distance)
        for asteroid in self.asteroids:
            if not asteroid.is_empty:
                # TODO - Старайтесь не использовать eval
                if eval(f'self.distance_to(asteroid) {operand} target_asteroid[0]'):
                    target_asteroid = [self.distance_to(asteroid), asteroid]
        return target_asteroid[1]

    def on_stop_at_asteroid(self, asteroid):
        self.load_from(asteroid)

    def on_load_complete(self):
        if not self.is_full:
            self.target = self._get_my_asteroid(distance='near')
            self.move_at(self.target)
        else:
            self.move_at(self.my_mothership)

    def on_stop_at_mothership(self, mothership):
        self.unload_to(mothership)

    def on_unload_complete(self):
        if self.target.is_empty:
            self.target = self._get_my_asteroid(distance='far')
        self.move_at(self.target)
