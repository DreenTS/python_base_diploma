import logging.config

LOG_CONFIG = {
    'version': 1,
    'formatters': {
        'drones_logger_formatter': {
            'format': '%(asctime)s - [%(levelname)s]: %(message)s',
            'datefmt': '%d-%m-%Y %H:%M',
        },
    },
    'handlers': {
        'file_handler': {
            'class': 'logging.FileHandler',
            'formatter': 'drones_logger_formatter',
            'filename': 'yurikov_drones/game.log',
            'mode': 'a',
            'encoding': 'utf-8',
        },
    },
    'loggers': {
        'drone_logger': {
            'handlers': ['file_handler', ],
            'level': 'DEBUG',
        },
    },
}


def configure_logger():
    logging.config.dictConfig(LOG_CONFIG)
    log = logging.getLogger('drone_logger')
    return log


if __name__ == '__main__':
    drone_logger = configure_logger()
    drone_logger.info(msg='TEST TEST TEST')
    print('Done!!!')
