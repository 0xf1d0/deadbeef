import aiohttp, re, asyncio
from typing import Optional, Callable, Any
from functools import wraps

from utils import ConfigManager


class API:
    def __init__(self, url: str, headers: dict = {}, cookies: dict = {}):
        self.url = url.rstrip('/')
        self.headers = headers
        self.cookies = cookies
        self._session: Optional[aiohttp.ClientSession] = None
        self._lock = asyncio.Lock()
        self.data: Any = None
        self.status: int = 0
        
    async def __aenter__(self):
        await self._ensure_session()
        return self
    
    async def __aexit__(self, ex_type, exc, tb):
        await self.close()
        
    async def _ensure_session(self):
        if self._session is None or self._session.closed:
            async with self._lock:
                if self._session is None or self._session.closed:
                    self._session = aiohttp.ClientSession(
                        connector=aiohttp.TCPConnector(limit=10),
                        headers=self.headers,
                        cookies=self.cookies
                    )
        
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
            
    async def _request(self, method: str, route: str, *args, **kwargs):
        await self._ensure_session()
        url = f"{self.url}/{route.strip('/')}{'/'.join(args)}"
        print(url, kwargs)
        
        try:
            async with self._session.request(method, url, json=kwargs) as response:
                self.data = await response.json()
                self.status = response.status
                return self.data, self.status
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            await self.close()
            raise ConnectionError(f"Session expired: {str(e)}") from e

    @staticmethod
    def endpoint(route: str, method: str = 'GET') -> Callable:
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(self, *args, **kwargs):
                await self._request(method, route, *args, **kwargs)
                return func(self, *args, **kwargs)
            return wrapper
        return decorator


class MistralAI(API):
    def __init__(self):
        super().__init__(
            url='https://api.mistral.ai',
            headers={
                "Authorization": f"Bearer {ConfigManager.get('mistral_key')}",
                "Accept-Encoding": "gzip",
                "Content-Type": "application/json"
            }
        )

    @API.endpoint('/chat/completions', method='POST')
    def ask(self, **kwargs):
        if self.status == 200:
            content = self.data['choices'][0]['message']['content']
            return re.sub(r'<@&?\d+>|@everyone|@here', 'X', content)
        elif self.status == 422:
            raise ValueError(self.data['detail'][-1]['msg'])
        else:
            raise RuntimeError(f"API Error {self.status}: {self.data.get('message', 'Unknown error')}")


class RootMe(API):
    def __init__(self):
        super().__init__(
            url='https://api.root-me.org', 
            headers={
                "Accept-Encoding": "gzip",
                "Content-Type": "application/json"
            },
            cookies={'api_key': ConfigManager.get('rootme_key')}
        )

    @API.endpoint('/challenges')
    def get_challenges(self, *args, **kwargs):
        if self.status == 200:
            return self.data
        raise Exception("Impossible de trouver des informations sur ce challenge.")
    
    @API.endpoint('/auteurs')
    def get_authors(self, *args, **kwargs):
        if self.status == 200:
            return self.data
        raise Exception("Impossible de trouver des informations sur cet utilisateur.")
    
    @API.endpoint('/classement')
    def leaderboard(self, *, debut_classement: str):
        if self.status == 200:
            return self.data
        raise Exception("Impossible de trouver des informations sur le classement.")
    
    @API.endpoint('/environnements_virtuels')
    def virtual_environments(self, *args, **kwargs):
        if self.status == 200:
            return self.data
        raise Exception("Impossible de trouver des informations sur le environnements virtuels.")
