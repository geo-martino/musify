import json
from datetime import datetime as dt
from datetime import timedelta
from time import sleep
from typing import Optional

import requests

from syncify.utils_new.api import APIAuthoriser
from syncify.utils.logger import Logger


class RequestHandler(APIAuthoriser, Logger):

    timeout = 300
    backoff_factor = 2

    def handle_request(self, kind: str, url: str, *args, **kwargs) -> Optional[dict]:

        response = requests.request(method=kind.upper(), url=url, headers=self.headers, *args, **kwargs)
        i = self.backoff_factor
        while response.status_code >= 400:
            self._logger.warning(f"\33[91mEndpoint: {url} | Code: {response.status_code}\n{response.text}"
                                 f"\n{response.headers}\33[0m")

            if 'retry-after' in response.headers:  # wait if time is short
                wait_time = int(response.headers['retry-after'])
                wait_dt = dt.now() + timedelta(seconds=wait_time)
                self._logger.info(f"Rate limit exceeded. Retry again at {wait_dt.strftime('%Y-%m-%d %H:%M:%S')}")

                if wait_time > self.timeout:   # exception if too long
                    raise ConnectionError(f"Time to wait to retry is greater than {self.timeout} seconds")

                response = getattr(requests, kind)(url, *args, **kwargs, headers=self.headers)
            elif i < self.timeout:
                self._logger.info(f"Retrying in {i} seconds...")
                sleep(i)
                i *= self.backoff_factor
            else:
                raise ConnectionError("Max retries exceeded")

        try:
            return response.json()
        except json.decoder.JSONDecodeError:
            self._logger.error(f"Endpoint: {url} | Code: {response.status_code} | Response: {response.text}")
