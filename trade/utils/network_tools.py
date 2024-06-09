import csv
import os
from abc import ABC
from io import BytesIO
from typing import Optional, Tuple
from urllib.error import HTTPError
from urllib.parse import urlparse
from zipfile import ZipFile

import requests
from pandas import DataFrame, read_csv, read_excel
from requests import Session
from requests.exceptions import ConnectionError, InvalidURL, ReadTimeout

from trade.utils.html_parsing import HtmlParser
import warnings


warnings.simplefilter(action='ignore', category=FutureWarning)

CHUNK_SIZE = 1024
INVALID_URL = "URL: {0}, Status Code:{1}"
RECEIVED_STATUS = "Status Code Received: {0}"
UNKNOWN_CONTENT = "Unknown Content type."


class CustomHTTPException(Exception):
    pass


class DownloadTools(ABC):

    def match_http(self, result, status_code: int, url: Optional[str] = None):
        msg = ""
        match status_code:
            case 200:
                return result

            case 404:
                raise InvalidURL(INVALID_URL.format(url, result.status_code))

            case 403:
                msg = RECEIVED_STATUS.format(status_code)
                if url is not None:
                    msg += ". For url: {0}".format(url)

                raise CustomHTTPException(msg)

            case _:
                raise CustomHTTPException(RECEIVED_STATUS.format(status_code))

    def parse_through_html(self, url: str, headers: dict, tags: Tuple[str]) -> str:

        html_parser = HtmlParser(url, headers, tags)

        return html_parser.get_latest_file()

    def get_cookies(self, base_url: str, headers: dict, timeout: int = 5) -> dict:

        url = self.extract_domain(base_url)

        session = Session()
        try:
            request = session.get(url, headers=headers, timeout=timeout)

        except (ConnectionError, ReadTimeout) as msg:
            return self.get_cookies(url, headers)

        return dict(request.cookies)

    def get_request_api(
        self, url: str, headers: dict, cookies: Optional[dict] = None, **kwargs
    ):

        cookies = self.get_cookies(url, headers)
        result = requests.get(url, headers=headers, cookies=cookies, **kwargs)
        return self.match_http(result, result.status_code, url)

    def extract_domain(self, url: str) -> str:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc

        return "https://" + domain

    def get_headers(self, url):
        return requests.head(url)

    def download_data(self, url: str, headers: Optional[str] = None) -> DataFrame:
        """
        For a given url and file name
        download data to the provided filename/path.
        """
        domain = self.extract_domain(url)
        cookies = self.get_cookies(domain, headers)
        response = self.get_request_api(url, headers, cookies)

        bytes_obj = BytesIO(response.content)

        if self.is_zip(bytes_obj):
            bytes_obj = self.unzip(bytes_obj)

        try:
            result = self.read_from_buffer(bytes_obj)
        except ValueError:
            result = self.read_from_buffer(response.content)

        return result

    def unzip(self, source_buffer: BytesIO) -> bytes:
        """
        Extracts content of the zip file and
        returns a reference to the extracted CSV file.
        :param source_buffer: Path to the source Zip Bytes.
        :return: str
        """
        zip_file = ZipFile(source_buffer)
        file_name = zip_file.namelist()[0]
        csv_buffer = BytesIO(zip_file.read(file_name))
        zip_file.close()

        return csv_buffer

    def is_zip(self, byte_obj: BytesIO):
        zip_signature = b"PK\x03\x04"

        return byte_obj.getvalue().startswith(zip_signature)

    def is_xlsx(self, byte_obj: BytesIO) -> bool:
        xlsx_signature = b"PK\x03\x04"

        if hasattr(byte_obj, "startswith"):
            return byte_obj.startswith(xlsx_signature)

        return False

    def is_csv(self, byte_obj: BytesIO):
        try:
            content = byte_obj.getvalue().decode("utf-8")
            dialect = csv.Sniffer().sniff(content)
            # TODO: Handle _csv.Error here.
            return True

        except (UnicodeDecodeError, csv.Error, AttributeError):
            return False

    def read_csv(self, bytes_obj: BytesIO) -> DataFrame:
        return read_csv(bytes_obj)

    def read_xlsx(self, bytes_obj: BytesIO) -> DataFrame:
        try:
            return read_excel(bytes_obj)
        except ValueError:
            return read_excel(bytes_obj, engine="openpyxl")

    def read_from_buffer(self, bytes_obj: BytesIO):
        if self.is_csv(bytes_obj):
            return self.read_csv(bytes_obj)

        elif self.is_xlsx(bytes_obj):
            return self.read_xlsx(bytes_obj)

        else:
            raise ValueError(UNKNOWN_CONTENT)
