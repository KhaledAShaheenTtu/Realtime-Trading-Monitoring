import datetime
import json
import logging
import random
import re
import string
import os
# Could be out of stardard Conda package
import requests                             # conda install requests
import pandas as pd                         # conda install pandas
from websocket import create_connection     # conda install websocket-client

logger = logging.getLogger(__name__)


class GetDataTradingView:
    """
    This class is a set of functions to get the price data from TradingView properly. 
    Mostly it's copied from current existing TradingDataFeed project, 
    but we also have to make some additional fixes to make it work on its own. 

    In the end, we use the get_hist() function with the parameters below to retrieve prices in two scenarios:

        (1) Latest candle — fetch the most recent candle with the instrument’s current price.
        (2) Recent history — fetch recent historical data within TradingView’s limits.

    As of now, TradingView provides up to 10,000 candles going backward 
    from the present at no cost (per their ToS).
    
    Source of the code of this Class could be found here (last version - Mar 2024): 
    https://pypi.org/project/tradingview-datafeed/
    
    """
    __sign_in_url = 'https://www.tradingview.com/accounts/signin/'
    __ws_headers = json.dumps({"Origin": "https://data.tradingview.com"})
    __signin_headers = {'Referer': 'https://www.tradingview.com'}
    __ws_timeout = 5

    def __init__(
        self,
        username: str = None,
        password: str = None,
        console_logging: bool = False,
    ) -> None:
        """Create TvDatafeed object

        Args:
            username (str, optional): tradingview username. Defaults to None.
            password (str, optional): tradingview password. Defaults to None.

        """

        self.ws_debug = False

        self.token = self.__auth(username, password)

        if self.token is None:
            self.token = "unauthorized_user_token"
            if console_logging:
                logger.warning(
                    "you are using nologin method, data you access may be limited"
                )
            # logger.warning(
            #     "you are using nologin method, data you access may be limited"
            # )

        self.ws = None
        self.session = self.__generate_session()
        self.chart_session = self.__generate_chart_session()

    def __auth(self, username, password):

        """
        We can use Auth to TradingView with login and password, 
        but we do not need it for our small amounts of recent data 
        (up to 10k candles or something like that)
        since it's available for all for free according to TradingView TOC
        """

        if (username is None or password is None):
            token = None

        else:
            data = {"username": username,
                    "password": password,
                    "remember": "on"}
            try:
                response = requests.post(
                    url=self.__sign_in_url, data=data, headers=self.__signin_headers)
                token = response.json()['user']['auth_token']
            except Exception as e:
                logger.error('error while signin')
                token = None

        return token

    def __create_connection(self):
        logging.debug("creating websocket connection")
        self.ws = create_connection(
            "wss://data.tradingview.com/socket.io/websocket", headers=self.__ws_headers, timeout=self.__ws_timeout
        )

    @staticmethod
    def __filter_raw_message(text):
        try:
            found = re.search('"m":"(.+?)",', text).group(1)
            found2 = re.search('"p":(.+?"}"])}', text).group(1)

            return found, found2
        except AttributeError:
            logger.error("error in filter_raw_message")

    @staticmethod
    def __generate_session():
        stringLength = 12
        letters = string.ascii_lowercase
        random_string = "".join(random.choice(letters)
                                for i in range(stringLength))
        return "qs_" + random_string

    @staticmethod
    def __generate_chart_session():
        stringLength = 12
        letters = string.ascii_lowercase
        random_string = "".join(random.choice(letters)
                                for i in range(stringLength))
        return "cs_" + random_string

    @staticmethod
    def __prepend_header(st):
        return "~m~" + str(len(st)) + "~m~" + st

    @staticmethod
    def __construct_message(func, param_list):
        return json.dumps({"m": func, "p": param_list}, separators=(",", ":"))

    def __create_message(self, func, paramList):
        return self.__prepend_header(self.__construct_message(func, paramList))

    def __send_message(self, func, args):
        m = self.__create_message(func, args)
        if self.ws_debug:
            print(m)
        self.ws.send(m)

    @staticmethod
    def __create_df(raw_data, symbol):
        try:
            out = re.search(r'"s":\[(.+?)\}\]', raw_data).group(1)
            x = out.split(',{"')
            data = list()
            volume_data = True

            for xi in x:
                xi = re.split(r"\[|:|,|\]", xi)
                ts = datetime.datetime.fromtimestamp(float(xi[4]), tz=datetime.timezone.utc)
                row = [ts]

                for i in range(5, 10):

                    # skip converting volume data if does not exists
                    if not volume_data and i == 9:
                        row.append(0.0)
                        continue
                    try:
                        row.append(float(xi[i]))

                    except ValueError:
                        volume_data = False
                        row.append(0.0)
                        logger.debug('no volume data')

                data.append(row)

            data = pd.DataFrame(
                data, columns=["datetime", "open", "high", "low", "close", "volume"]
            ).set_index("datetime")
            data.insert(0, "symbol", value=symbol)
            return data
        except AttributeError:
            print("no data, please check the exchange and symbol")
            logger.error("no data, please check the exchange and symbol")

    @staticmethod
    def __format_symbol(symbol, exchange, contract: int = None):

        if ":" in symbol:
            pass
        elif contract is None:
            symbol = f"{exchange}:{symbol}"

        elif isinstance(contract, int):
            symbol = f"{exchange}:{symbol}{contract}!"

        else:
            raise ValueError("not a valid contract")

        return symbol

    def get_hist(
        self,
        symbol: str,
        exchange: str = "BINANCE",
        interval: str = "5", # default value is 5 min
        n_bars: int = 1,     # default amount of candles is 10
        fut_contract: int = None,
        extended_session: bool = False,
    ) -> pd.DataFrame:
        """get historical data

        Args:
            symbol (str): symbol name
            exchange (str, optional): exchange, not required if symbol is in format EXCHANGE:SYMBOL. 
            Defaults to None.
            interval (str, optional): chart interval. Defaults to 'D'.
            n_bars (int, optional): no of bars to download, max 5000. 
            Defaults to 10.

            fut_contract (int, optional): None for cash, 1 for continuous current contract in front, 
            2 for continuous next contract in front . 
            Defaults to None.

            extended_session (bool, optional): regular session if False, extended session if True, 
            Defaults to False.

        Returns:
            pd.Dataframe: dataframe with sohlcv as columns
        """

        symbol = self.__format_symbol(
            symbol=symbol, exchange=exchange, contract=fut_contract
        )

        self.__create_connection()

        self.__send_message("set_auth_token", [self.token])
        self.__send_message("chart_create_session", [self.chart_session, ""])
        self.__send_message("quote_create_session", [self.session])
        self.__send_message(
            "quote_set_fields",
            [
                self.session,
                "ch",
                "chp",
                "current_session",
                "description",
                "local_description",
                "language",
                "exchange",
                "fractional",
                "is_tradable",
                "lp",
                "lp_time",
                "minmov",
                "minmove2",
                "original_name",
                "pricescale",
                "pro_name",
                "short_name",
                "type",
                "update_mode",
                "volume",
                "currency_code",
                "rchp",
                "rtc",
            ],
        )

        self.__send_message(
            "quote_add_symbols", [self.session, symbol,
                                  {"flags": ["force_permission"]}]
        )
        self.__send_message("quote_fast_symbols", [self.session, symbol])

        self.__send_message(
            "resolve_symbol",
            [
                self.chart_session,
                "symbol_1",
                '={"symbol":"'
                + symbol
                + '","adjustment":"splits","session":'
                + ('"regular"' if not extended_session else '"extended"')
                + "}",
            ],
        )
        self.__send_message(
            "create_series",
            [self.chart_session, "s1", "s1", "symbol_1", interval, n_bars],
        )
        self.__send_message("switch_timezone", [
                            self.chart_session, "exchange"])

        raw_data = ""

        logger.debug(f"getting data for {symbol}...")
        while True:
            try:
                result = self.ws.recv()
                raw_data = raw_data + result + "\n"
            except Exception as e:
                logger.error(e)
                break

            if "series_completed" in result:
                break

        return self.__create_df(raw_data, symbol)

##############################################################################
# Source of the code above:  https://pypi.org/project/tradingview-datafeed/  # 
##############################################################################




class DataWorks: 

    def write_log_line(self, text, file_path="data/logs.csv"):
        """
        Basic function for appending log rows to .csv file.
        Expecting 2 args: 
            (1) f-string with text to be written
            (2) path to csv file for appending the log line 
        """
        try: 
            file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path)
            logging.info(f'{text}')
            timestamp = datetime.datetime.now(tz = datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(f'{timestamp} {text}\n')
                print(text)                                 # to also show in console 
        except Exception as e:
            logging.error(f"Error writing to log file: {e}")
            print(f"Error writing to log file: {e}")
        return

    def convert_timestamp_to_iso(self, timestamp):
        """
        Basic function to convert ISO timestamps to more convenient pandas-timestamps
        """
        dt = datetime.datetime.fromtimestamp(timestamp / 1000.0, tz=datetime.timezone.utc) # 
        return dt.strftime('%Y-%m-%d %H:%M:%S.%f')         # Convert to ISO timestamp
