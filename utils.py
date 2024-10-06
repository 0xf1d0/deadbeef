import yt_dlp
import asyncio
import re
import json
import os
from discord import PCMVolumeTransformer, FFmpegPCMAudio


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


class YTDLSource(PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.filepath = data.get('filepath')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False, timestamp=0, stop=None):
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
    def __init__(self, path='config.json'):
        self.path = path
        self.config = {}
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)

    def get(self, key, default=None):
        return self.config.get(key, default)
    
    def set(self, key, value):
        self.config[key] = value
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4)

    def append(self, key, value):
        if key in self.config and isinstance(self.config[key], list):
            self.config[key].append(value)
        else:
            self.config[key] = [value]
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4)
    
    def remove(self, key):
        if key in self.config:
            del self.config[key]
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
