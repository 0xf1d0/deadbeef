import yt_dlp, asyncio, re, json, os, csv
from discord import PCMVolumeTransformer, FFmpegPCMAudio, Object, Guild, Role


CYBER = Object(1289169690895323167, Guild)
ROLE_FI = Object(1289241716985040960, Role)
ROLE_FA = Object(1289241666871627777, Role)
ROLE_GUEST = Object(1291510062753517649, Role)


yt_dlp.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'quiet': True,
    'restrictfilenames': True,
    'no_warnings': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'logtostderr': False,
    'impersonate': yt_dlp.ImpersonateTarget(client='chrome', version='110', os='windows', os_version='10'),
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

def read_csv(file_path):
    """
    @brief Reads a CSV file and returns a list of rows.
    @param file_path The path to the CSV file.
    @return List of rows, where each row is a list of values.
    """
    data = []
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip the header row
        for row in reader:
            data.append(row)
    return data


class YTDLSource(PCMVolumeTransformer):
    """
    @brief A class to handle audio source from YouTube using youtube-dl and FFmpeg.
    This class inherits from PCMVolumeTransformer and is used to create an audio source
    from a YouTube URL. It supports streaming and downloading of audio, as well as 
    specifying start and stop times for the audio.
    """

    def __init__(self, source, *, data, volume=0.5):
        """
        Initializes the object with the given source, data, and optional volume.
        @param source: The source of the object.
        @param data: A dictionary containing metadata such as title, url, and filepath.
        @param volume: The volume level, default is 0.5.
        """

        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.filepath = data.get('filepath')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False, timestamp=0, stop=None):
        """
        Asynchronously creates an instance from a given URL.
        @param cls: The class itself.
        @param url: The URL to extract information from.
        @param loop: (Optional) The event loop to use. If not provided, the default event loop is used.
        @param stream: (Optional) If True, the audio will be streamed. Defaults to False.
        @param timestamp: (Optional) The starting timestamp for the audio. Defaults to 0.
        @param stop: (Optional) The stopping timestamp for the audio. If not provided, the audio will play until the end.
        @return: A tuple containing an instance of the class and the filename.
        """

        loop = loop or asyncio.get_event_loop()
        match = re.search(r'[&?]t=(\d+)', url)
        if not timestamp and match:
            timestamp = int(match.group(1))

        ffmpeg_options = {
            'options': f'-vn -ss {timestamp}' + (f' -to {stop}' if stop else ''),
        }


        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)

        return cls(FFmpegPCMAudio(filename, **ffmpeg_options), data=data), filename
    

class LocalSource(PCMVolumeTransformer):
    """
    @brief A class to handle local audio sources with volume transformation.
    This class extends PCMVolumeTransformer to provide functionality for handling
    local audio files with adjustable volume.
    """

    def __init__(self, source, *, volume=0.5):
        """
        @brief Initializes the object with the given source and volume.
        @param source The source to be used for initialization.
        @param volume The volume level to be set. Default is 0.5.
        """

        super().__init__(source, volume)
        
    @classmethod
    def from_path(cls, path, *, start=0, stop=None):
        """
        Create an instance of the class from a given file path with optional start and stop times.
        @param cls: The class itself.
        @param path: The file path to the audio file.
        @param start: The start time in seconds (default is 0).
        @param stop: The stop time in seconds (default is None, which means play until the end).
        @return: An instance of the class with the specified audio file and options.
        """

        ffmpeg_options = {
            'options': f'-vn -ss {start}'
        }

        if stop:
            ffmpeg_options['options'] += f' -to {stop}'

        return cls(FFmpegPCMAudio(path, **ffmpeg_options))


class ConfigManager:
    """
    @class ConfigManager
    @brief Manages configuration settings stored in a JSON file.
    This class provides methods to read, write, append, and remove configuration
    settings from a JSON file. It ensures that the configuration file is updated
    whenever changes are made.
    """

    def __init__(self, path='config.json'):
        """
        Initializes the configuration object.
        @param path: The path to the configuration file. Defaults to 'config.json'.
        @type path: str
        @var path: Stores the path to the configuration file.
        @var config: A dictionary to store the configuration data. If the file exists, it loads the data from the file.
        """

        self.path = path
        self.config = {}
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)

    def get(self, key, default=None):
        """
        @brief Retrieves the value for a given key from the configuration.
        @param key The key to look up in the configuration.
        @param default The default value to return if the key is not found. Defaults to None.
        @return The value associated with the key if it exists, otherwise the default value.
        """

        return self.config.get(key, default)
    
    def set(self, key, value):
        """
        @brief Sets a configuration key to a specified value and updates the configuration file.
        @param key The configuration key to set.
        @param value The value to assign to the configuration key.
        This method updates the in-memory configuration dictionary with the provided key-value pair
        and writes the updated configuration back to the file specified by self.path in JSON format.
        """

        self.config[key] = value
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4)

    def append(self, key, value):
        """
        @brief Appends a value to a list associated with a key in the configuration.
        If the key exists in the configuration and its value is a list, the value is appended to the list.
        Otherwise, a new list is created with the value as its first element.
        The updated configuration is then written back to the file.
        @param key The key in the configuration dictionary.
        @param value The value to append to the list associated with the key.
        """

        if key in self.config and isinstance(self.config[key], list):
            self.config[key].append(value)
        else:
            self.config[key] = [value]
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4)
    
    def remove(self, key):
        """
        @brief Removes a key from the configuration and updates the configuration file.
        @param key The key to be removed from the configuration.
        This method deletes the specified key from the configuration dictionary and writes the updated configuration back to the file specified by self.path.
        """

        if key in self.config:
            del self.config[key]
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
