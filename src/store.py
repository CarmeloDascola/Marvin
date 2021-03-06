import json
import logging

from data import DATA_DIR


STORE_PATH = DATA_DIR + 'store.json'

logger = logging.getLogger('Store')


class Store:
    command_panel_channel_id: int
    table_url: str
    counting_channel_id: int
    ok_channel_id: int

    def load(self) -> bool:
        """ Load stored data. Return whether successful. """
        # Load json
        try:
            with open(STORE_PATH) as f:
                data: dict = json.load(f)
        except FileNotFoundError:
            logger.info(f'{STORE_PATH} not found. Will not load any stored data.')
            data = {}

        logger.info('Loadeding data.')
        logger.debug(data)

        # Set attributes
        for key, value in data.items():
            setattr(self, key, value)

        for attr, _ in self.__annotations__.items():
            setattr(self, attr, data.get(attr, None))

        return True

    def save(self):
        # Get data from attributes
        data = {}

        for attr, _ in self.__annotations__.items():
            value = getattr(self, attr, None)
            data[attr] = value

        # Save json
        with open(STORE_PATH, 'w') as f:
            json.dump(data, f, indent=4)
