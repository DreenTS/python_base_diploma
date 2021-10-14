LOG_FILENAME = 'game_with_20.log'  # 'game_with_10.log'
PLAYER_WINNER_PATTERN = 'WINNER: YurikovDrone'
ENEMY_WINNER_PATTERN = 'WINNER: DrillerDrone'
PLAYER_RESOURCE_AMOUNT = 'YurikovDrone: '
ENEMY_RESOURCE_AMOUNT = 'DrillerDrone: '

if __name__ == '__main__':
    with open(LOG_FILENAME, 'r', encoding='utf-8') as file:
        game = file.readlines()
    player_win = 0
    player_total_resources = 0
    enemy_win = 0
    enemy_total_resources = 0

    for line in game:
        if PLAYER_WINNER_PATTERN in line:
            player_win += 1
        elif ENEMY_WINNER_PATTERN in line:
            enemy_win += 1
        elif PLAYER_RESOURCE_AMOUNT in line:
            player_total_resources += int(line[len(PLAYER_RESOURCE_AMOUNT):])
        elif ENEMY_RESOURCE_AMOUNT in line:
            enemy_total_resources += int(line[len(ENEMY_RESOURCE_AMOUNT):])

    runs_total = enemy_win + player_win
    player_winrate = player_win / runs_total * 100
    player_avg_resource_amount = player_total_resources / runs_total
    enemy_avg_resource_amount = enemy_total_resources / runs_total

    print(f'RUNS TOTAL: {runs_total}\n')
    print(f'PLAYER WIN: {player_win}')
    print(f'PLAYER AVG RESOURCE AMOUNT: {player_avg_resource_amount}\n')
    print(f'ENEMY WIN: {enemy_win}')
    print(f'ENEMY AVG RESOURCE AMOUNT: {enemy_avg_resource_amount}\n')
    print(f'PLAYER WINRATE = {player_winrate}')
