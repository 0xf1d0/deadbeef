import yt_dlp, asyncio, re, json, os, csv, functools
from discord import PCMVolumeTransformer, FFmpegPCMAudio, Object, Guild, Role, Message, TextChannel


CYBER = Object(1289169690895323167, type=Guild)
ROLE_FI = Object(1289241716985040960, type=Role)
ROLE_FA = Object(1289241666871627777, type=Role)
ROLE_GUEST = Object(1291510062753517649, type=Role)
WELCOME_MESSAGE = Object(1314385676107645010, type=Message)
WELCOME_CHANNEL = Object(1291494038427537559, type=TextChannel)
CALENDAR_CHANNEL = Object(1293319532361809986, type=TextChannel)

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

FI = read_csv('assets/cyber_sante.csv')
FA = read_csv('assets/cyber.csv')


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
    'geo_bypass': True,
    'geo_bypass_country': 'US',
    'geo_bypass_ip_block': '0.0.0.0/0',
    'impersonate': yt_dlp.ImpersonateTarget(client='chrome', version='110', os='windows', os_version='10'),
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)
        
def restrict_channel(channel_id):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, interaction, *args, **kwargs):
            if interaction.channel.id != channel_id:
                await interaction.response.send_message(f"Cette commande ne peut être utilisée que dans le salon <#{channel_id}>.", ephemeral=True)
                return
            return await func(self, interaction, *args, **kwargs)
        return wrapper
    return decorator


class YTDLSource(PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.filepath = data.get('filepath')

    @staticmethod
    def is_url_supported(url):
        extractors = yt_dlp.gen_extractors()
        for extractor in extractors:
            if extractor.suitable(url) and extractor.IE_NAME != 'generic':
                return True
        return False

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False, timestamp=0, stop=None):
        if re.match(r'^https?', url) and not YTDLSource.is_url_supported(url):
            raise yt_dlp.utils.UnsupportedError(url)

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
    def __init__(self, source, *, volume=0.5):
        super().__init__(source, volume)
        
    @classmethod
    def from_path(cls, path, *, start=0, stop=None):
        ffmpeg_options = {
            'options': f'-vn -ss {start}'
        }

        if stop:
            ffmpeg_options['options'] += f' -to {stop}'

        return cls(FFmpegPCMAudio(path, **ffmpeg_options))


class ConfigManager:
    path = 'config.json'
    config = {}

    @classmethod
    def load(cls):
        if os.path.exists(cls.path):
            with open(cls.path, 'r', encoding='utf-8') as f:
                cls.config = json.load(f)

    @classmethod
    def get(cls, key, default=None):
        return cls.config.get(key, default)

    @classmethod
    def set(cls, key, value):
        cls.config[key] = value
        cls.save()

    @classmethod
    def append(cls, key, value):
        if key in cls.config and isinstance(cls.config[key], list):
            cls.config[key].append(value)
        else:
            cls.config[key] = [value]
        cls.save()

    @classmethod
    def remove(cls, key):
        if key in cls.config:
            del cls.config[key]
            cls.save()

    @classmethod
    def save(cls):
        with open(cls.path, 'w', encoding='utf-8') as f:
            json.dump(cls.config, f, indent=4)
