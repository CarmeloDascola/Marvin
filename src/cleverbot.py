import logging
from asyncio import get_event_loop

from selenium.common.exceptions import TimeoutException
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger('Cleverbot')


class Cleverbot(Chrome):
    def __init__(self):
        # Initialize options
        logger.debug('Initializing driver options..')
        _opts = ChromeOptions()
        _opts.add_argument('--headless')
        _opts.add_argument('--log-level=3')  # fatal

        # Initialize the browser
        logger.debug('Initializing browser..')
        super().__init__(options=_opts)

        # Get the url
        logger.debug('Loading cleverbot..')
        self.get('https://www.cleverbot.com')

        # Locate the input box
        logger.debug('Locating elements..')
        self.input_box = self.find_element_by_xpath(
            '//*[@id="avatarform"]/input[1]')

    async def communicate(self, string: str):
        # Type the input in
        self.input_box.send_keys(string + '\n')

        # Wait for reply by looking for the yellow snip icon
        try:
            WebDriverWait(self, 10).until(
                EC.visibility_of_element_located((By.ID, 'snipTextIcon')))
        except TimeoutException:
            return ('I am sorry, I am not feeling very well today. I have'
                    ' eaten a *TimeoutException*.. :frowning:*')

        # Return the reply
        return self.find_element_by_xpath('//*[@id="line1"]/span[1]').text


async def test(cb: Cleverbot):
    for i in range(10):
        response = await cb.communicate(str(i))
        print(response)


if __name__ == "__main__":
    cb = Cleverbot()
    loop = get_event_loop()
    loop.run_until_complete(loop.create_task(test(cb)))
