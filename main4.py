import time
import webbrowser
import requests
import speech_recognition as sr
import pyttsx3
import pyautogui
import yfinance
from ai import ask_ai
import musicLibrary

# Configuration
class Config:
    WAKE_WORD = "jarvis"
    NEWS_API_KEY = "your_newsapi_key_here"  # Replace with your actual key
    SEARCH_DELAY = 1.5
    COMMAND_TIMEOUT = 5
    MAX_RESPONSE_LENGTH = 300
    QUESTION_WORDS = ["what", "who", "when", "where", "why", "how", "tell me", "explain"]

class NewsFetcher:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2/"

    def fetch_news(self, category="general", country="us", page_size=3):
        try:
            url = f"{self.base_url}top-headlines?country={country}&category={category}&pageSize={page_size}&apiKey={self.api_key}"
            response = requests.get(url)
            response.raise_for_status()
            return response.json().get('articles', [])
        except Exception as e:
            print(f"News API error: {e}")
            return None

class VoiceAssistant:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.engine = pyttsx3.init()
        self.news = NewsFetcher(api_key=Config.NEWS_API_KEY)
        self._configure_engine()
        
        if not sr.Microphone.list_microphone_names():
            raise Exception("No microphone detected!")

    def _configure_engine(self):
        voices = self.engine.getProperty('voices')
        self.engine.setProperty('voice', voices[0].id)
        self.engine.setProperty('rate', 150)

    def speak(self, text):
        try:
            print(f"Assistant: {text}")
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"Speech error: {e}")

    def take_screenshot(self):
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            pyautogui.screenshot(filename)
            return filename
        except Exception as e:
            print(f"Screenshot error: {e}")
            return None

    def listen_for_command(self):
        with sr.Microphone() as source:
            print("\nListening for command...")
            try:
                audio = self.recognizer.listen(
                    source, 
                    timeout=Config.COMMAND_TIMEOUT,
                    phrase_time_limit=Config.COMMAND_TIMEOUT
                )
                return self.recognizer.recognize_google(audio).lower()
            except sr.WaitTimeoutError:
                return None
            except Exception as e:
                print(f"Listening error: {e}")
                return None

    def stock_report(self, ticker_input="BTC-USD"):
        try:
            # Asset mapping (TradingView : Yahoo Finance)
            asset_map = {
                "gold": ("XAUUSD", "GC=F"),
                "bitcoin": ("BTCUSD", "BTC-USD"),
                "apple": ("NASDAQ:AAPL", "AAPL"),
                "crude oil": ("OIL", "CL=F"),
                "nifty": ("NSE:NIFTY", "^NSEI"),
                "bank nifty": ("NSE:BANKNIFTY", "^NSEBANK"),
                "reliance": ("NSE:RELIANCE", "RELIANCE.NS")
            }
            
            # Get proper symbols
            tv_symbol, yf_symbol = asset_map.get(ticker_input.lower(), (ticker_input, ticker_input))
            
            # Special handling for cryptocurrencies
            if ticker_input.lower() in ["bitcoin", "btc"]:
                try:
                    # Get crypto data from CoinGecko
                    response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true")
                    data = response.json()
                    current_price = data["bitcoin"]["usd"]
                    change_pct = data["bitcoin"]["usd_24h_change"]
                    
                    # Generate professional analysis
                    analysis = ask_ai(
                        f"Analyze Bitcoin at ${current_price} ({change_pct:+.2f}% change) using SMC/ICT concepts. "
                        "Provide concise 5-line trading plan:\n"
                        "1. [BUY/SELL/WAIT] - [SMC Pattern + ICT Confirmation]\n"
                        "2. Key Levels: [Support] | [Resistance] | [Liquidity]\n"
                        "3. Market Structure: [Bullish/Bearish/Ranging]\n"
                        "4. Risk Management: [Stop Location] | [Risk %]\n"
                        "5. Targets: [TP1] | [TP2] | [Liquidity Run]"
                    )
                    
                    self.speak(f"Bitcoin Professional Analysis:\n{analysis}")
                    webbrowser.open(f"https://www.tradingview.com/chart/?symbol=BTCUSD")
                    return
                    
                except Exception as e:
                    print(f"Crypto API error: {e}")
                    self.speak("Showing Bitcoin chart. Detailed analysis unavailable.")
                    webbrowser.open("https://www.tradingview.com/chart/?symbol=BTCUSD")
                    return

            # For traditional assets (stocks, commodities, indices)
            stock = yfinance.Ticker(yf_symbol)
            data = stock.history(period="15d", interval="1d")
            
            if len(data) < 10:
                raise ValueError("Insufficient historical data")
            
            # Calculate key levels (ICT Power of 3)
            weekly_high = data['High'].max()
            weekly_low = data['Low'].min()
            current_price = data['Close'].iloc[-1]
            
            level_3 = weekly_high - (weekly_high - weekly_low) * 0.236
            level_2 = weekly_high - (weekly_high - weekly_low) * 0.5
            level_1 = weekly_high - (weekly_high - weekly_low) * 0.786
            
            # Generate professional trading signal
            analysis = ask_ai(
                f"Analyze {ticker_input} at {current_price:.2f} using SMC/ICT concepts. "
                f"Key Levels: L3 {level_3:.2f} | L2 {level_2:.2f} | L1 {level_1:.2f}. "
                "Provide exact 5-line response:\n"
                "1. [BUY/SELL/WAIT] - [SMC Pattern + ICT Confirmation]\n"
                "2. Key Levels: [L3] | [L2] | [L1]\n"
                "3. Market Structure: [Bullish/Bearish/Ranging]\n"
                "4. Liquidity Zones: [Above/Below] current price\n"
                "5. Optimal Entry: [price] | Stop Loss: [price]"
            )
            
            self.speak(f"{ticker_input} Professional Analysis:\n{analysis}")
            webbrowser.open(f"https://www.tradingview.com/chart/?symbol={tv_symbol}")
            
        except Exception as e:
            print(f"Analysis error: {e}")
            self.speak(f"Showing {ticker_input} chart. Detailed analysis unavailable.")
            webbrowser.open(f"https://www.tradingview.com/chart/?symbol={tv_symbol}")

    def _handle_news(self, command, category="general"):
        self.speak(f"Fetching {category} news...")
        articles = self.news.fetch_news(category=category)
        
        if not articles:
            self.speak("News unavailable currently")
            return

        for i, article in enumerate(articles[:3], 1):
            title = article["title"].split(" - ")[0]
            self.speak(f"Headline {i}: {title}")
            time.sleep(0.8)

    def _introduce_self(self, _):
        intro = "I am JARVIS with financial and news capabilities. Say 'help' for options."
        self.speak(intro)

    def _open_website(self, url, name):
        webbrowser.open(url)
        self.speak(f"Opening {name}")

    def _handle_music(self, command):
        try:
            song = command.split("play", 1)[1].strip()
            if song in musicLibrary.music:
                webbrowser.open(musicLibrary.music[song])
                self.speak(f"Playing {song}")
            else:
                self.speak(f"Song '{song}' not found")
        except Exception as e:
            print(f"Music error: {e}")
            self.speak("Music playback failed")

    def _handle_screenshot(self, _):
        filename = self.take_screenshot()
        if filename:
            self.speak(f"Screenshot saved as {filename}")
        else:
            self.speak("Screenshot failed")

    def _handle_search(self, command):
        query = command.replace("open", "").strip()
        self.speak(f"Searching for {query}...")
        try:
            pyautogui.press("win")
            pyautogui.typewrite(query)
            time.sleep(Config.SEARCH_DELAY)
            pyautogui.press("enter")
        except Exception as e:
            self.speak("Search failed")
            print(f"Search error: {e}")

    def _show_help(self, _):
        help_text = """Commands:
        - Stocks: 'gold', 'bitcoin', 'apple', 'crude oil', 'nifty', 'bank nifty', 'reliance'
        - News: 'news', 'tech news'
        - Music: 'play [song]'
        - Tools: 'screenshot', 'open [app]'
        - Web: 'open youtube', 'open google'
        - Info: 'help', 'introduce yourself'"""
        self.speak(help_text)

    def process_command(self, command):
        if not command:
            return

        print(f"Processing: {command}")

        # Stock commands
        stock_commands = {
            "gold": "gold",
            "bitcoin": "bitcoin",
            "btc": "bitcoin",
            "apple": "apple",
            "crude oil": "crude oil",
            "nifty": "nifty",
            "bank nifty": "bank nifty",
            "reliance": "reliance"
        }
        for keyword, ticker in stock_commands.items():
            if keyword in command:
                self.stock_report(ticker)
                return

        # News commands
        news_commands = {
            "news": "general",
            "tech news": "technology",
            "sports news": "sports"
        }
        for cmd, category in news_commands.items():
            if cmd in command:
                self._handle_news(command, category)
                return

        # Original commands
        original_handlers = {
            "introduce yourself": self._introduce_self,
            "open google": lambda _: self._open_website("https://google.com", "Google"),
            "open youtube": lambda _: self._open_website("https://youtube.com", "YouTube"),
            "play": self._handle_music,
            "screenshot": self._handle_screenshot,
            "open": self._handle_search,
            "help": self._show_help
        }
        
        for keyword, handler in original_handlers.items():
            if keyword in command:
                handler(command)
                return

        # AI fallback
        try:
            response = ask_ai(command)[:Config.MAX_RESPONSE_LENGTH]
            self.speak(response)
        except Exception as e:
            print(f"AI error: {e}")
            self.speak("Command not recognized")

    def run(self):
        """Main execution loop"""
        self.speak("JARVIS activated")
        while True:
            try:
                with sr.Microphone() as source:
                    print("\nListening for wake word...")
                    audio = self.recognizer.listen(source, phrase_time_limit=3)
                    try:
                        text = self.recognizer.recognize_google(audio).lower()
                        if Config.WAKE_WORD in text:
                            self.speak("Yes?")
                            command = self.listen_for_command()
                            if command:
                                self.process_command(command)
                    except Exception:
                        continue
            except KeyboardInterrupt:
                self.speak("Goodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(1)

if __name__ == "__main__":
    try:
        assistant = VoiceAssistant()
        assistant.run()  # This will now work
    except Exception as e:
        print(f"Startup error: {e}")
