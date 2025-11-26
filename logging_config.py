import logging
import logging.config
import config

def setup_logging():
    """
    Konfiguruje system logowania:
    - Zapisuje komunikaty INFO i wyższe do pliku 'smart_home.log'.
    - Zapisuje komunikaty DEBUG i wyższe do konsoli (StreamHandler).
    """
    log_format = (
        "[%(asctime)s] "
        "[%(levelname)-8s] "
        "[%(name)s] "
        "%(message)s")

    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': log_format,
                'datefmt': '%d-%m-%Y %H:%M:%S'
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'standard',
                'level': logging.DEBUG,
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'formatter': 'standard',
                'filename': config.LOG_FILE_PATH,
                'maxBytes': 1024 * 1024 * 5,  # 5 MB
                'backupCount': 5,
                'level': config.LOG_LEVEL if hasattr(config, 'LOG_LEVEL') else logging.INFO,
            },
        },
        'loggers': {
            # Logger główny
            '': { 
                'handlers': ['console', 'file'],
                'level': logging.INFO,
                'propagate': True
            },
            # Logger Paho-MQTT
            'paho-mqtt': {
                'handlers': ['console', 'file'],
                'level': logging.WARNING,
                'propagate': False
            }
        }
    }

    logging.config.dictConfig(logging_config)
    logging.info("System logowania został zainicjalizowany.")