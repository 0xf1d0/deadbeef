import functools, aiohttp, re

from utils import ConfigManager


class API:
    def __init__(self, url: str, session: aiohttp.ClientSession):
        self.url = url
        self.session = session

    @staticmethod
    def endpoint(route: str, *, method: str = 'get'):
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(self, *args, **kwargs):
                async with getattr(self.session, method)(self.url + route + '/'.join(args), json=kwargs) as response:
                    self.data = await response.json()
                    self.status = response.status
                    return func(self, *args, **kwargs)
            return wrapper
        return decorator


class MistralAI(API):
    def __init__(self):
        super().__init__('https://api.mistral.ai', aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=10),
            headers={
                "Authorization": f"Bearer {ConfigManager.get('mistral_key')}",
                "Accept-Encoding": "gzip",
                "Content-Type": "application/json"
            }
        ))

    @API.endpoint('/chat/completions', method='post')
    def ask(self, **kwargs):
        if self.status == 200:
            r = self.data['choices'][0]['message']['content']
            r = re.sub(r'<@&?\d+>|@everyone|@here', 'X', r)
            
            return r
        elif self.status == 422:
            raise Exception(self.data['detail'][-1]['msg'])
        else:
            raise Exception("Sorry, I couldn't generate a response at this time.")
        

class RootMe(API):
    def __init__(self):
        super().__init__('https://api.root-me.org', aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=10),
            headers={
                "Accept-Encoding": "gzip",
                "Content-Type": "application/json"
            },
            cookies={'api_key': ConfigManager.get('rootme_key')}
        ))

    @API.endpoint('/challenges')
    def get_challenges(self, *args, **kwargs):
        if self.status == 200:
            return self.data
        else:
            raise Exception("Impossible de trouver des informations sur ce challenge.")
    
    @API.endpoint('/auteurs')
    def get_authors(self, *args, **kwargs):
        if self.status == 200:
            return self.data
        else:
            raise Exception("Impossible de trouver des informations sur cet utilisateur.")
    
    @API.endpoint('/classement')
    def leaderboard(self, *, debut_classement: str):
        if self.status == 200:
            return self.data
        else:
            raise Exception("Impossible de trouver des informations sur le classement.")
    
    @API.endpoint('/environnements_virtuels')
    def virtual_environments(self, *args, **kwargs):
        if self.status == 200:
            return self.data
        else:
            raise Exception("Impossible de trouver des informations sur le environnements virtuels.")
