import time
import webbrowser
import threading
import speech_recognition as sr
import pyttsx3
import pyautogui
import json
import os
import logging
import random
import requests
from difflib import SequenceMatcher
from datetime import datetime

# Try to import optional modules
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    print("⚠️ Keyboard module not installed. Hotkey support disabled.")

try:
    import screen_brightness_control as sbc
    BRIGHTNESS_AVAILABLE = True
except ImportError:
    BRIGHTNESS_AVAILABLE = False
    print("⚠️ Brightness control module not installed.")

# Import your custom modules
try:
    from ai import AIClient
    AI_AVAILABLE = True
    print("✅ AI module loaded successfully")
except ImportError as e:
    AI_AVAILABLE = False
    print(f"⚠️ AI module not available: {e}")

try:
    import musicLibrary
    MUSIC_AVAILABLE = True
    print(f"✅ Music library loaded with {len(musicLibrary.music)} songs")
except ImportError as e:
    MUSIC_AVAILABLE = False
    print(f"⚠️ Music library not available: {e}")

# Configuration
class Config:
    def __init__(self):
        self.config = self._load_config()
    
    def _load_config(self):
        default_config = {
            "wake_word": "jarvis",
            "search_delay": 1.0,
            "command_timeout": 3,
            "ai_timeout": 8,
            "question_words": ["what", "who", "when", "where", "why", "how", "tell me", "explain"],
            "team_members": {
                "first": {"name": "Tejas Manwade", "role": "Project Lead"},
                "second": {"name": "Vaibhav Patil", "role": "Systems Development"},
                "third": {"name": "Sachin Mahajan", "role": "Interface Design"},
                "fourth": {"name": "Rohit Mahajan", "role": "Data Analytics"}
            },
            "predefined_responses": {
                "what's your name": "I'm JARVIS, your voice assistant.",
                "who made you": "I was created by Tejas, Vaibhav, Sachin and Rohit.",
                "hello": "Hello! How can I help you today?",
                "what time is it": "The current time is {time}.",
                "how are you": "I'm functioning at optimal levels, thank you!",
                "what can you do": "I can open websites, play music, answer questions, and take screenshots. Say 'help' for details.",
                "tell me a joke": "Why don't scientists trust atoms? Because they make up everything!",
                "goodbye": "Goodbye! Shutting down systems.",
                "open website": "I can open websites like Google, YouTube, Facebook, LinkedIn, and Gmail.",
                "play music": "I can play songs like Believer, Despacito, Shape of You, and more.",
                "take screenshot": "I can take screenshots of your screen.",
                "search": "I can search for things on your computer."
            },
            "screenshot_dir": "screenshots",
            "log_file": "jarvis.log",
            "sensitive_commands": ["shutdown", "format", "delete", "uninstall", "rm -rf", "format c:"],
            "wake_word_threshold": 0.7,
            "command_similarity_threshold": 0.6,
            "hotkey": "ctrl+alt+j",
            "ai_model": "deepseek/deepseek-r1:free",
            "ai_temperature": 0.7,
            "ai_max_tokens": 200
        }
        
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r") as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
                    print("✅ Configuration loaded from config.json")
        except Exception as e:
            print(f"⚠️ Error loading config file: {e}, using defaults")
        
        return default_config
    
    def __getitem__(self, key):
        return self.config[key]
    
    def get(self, key, default=None):
        return self.config.get(key, default)

CONFIG = Config()

class VoiceAssistant:
    def __init__(self):
        print("🚀 Initializing JARVIS Voice Assistant...")
        
        # Initialize speech recognition
        try:
            self.recognizer = sr.Recognizer()
            print("✅ Speech recognition initialized")
        except Exception as e:
            print(f"❌ Failed to initialize speech recognition: {e}")
            raise
        
        # Initialize text-to-speech
        try:
            self.engine = pyttsx3.init()
            self._configure_engine()
            print("✅ Text-to-speech initialized")
        except Exception as e:
            print(f"❌ Failed to initialize TTS: {e}")
            raise
        
        # Initialize AI client if available
        self.ai_client = None
        if AI_AVAILABLE:
            try:
                self.ai_client = AIClient()
                print("✅ AI client initialized with OpenRouter")
            except Exception as e:
                print(f"⚠️ AI client initialization failed: {e}")
                self.ai_client = None
        else:
            print("ℹ️ AI features disabled")
        
        # State management
        self.last_command_time = 0
        self.command_cooldown = 2
        self.is_processing = False
        self.speech_lock = threading.Lock()
        self.command_history = []
        self.conversation_memory = []
        self.current_music = None
        
        # Responses
        self.responses = {
            'acknowledgment': ["Yes?", "How can I help?", "I'm listening", "At your service"],
            'confirmation': ["Done", "Completed", "Finished", "All set"],
            'error': ["Sorry, I couldn't do that", "An error occurred", "Something went wrong"],
            'not_understood': ["I didn't catch that", "Could you repeat that?", "Say again?"],
            'welcome': ["You're welcome", "Happy to help", "My pleasure"],
            'music': ["Now playing", "Enjoy the music", "Playing your requested song"]
        }
        
        # Setup logging
        self.setup_logging()
        
        # Create directories
        self._create_directories()
        
        # Check microphone
        self._check_microphone()
        
        # Register hotkey if available
        if KEYBOARD_AVAILABLE:
            self._register_hotkey()
        else:
            print("ℹ️ Hotkey support disabled (keyboard module not installed)")
        
        # List available songs
        if MUSIC_AVAILABLE:
            print(f"🎵 Available songs: {', '.join(list(musicLibrary.music.keys())[:5])}...")
        
        print("✅ JARVIS initialization complete!")
    
    def _configure_engine(self):
        """Configure text-to-speech engine"""
        try:
            voices = self.engine.getProperty('voices')
            if len(voices) > 0:
                self.engine.setProperty('voice', voices[0].id)
            self.engine.setProperty('rate', 160)
            self.engine.setProperty('volume', 0.9)
        except Exception as e:
            print(f"⚠️ Could not configure TTS engine: {e}")
    
    def setup_logging(self):
        """Setup logging configuration"""
        try:
            logging.basicConfig(
                filename=CONFIG["log_file"],
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            self.logger = logging.getLogger("JARVIS")
            
            # Also log to console
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(levelname)s - %(message)s')
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
            self.logger.info("Logging initialized")
        except Exception as e:
            print(f"⚠️ Failed to setup logging: {e}")
            self.logger = None
    
    def _create_directories(self):
        """Create necessary directories"""
        try:
            os.makedirs(CONFIG["screenshot_dir"], exist_ok=True)
            os.makedirs("logs", exist_ok=True)
        except Exception as e:
            print(f"⚠️ Failed to create directories: {e}")
    
    def _check_microphone(self):
        """Check if microphone is available"""
        try:
            mics = sr.Microphone.list_microphone_names()
            if not mics:
                print("⚠️ No microphone detected!")
                raise Exception("No microphone detected!")
            print(f"✅ Microphone detected: {mics[0]}")
        except Exception as e:
            print(f"❌ Microphone check failed: {e}")
            raise
    
    def _register_hotkey(self):
        """Register global hotkey for activation"""
        if not KEYBOARD_AVAILABLE:
            return
            
        try:
            def on_hotkey():
                if not self.is_processing:
                    print("🔥 Hotkey activated")
                    if self.logger:
                        self.logger.info("Hotkey activated")
                    self.speak("Hotkey activated")
                    command = self.listen_for_command()
                    if command:
                        self.process_command(command)
            
            keyboard.add_hotkey(CONFIG["hotkey"], on_hotkey)
            print(f"✅ Hotkey {CONFIG['hotkey']} registered")
        except Exception as e:
            print(f"⚠️ Failed to register hotkey: {e}")
    
    def speak(self, text):
        """Speak text in a separate thread"""
        def _speak():
            with self.speech_lock:
                try:
                    if self.logger:
                        self.logger.info(f"Speaking: {text}")
                    print(f"🤖 Assistant: {text}")
                    engine = pyttsx3.init()
                    engine.say(text)
                    engine.runAndWait()
                    engine.stop()
                except Exception as e:
                    error_msg = f"Speech error: {e}"
                    print(f"❌ {error_msg}")
                    if self.logger:
                        self.logger.error(error_msg)

        threading.Thread(target=_speak, daemon=True).start()
    
    def get_random_response(self, category):
        """Get a random response from a category"""
        return random.choice(self.responses.get(category, ["Okay"]))
    
    def take_screenshot(self):
        """Take a screenshot and save it"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(CONFIG["screenshot_dir"], f"screenshot_{timestamp}.png")
            screenshot = pyautogui.screenshot()
            screenshot.save(filename)
            print(f"📸 Screenshot saved: {filename}")
            if self.logger:
                self.logger.info(f"Screenshot saved: {filename}")
            return filename
        except Exception as e:
            error_msg = f"Screenshot error: {e}"
            print(f"❌ {error_msg}")
            if self.logger:
                self.logger.error(error_msg)
            return None
    
    def listen_for_command(self):
        """Listen for a voice command"""
        with sr.Microphone() as source:
            print("\n🎤 Listening for command...")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.8)
            
            try:
                audio = self.recognizer.listen(
                    source,
                    timeout=CONFIG["command_timeout"],
                    phrase_time_limit=5
                )
                text = self.recognizer.recognize_google(audio, language="en-US").lower()
                print(f"👤 User said: {text}")
                if self.logger:
                    self.logger.info(f"Recognized: {text}")
                return text
            except sr.UnknownValueError:
                self.speak(self.get_random_response('not_understood'))
                return None
            except sr.WaitTimeoutError:
                print("⏰ Listening timeout")
                return None
            except Exception as e:
                error_msg = f"Recognition error: {e}"
                print(f"❌ {error_msg}")
                if self.logger:
                    self.logger.error(error_msg)
                return None
    
    def _is_wake_word(self, text):
        """Verify if wake word was actually spoken"""
        if not text:
            return False
        
        words = text.split()
        for word in words:
            similarity = SequenceMatcher(None, word, CONFIG["wake_word"]).ratio()
            if similarity >= CONFIG["wake_word_threshold"]:
                return True
        
        # Also check for exact phrase
        if CONFIG["wake_word"] in text:
            return True
        
        return False
    
    def find_best_match(self, command, command_list):
        """Find best matching command using fuzzy matching"""
        best_match = None
        best_ratio = 0
        
        for possible_command in command_list:
            ratio = SequenceMatcher(None, command, possible_command).ratio()
            if ratio > best_ratio and ratio > CONFIG["command_similarity_threshold"]:
                best_ratio = ratio
                best_match = possible_command
        
        return best_match
    
    def get_predefined_response(self, question):
        """Check for instant predefined answers"""
        question = question.lower().strip()
        
        # First check exact matches
        for q, answer in CONFIG["predefined_responses"].items():
            if q in question:
                # Format with current time if needed
                if "{time}" in answer:
                    answer = answer.format(time=datetime.now().strftime("%I:%M %p"))
                return answer
        
        # Then check for similar questions
        best_match = self.find_best_match(question, CONFIG["predefined_responses"].keys())
        if best_match:
            answer = CONFIG["predefined_responses"][best_match]
            if "{time}" in answer:
                answer = answer.format(time=datetime.now().strftime("%I:%M %p"))
            return answer
        
        return None
    
    def _check_sensitive_command(self, command):
        """Check if command is sensitive and requires verification"""
        for sensitive in CONFIG["sensitive_commands"]:
            if sensitive in command:
                return True
        return False
    
    def _verify_sensitive_command(self, command):
        """Verify sensitive command with user"""
        self.speak("This command requires authorization. Say 'authorize' to proceed or 'cancel' to stop.")
        verification = self.listen_for_command()
        
        if verification and "authorize" in verification:
            self.speak("Authorization confirmed. Proceeding.")
            return True
        else:
            self.speak("Command cancelled.")
            return False
    
    def _open_website(self, url, name):
        """Open a website"""
        try:
            webbrowser.open(url)
            self.speak(f"Opening {name}")
            print(f"🌐 Opening {name}")
            if self.logger:
                self.logger.info(f"Opened website: {name} ({url})")
        except Exception as e:
            error_msg = f"Failed to open {name}: {e}"
            self.speak(f"Failed to open {name}")
            print(f"❌ {error_msg}")
    
    def _handle_music(self, command=None):
        """Handle music playback"""
        if not MUSIC_AVAILABLE:
            self.speak("Music library is not available")
            return
            
        try:
            if not command:
                self.speak("Please say 'play' followed by a song name")
                return
            
            # Extract song name from command
            song_name = None
            if "play" in command.lower():
                parts = command.lower().split("play")
                if len(parts) > 1:
                    song_name = parts[1].strip()
            
            if not song_name:
                self.speak("Please say 'play' followed by a song name")
                return
            
            # Check for music genres or categories
            if song_name in musicLibrary.music:
                url = musicLibrary.music[song_name]
                self.current_music = song_name
                webbrowser.open(url)
                self.speak(f"Playing {song_name}")
                print(f"🎵 Playing: {song_name}")
                if self.logger:
                    self.logger.info(f"Playing song: {song_name}")
            else:
                # Try fuzzy matching for song names
                available_songs = list(musicLibrary.music.keys())
                best_match = self.find_best_match(song_name, available_songs)
                if best_match:
                    url = musicLibrary.music[best_match]
                    self.current_music = best_match
                    webbrowser.open(url)
                    self.speak(f"Playing {best_match}")
                    print(f"🎵 Playing (fuzzy match): {best_match}")
                    if self.logger:
                        self.logger.info(f"Playing song (fuzzy match): {best_match}")
                else:
                    # List available songs
                    self.speak(f"I couldn't find {song_name} in my library. I have songs like {', '.join(list(musicLibrary.music.keys())[:3])}")
        except Exception as e:
            error_msg = f"Music error: {e}"
            self.speak("I couldn't play that song")
            print(f"❌ {error_msg}")
            if self.logger:
                self.logger.error(error_msg)
    
    def _list_music(self):
        """List available music"""
        if not MUSIC_AVAILABLE:
            self.speak("Music library is not available")
            return
        
        try:
            songs = list(musicLibrary.music.keys())
            if songs:
                self.speak(f"I have {len(songs)} songs including {', '.join(songs[:5])}")
                print(f"📋 Available songs: {', '.join(songs)}")
            else:
                self.speak("My music library is empty")
        except Exception as e:
            error_msg = f"Music listing error: {e}"
            self.speak("Could not list music")
            print(f"❌ {error_msg}")
    
    def _pause_music(self):
        """Pause music by pressing space"""
        try:
            pyautogui.press('space')
            self.speak("Music paused")
            print("⏸️ Music paused")
        except Exception as e:
            error_msg = f"Pause error: {e}"
            self.speak("Could not pause music")
            print(f"❌ {error_msg}")
    
    def _next_track(self):
        """Next track"""
        try:
            pyautogui.press('shift+n')  # Common shortcut for next track
            self.speak("Next track")
            print("⏭️ Next track")
        except Exception as e:
            error_msg = f"Next track error: {e}"
            self.speak("Could not skip to next track")
            print(f"❌ {error_msg}")
    
    def _introduce_self(self):
        """Introduce the assistant"""
        intro = f"""
        I am JARVIS, your intelligent voice assistant created by {CONFIG['team_members']['first']['name']} and team.
        I can help you with web browsing, playing {len(musicLibrary.music) if MUSIC_AVAILABLE else '0'} songs from my library,
        answering questions using AI, taking screenshots, and system control.
        Just say '{CONFIG['wake_word']}' followed by your command!
        """
        self.speak(intro)
        print("ℹ️ Assistant introduction")
    
    def _introduce_team(self):
        """Introduce the development team"""
        self.speak("Our development team consists of:")
        for member in CONFIG["team_members"].values():
            self.speak(f"{member['name']}, {member['role']}")
        print("👥 Team introduction")
        if self.logger:
            self.logger.info("Introduced team members")
    
    def _handle_screenshot(self):
        """Handle screenshot command"""
        filename = self.take_screenshot()
        if filename:
            self.speak(f"Screenshot saved as {os.path.basename(filename)}")
        else:
            self.speak("Failed to take screenshot")
    
    def _handle_system_command(self, command):
        """Handle system-level commands"""
        command_lower = command.lower()
        
        if "volume up" in command_lower:
            for _ in range(3):  # Press volume up 3 times
                pyautogui.press("volumeup")
            self.speak("Volume increased")
            return True
        elif "volume down" in command_lower:
            for _ in range(3):  # Press volume down 3 times
                pyautogui.press("volumedown")
            self.speak("Volume decreased")
            return True
        elif "mute" in command_lower or "unmute" in command_lower:
            pyautogui.press("volumemute")
            self.speak("Audio toggled")
            return True
        elif "brightness" in command_lower and BRIGHTNESS_AVAILABLE:
            self._adjust_brightness(command_lower)
            return True
        elif "lock screen" in command_lower or "lock computer" in command_lower:
            self._lock_screen()
            return True
        elif "pause" in command_lower and "music" in command_lower:
            self._pause_music()
            return True
        elif "next" in command_lower and ("track" in command_lower or "song" in command_lower):
            self._next_track()
            return True
        return False
    
    def _adjust_brightness(self, command):
        """Adjust screen brightness (platform-specific)"""
        try:
            if "increase" in command or "up" in command:
                current = sbc.get_brightness()
                if isinstance(current, list):
                    current = current[0]
                new_brightness = min(100, current + 20)
                sbc.set_brightness(new_brightness)
                self.speak(f"Brightness increased to {new_brightness}%")
                print(f"💡 Brightness: {new_brightness}%")
            elif "decrease" in command or "down" in command:
                current = sbc.get_brightness()
                if isinstance(current, list):
                    current = current[0]
                new_brightness = max(0, current - 20)
                sbc.set_brightness(new_brightness)
                self.speak(f"Brightness decreased to {new_brightness}%")
                print(f"💡 Brightness: {new_brightness}%")
        except Exception as e:
            error_msg = f"Brightness adjustment error: {e}"
            self.speak("Could not adjust brightness")
            print(f"❌ {error_msg}")
    
    def _lock_screen(self):
        """Lock the computer screen"""
        try:
            if os.name == 'nt':  # Windows
                import ctypes
                ctypes.windll.user32.LockWorkStation()
                self.speak("Screen locked")
                print("🔒 Screen locked")
            else:
                self.speak("Screen lock not supported on this system")
        except Exception as e:
            error_msg = f"Screen lock error: {e}"
            self.speak("Could not lock screen")
            print(f"❌ {error_msg}")
    
    def _handle_search(self, command):
        """Handle search command"""
        query = command.replace("open", "").replace("search", "").strip()
        self.speak(f"Searching for {query}...")
        print(f"🔍 Searching for: {query}")
        try:
            pyautogui.press("win")
            time.sleep(0.5)
            pyautogui.typewrite(query)
            time.sleep(CONFIG["search_delay"])
            pyautogui.press("enter")
            if self.logger:
                self.logger.info(f"Search performed: {query}")
        except Exception as e:
            error_msg = f"Search error: {e}"
            self.speak("Couldn't perform the search")
            print(f"❌ {error_msg}")
    
    def _show_help(self):
        """Show help information"""
        help_text = f"""I can help you with:
        - Opening websites like Google, YouTube, Facebook, LinkedIn, Gmail
        - Playing music from my library of {len(musicLibrary.music) if MUSIC_AVAILABLE else '0'} songs
        - Answering questions using AI (OpenRouter)
        - Taking screenshots
        - Searching your computer
        - Controlling volume and brightness
        - Locking your screen
        - Pausing and skipping music tracks
        Just say '{CONFIG['wake_word']}' followed by your command!"""
        self.speak(help_text)
        print("ℹ️ Help information displayed")
    
    def _handle_conversation(self, command):
        """Handle conversational commands"""
        command_lower = command.lower()
        
        if "thank you" in command_lower or "thanks" in command_lower:
            self.speak(self.get_random_response('welcome'))
            return True
        elif "remember that" in command_lower:
            thing_to_remember = command_lower.split("remember that")[-1].strip()
            self.conversation_memory.append(thing_to_remember)
            self.speak(f"I'll remember that {thing_to_remember}")
            print(f"💭 Remembered: {thing_to_remember}")
            if self.logger:
                self.logger.info(f"Remembered: {thing_to_remember}")
            return True
        elif "what do you remember" in command_lower:
            if self.conversation_memory:
                memories = ", ".join(self.conversation_memory[-3:])  # Last 3 memories
                self.speak(f"I remember: {memories}")
            else:
                self.speak("I don't remember anything yet")
            return True
        elif "forget everything" in command_lower:
            self.conversation_memory.clear()
            self.speak("I've cleared my memory")
            return True
        elif "list songs" in command_lower or "available music" in command_lower:
            self._list_music()
            return True
        elif "what song" in command_lower and "playing" in command_lower:
            if self.current_music:
                self.speak(f"Currently playing {self.current_music}")
            else:
                self.speak("No music is currently playing")
            return True
        
        return False
    
    def _handle_ai_query(self, question):
        """Handle AI questions with instant fallback"""
        # First check predefined answers
        instant_response = self.get_predefined_response(question)
        if instant_response:
            self.speak(instant_response)
            return
        
        # Check if AI is available
        if not self.ai_client:
            self.speak("AI features are currently unavailable")
            print("ℹ️ AI features disabled")
            return
        
        # Otherwise use AI
        self.speak("Let me think about that...")
        print("🤔 Processing AI query...")
        try:
            response = self.ai_client.ask_ai(
                question=question,
                model=CONFIG["ai_model"],
                temperature=CONFIG["ai_temperature"],
                max_tokens=CONFIG["ai_max_tokens"]
            )
            # Limit response length and speak
            spoken_response = response[:250] + "..." if len(response) > 250 else response
            self.speak(spoken_response)
            print(f"🤖 AI Response: {response[:100]}...")
            if self.logger:
                self.logger.info(f"AI Query: {question[:50]}... Response: {response[:100]}...")
        except Exception as e:
            error_msg = f"AI Error: {e}"
            self.speak("I'm having trouble answering that right now")
            print(f"❌ {error_msg}")
            if self.logger:
                self.logger.error(error_msg)
    
    def process_command(self, command):
        """Process a voice command"""
        if not command or self.is_processing:
            return
        
        self.is_processing = True
        self.last_command_time = time.time()
        
        # Log command
        if self.logger:
            self.logger.info(f"Command received: {command}")
        self.command_history.append({
            'timestamp': datetime.now().isoformat(),
            'command': command
        })
        
        # Check for sensitive commands
        if self._check_sensitive_command(command):
            if not self._verify_sensitive_command(command):
                self.is_processing = False
                return
        
        print(f"👤 User: {command}")
        
        # Handle conversational commands
        if self._handle_conversation(command):
            self.is_processing = False
            return
        
        # Handle system commands
        if self._handle_system_command(command):
            self.is_processing = False
            return
        
        # Handle AI questions first
        if (CONFIG["wake_word"] in command or 
            any(q in command.lower() for q in CONFIG["question_words"])):
            question = command.replace(CONFIG["wake_word"], "").strip()
            if question:
                self._handle_ai_query(question)
                self.is_processing = False
                return
        
        # Predefined commands
        command_actions = {
            "introduce yourself": self._introduce_self,
            "who are you": self._introduce_self,
            "open google": lambda: self._open_website("https://google.com", "Google"),
            "open youtube": lambda: self._open_website("https://youtube.com", "YouTube"),
            "open facebook": lambda: self._open_website("https://facebook.com", "Facebook"),
            "open linkedin": lambda: self._open_website("https://linkedin.com", "LinkedIn"),
            "open gmail": lambda: self._open_website("https://mail.google.com", "Gmail"),
            "play": lambda: self._handle_music(command),
            "introduce team": self._introduce_team,
            "team members": self._introduce_team,
            "screenshot": self._handle_screenshot,
            "capture screen": self._handle_screenshot,
            "open": lambda: self._handle_search(command),
            "search": lambda: self._handle_search(command),
            "help": self._show_help,
            "what can you do": self._show_help,
            "show history": lambda: self._show_command_history(),
            "clear history": lambda: self._clear_command_history(),
            "list music": self._list_music,
            "available songs": self._list_music,
            "pause music": self._pause_music,
            "next song": self._next_track,
            "next track": self._next_track
        }
        
        # Try exact match first
        command_executed = False
        for cmd, action in command_actions.items():
            if cmd in command.lower():
                action()
                command_executed = True
                break
        
        # If no exact match, try fuzzy matching
        if not command_executed:
            best_match = self.find_best_match(command, command_actions.keys())
            if best_match:
                self.speak(f"Did you mean '{best_match}'?")
                confirm = self.listen_for_command()
                if confirm and any(word in confirm.lower() for word in ["yes", "yep", "correct", "sure", "okay"]):
                    command_actions[best_match]()
                else:
                    self.speak("Command not recognized. Try 'help' for options.")
            else:
                self.speak("Command not recognized. Try 'help' for options.")
        
        self.is_processing = False
    
    def _show_command_history(self):
        """Show command history"""
        if not self.command_history:
            self.speak("No commands in history")
            return
        
        self.speak(f"Last {min(3, len(self.command_history))} commands:")
        for item in self.command_history[-3:]:
            self.speak(item['command'])
    
    def _clear_command_history(self):
        """Clear command history"""
        self.command_history.clear()
        self.speak("Command history cleared")
    
    def run(self):
        """Main run loop"""
        self.speak("JARVIS initialized and ready for commands!")
        print("✅ JARVIS running...")
        
        print("\n" + "="*50)
        print("🎯 JARVIS Voice Assistant")
        print(f"📢 Say '{CONFIG['wake_word']}' to activate")
        if MUSIC_AVAILABLE:
            print(f"🎵 Music Library: {len(musicLibrary.music)} songs")
        if AI_AVAILABLE:
            print(f"🤖 AI: {CONFIG['ai_model']}")
        if KEYBOARD_AVAILABLE:
            print(f"⌨️  Press {CONFIG['hotkey']} for quick activation")
        print("="*50 + "\n")
        
        try:
            while True:
                with sr.Microphone() as source:
                    print("\n🔊 Listening for wake word...")
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    
                    try:
                        audio = self.recognizer.listen(source, timeout=1.5)
                        text = self.recognizer.recognize_google(audio).lower()
                        
                        if self._is_wake_word(text) and not self.is_processing:
                            self.speak(self.get_random_response('acknowledgment'))
                            command = self.listen_for_command()
                            if command:
                                self.process_command(command)
                        
                    except sr.UnknownValueError:
                        continue
                    except sr.WaitTimeoutError:
                        continue
                    except Exception as e:
                        error_msg = f"Wake word detection error: {e}"
                        if self.logger:
                            self.logger.error(error_msg)
                        time.sleep(0.5)
                
        except KeyboardInterrupt:
            self.speak("Shutting down. Goodbye!")
            print("\n👋 JARVIS shutdown complete")
            if self.logger:
                self.logger.info("JARVIS shutdown by user")
        except Exception as e:
            error_msg = f"Fatal error: {e}"
            print(f"❌ {error_msg}")
            if self.logger:
                self.logger.critical(error_msg, exc_info=True)

if __name__ == "__main__":
    try:
        print("🚀 Starting JARVIS Voice Assistant...")
        print("📋 Loading configuration...")
        
        # Create default config file if it doesn't exist
        if not os.path.exists("config.json"):
            default_config = {
                "wake_word": "jarvis",
                "search_delay": 1.0,
                "command_timeout": 3,
                "ai_timeout": 8,
                "screenshot_dir": "screenshots",
                "log_file": "jarvis.log",
                "hotkey": "ctrl+alt+j",
                "wake_word_threshold": 0.7,
                "command_similarity_threshold": 0.6,
                "ai_model": "deepseek/deepseek-r1:free",
                "ai_temperature": 0.7,
                "ai_max_tokens": 200
            }
            with open("config.json", "w") as f:
                json.dump(default_config, f, indent=2)
            print("📄 Created default config.json file")
        
        assistant = VoiceAssistant()
        assistant.run()
    except Exception as e:
        print(f"❌ Initialization error: {e}")
