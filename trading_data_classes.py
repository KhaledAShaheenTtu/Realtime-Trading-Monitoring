import datetime
import json
import logging
import random
import re
import string
import os
import socket
import ssl
import base64
import hashlib
import struct
import urllib.parse
import requests                             
import pandas as pd

logger = logging.getLogger(__name__)


class SimpleWebSocket:
    """
    A simple WebSocket client implementation using only standard library components
    (socket, ssl, base64, hashlib) to replace websocket-client dependency.
    """
    
    def __init__(self, url, headers=None, timeout=5):
        self.url = url
        self.headers = headers or {}
        self.timeout = timeout
        self.sock = None
        self.connected = False
        
        # Parse URL
        parsed = urllib.parse.urlparse(url)
        self.host = parsed.hostname
        self.port = parsed.port or (443 if parsed.scheme == 'wss' else 80)
        self.path = parsed.path or '/'
        self.is_secure = parsed.scheme == 'wss'
        
    def connect(self):
        """Establish WebSocket connection with handshake"""
        # Create socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        
        # Wrap with SSL if needed
        if self.is_secure:
            context = ssl.create_default_context()
            self.sock = context.wrap_socket(self.sock, server_hostname=self.host)
        
        # Connect
        self.sock.connect((self.host, self.port))
        
        # WebSocket handshake
        key = base64.b64encode(os.urandom(16)).decode('utf-8')
        
        handshake = (
            f"GET {self.path} HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n"
        )
        
        # Add custom headers
        for header_key, header_value in self.headers.items():
            if isinstance(header_value, dict):
                header_value = json.dumps(header_value)
            handshake += f"{header_key}: {header_value}\r\n"
        
        handshake += "\r\n"
        
        self.sock.send(handshake.encode('utf-8'))
        
        # Read response
        response = b""
        while b"\r\n\r\n" not in response:
            response += self.sock.recv(1)
        
        # Verify handshake response
        if b"101 Switching Protocols" not in response:
            raise Exception("WebSocket handshake failed")
            
        self.connected = True
    
    def _create_frame(self, data, opcode=1):
        """Create WebSocket frame"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        frame = bytearray()
        
        # First byte: FIN (1) + RSV (000) + Opcode (0001 for text)
        frame.append(0x80 | opcode)
        
        # Payload length and masking
        payload_len = len(data)
        if payload_len < 126:
            frame.append(0x80 | payload_len)  # Masked bit + payload length
        elif payload_len < 65536:
            frame.append(0x80 | 126)  # Masked bit + 126
            frame.extend(struct.pack('>H', payload_len))
        else:
            frame.append(0x80 | 127)  # Masked bit + 127  
            frame.extend(struct.pack('>Q', payload_len))
        
        # Masking key (4 bytes)
        mask_key = os.urandom(4)
        frame.extend(mask_key)
        
        # Masked payload
        masked_data = bytearray()
        for i, byte in enumerate(data):
            masked_data.append(byte ^ mask_key[i % 4])
        frame.extend(masked_data)
        
        return bytes(frame)
    
    def send(self, data):
        """Send data through WebSocket"""
        if not self.connected:
            raise Exception("WebSocket not connected")
        
        frame = self._create_frame(data)
        self.sock.send(frame)
    
    def recv(self):
        """Receive data from WebSocket"""
        if not self.connected:
            raise Exception("WebSocket not connected")
        
        # Read first 2 bytes
        header = self.sock.recv(2)
        if len(header) < 2:
            raise Exception("Connection closed")
        
        # Parse header
        fin = (header[0] & 0x80) == 0x80
        opcode = header[0] & 0x0F
        masked = (header[1] & 0x80) == 0x80
        payload_len = header[1] & 0x7F
        
        # Handle extended payload length
        if payload_len == 126:
            payload_len = struct.unpack('>H', self.sock.recv(2))[0]
        elif payload_len == 127:
            payload_len = struct.unpack('>Q', self.sock.recv(8))[0]
        
        # Read mask key if present (server messages shouldn't be masked)
        mask_key = None
        if masked:
            mask_key = self.sock.recv(4)
        
        # Read payload
        payload = b""
        while len(payload) < payload_len:
            chunk = self.sock.recv(payload_len - len(payload))
            if not chunk:
                raise Exception("Connection closed")
            payload += chunk
        
        # Unmask payload if needed
        if masked and mask_key:
            unmasked = bytearray()
            for i, byte in enumerate(payload):
                unmasked.append(byte ^ mask_key[i % 4])
            payload = bytes(unmasked)
        
        # Handle close frame
        if opcode == 8:
            self.close()
            raise Exception("Connection closed by server")
        
        return payload.decode('utf-8')
    
    def close(self):
        """Close WebSocket connection"""
        if self.sock:
            try:
                # Send close frame
                close_frame = self._create_frame(b"", opcode=8)
                self.sock.send(close_frame)
            except:
                pass
            finally:
                self.sock.close()
                self.sock = None
                self.connected = False


def create_connection(url, headers=None, timeout=5):
    """
    Create and connect a WebSocket connection
    (Drop-in replacement for websocket.create_connection)
    """
    # Parse headers if they're provided as JSON string
    parsed_headers = {}
    if headers:
        if isinstance(headers, str):
            try:
                parsed_headers = json.loads(headers)
            except json.JSONDecodeError:
                parsed_headers = {"User-Agent": headers}
        else:
            parsed_headers = headers
    
    ws = SimpleWebSocket(url, parsed_headers, timeout)
    ws.connect()
    return ws


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
#      Its under MIT license, so copy and editing are allowed                # 
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


class Strategy:
    """
    Source code of the trading strategy (for Pine editor) are available pubclicly and declared as open-source
    https://www.tradingview.com/script/uCV8I4xA-Bollinger-RSI-Double-Strategy-by-ChartArt-v1-1/
    
    Has been rewritten for python by us.
    """

    def calculate_rsi(self, prices, period):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_bollinger_bands(self, prices, period, std_dev):
        sma = prices.rolling(window=period).mean()
        rolling_std = prices.rolling(window=period).std()
        upper_band = sma + (rolling_std * std_dev)
        lower_band = sma - (rolling_std * std_dev)
        return sma, upper_band, lower_band
        
    def apply_values_for_double_strat(self, data, close_price_field, instrument):   
        RSI_period = 3
        Bollinger_period = 165
        Bollinger_std_dev = 2
        RSI_overbought = 50
        RSI_oversold = 49
        
        data['RSI_dd_strat'] = self.calculate_rsi(data[close_price_field], RSI_period)
        data['BB_basis'], data['BB_upper'], data['BB_lower']= self.calculate_bollinger_bands(
            data[close_price_field], 
            Bollinger_period, 
            Bollinger_std_dev)

        buy_signal_field_name = 'buy_signal_' + instrument
        sell_signal_field_name = 'sell_signal_' + instrument

        data[buy_signal_field_name] = ((data['RSI_dd_strat'] > RSI_oversold) 
                                            & (data[close_price_field] < data['BB_lower'])).astype('int')
        data[sell_signal_field_name] = ((data['RSI_dd_strat'] < RSI_overbought) 
                                            & (data[close_price_field] > data['BB_upper'])).astype('int')
        return data