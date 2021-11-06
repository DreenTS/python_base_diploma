LOG_FILENAME = 'game_with_gun.log'
WINNER_PATTERN = 'WINNER'
PLAYER_WINNER_PATTERN = 'WINNER: YurikovDrone'
PLAYER_RESOURCE_AMOUNT = 'YurikovDrone: '

if __name__ == '__main__':
    with open(LOG_FILENAME, 'r', encoding='utf-8') as file:
        game = file.readlines()
    runs_total = 0
    player_win = 0
    player_total_resources = 0

    for line in game:
        if WINNER_PATTERN in line:
            runs_total += 1
        if PLAYER_WINNER_PATTERN in line:
            player_win += 1
        elif PLAYER_RESOURCE_AMOUNT in line:
            player_total_resources += int(line[len(PLAYER_RESOURCE_AMOUNT):])

    player_winrate = player_win / runs_total * 100
    player_avg_resource_amount = player_total_resources / runs_total

    print(f'RUNS TOTAL: {runs_total}\n')
    print(f'PLAYER WIN: {player_win}')
    print(f'PLAYER AVG RESOURCE AMOUNT: {player_avg_resource_amount}\n')
    print(f'PLAYER WINRATE = {player_winrate}')
