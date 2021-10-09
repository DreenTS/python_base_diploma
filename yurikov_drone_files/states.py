from abc import ABC, abstractmethod


class DroneState(ABC):

    def __init__(self, drone):
        self.drone = drone
        self.next_state = None

    @abstractmethod
    def handle(self):
        pass

    def on_game_step(self):
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

    def handle(self):
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
        for astrd_with_rel in relations:
            asteroid, rel = astrd_with_rel
            if asteroid.start_worker is None:
                asteroid.start_worker = self.drone
                self.drone.curr_asteroid = asteroid
                return asteroid

    def on_game_step(self):
        super().on_game_step()
        if self.drone.task_for_move in [LOAD_TASK, UNLOAD_TASK]:
            self.drone.target = self.handle()
            self.drone.move_at(self.drone.target)


class LoadState(DroneState):

    def handle(self):
        self.drone.need_turn = False
        self.next_state = MOVE(self.drone)
        if not self.drone.is_full:
            self.drone.task_for_move = LOAD_TASK
        else:
            self.drone.task_for_move = UNLOAD_TASK


class UnloadState(DroneState):

    def handle(self):
        self.drone.need_turn = False
        self.next_state = MOVE(self.drone)
        self.drone.task_for_move = LOAD_TASK


MOVE = MoveState
LOAD_TASK = 'load_task'
UNLOAD_TASK = 'unload_task'

LOAD = LoadState
UNLOAD = UnloadState
