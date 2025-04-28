import aiohttp, asyncio, logging, time, re
from typing import ClassVar, Optional, Dict, Any, Tuple, List, TypeVar, Type
from functools import wraps

from utils import ConfigManager

T = TypeVar('T', bound='API')
ResponseType = Tuple[Any, int]

class API:
    # Base configuration
    url: ClassVar[str] = ""
    headers: ClassVar[Dict[str, str]] = {}
    cookies: ClassVar[Dict[str, str]] = {}
    
    # Session management
    _session: ClassVar[Optional[aiohttp.ClientSession]] = None
    _lock: ClassVar[asyncio.Lock] = asyncio.Lock()
    _last_used: ClassVar[float] = 0
    _session_ttl: ClassVar[float] = 300  # 5 minutes
    
    # Error handling and retry configuration
    _max_retries: ClassVar[int] = 3
    _retry_delay: ClassVar[float] = 1.0
    _timeout: ClassVar[aiohttp.ClientTimeout] = aiohttp.ClientTimeout(total=30)
    _logger: ClassVar[logging.Logger] = logging.getLogger("API")

    @classmethod
    def configure(cls: Type[T], *, 
                url: Optional[str] = None,
                headers: Optional[Dict[str, str]] = None, 
                cookies: Optional[Dict[str, str]] = None,
                session_ttl: Optional[float] = None,
                max_retries: Optional[int] = None,
                retry_delay: Optional[float] = None,
                timeout: Optional[float] = None) -> Type[T]:
        """Configure API parameters."""
        if url is not None:
            cls.url = url.rstrip('/')
        if headers is not None:
            cls.headers = headers
        if cookies is not None:
            cls.cookies = cookies
        if session_ttl is not None:
            cls._session_ttl = session_ttl
        if max_retries is not None:
            cls._max_retries = max_retries
        if retry_delay is not None:
            cls._retry_delay = retry_delay
        if timeout is not None:
            cls._timeout = aiohttp.ClientTimeout(total=timeout)
        return cls

    @classmethod
    async def _ensure_session(cls: Type[T]) -> None:
        """Ensure an active session exists or create a new one."""
        current_time = time.time()
        
        # If the session exists but is expired, close it
        if (cls._session and not cls._session.closed and 
            current_time - cls._last_used > cls._session_ttl):
            cls._logger.debug("Session expired, closing...")
            await cls.close()
        
        # If no session or session is closed, create a new one
        if cls._session is None or cls._session.closed:
            async with cls._lock:
                if cls._session is None or cls._session.closed:
                    cls._logger.debug("Creating a new session...")
                    cls._session = aiohttp.ClientSession(
                        connector=aiohttp.TCPConnector(limit=10, ssl=False),
                        headers=cls.headers,
                        cookies=cls.cookies,
                        timeout=cls._timeout
                    )
        
        cls._last_used = current_time

    @classmethod
    async def close(cls: Type[T]) -> None:
        """Close the HTTP session if it exists."""
        if cls._session and not cls._session.closed:
            await cls._session.close()
            cls._session = None
            cls._logger.debug("Session closed")

    @classmethod
    async def _request(cls: Type[T], method: str, route: str, 
                      *args, retry_count: int = 0, **kwargs) -> ResponseType:
        """Execute an HTTP request with error handling and retries."""
        await cls._ensure_session()
        url = f"{cls.url}/{route.strip('/')}"
        if args:
            url = f"{url}/{'/'.join(str(arg) for arg in args)}"
        
        cls._logger.debug(f"Sending {method} to {url}")
        
        try:
            async with cls._session.request(method, url, **kwargs) as response:
                cls._last_used = time.time()
                
                # Handle rate limiting and server errors with retries
                if response.status in {429, 500, 502, 503, 504} and retry_count < cls._max_retries:
                    retry_after = int(response.headers.get('Retry-After', cls._retry_delay))
                    cls._logger.warning(
                        f"Error {response.status}, retrying in {retry_after}s "
                        f"({retry_count + 1}/{cls._max_retries})"
                    )
                    await asyncio.sleep(retry_after)
                    return await cls._request(method, route, *args, retry_count=retry_count + 1, **kwargs)
                
                try:
                    data = await response.json()
                except aiohttp.ContentTypeError:
                    # Fallback if the response is not JSON
                    data = await response.text()
                
                return data, response.status
                
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            cls._logger.error(f"Connection error: {str(e)}")
            
            # Retry with exponential backoff
            if retry_count < cls._max_retries:
                # Reset the session in case of an error
                await cls.close()
                await asyncio.sleep(cls._retry_delay * (2 ** retry_count))
                return await cls._request(method, route, *args, retry_count=retry_count + 1, **kwargs)
            
            raise ConnectionError(f"Connection failed after {cls._max_retries} attempts: {str(e)}") from e

    @classmethod
    async def __aenter__(cls: Type[T]) -> Type[T]:
        """Class context manager for use with 'async with'."""
        await cls._ensure_session()
        return cls

    @classmethod
    async def __aexit__(cls: Type[T], *exc_details) -> None:
        """Close the session when exiting the context manager."""
        await cls.close()

    @staticmethod
    def endpoint(route: str, method: str = 'GET') -> callable:
        """Decorator to easily create API endpoints."""
        def decorator(func: callable):
            @wraps(func)
            def wrapped(cls, data, status, *args, **kwargs):
                return func(cls, data, status, *args, **kwargs)
            
            async def wrapper(cls: Type[T], *args, **kwargs) -> Any:
                # Extract request-specific parameters
                request_kwargs = {}
                request_keys = {'params', 'json', 'data', 'headers', 'cookies', 'allow_redirects'}
                
                for key in list(kwargs.keys()):
                    if key in request_keys:
                        request_kwargs[key] = kwargs.pop(key)
                
                # If 'json' not in request_kwargs but there are kwargs, use them as json for appropriate methods
                if 'json' not in request_kwargs and kwargs and method in {'POST', 'PUT', 'PATCH'}:
                    request_kwargs['json'] = kwargs
                    kwargs = {}  # Clear kwargs to avoid duplicates
                
                data, status = await cls._request(method, route, *args, **request_kwargs)
                return wrapped(cls, data, status, *args, **kwargs)
            
            return classmethod(wrapper)
        return decorator


class MistralAI(API):
    url = 'https://api.mistral.ai'
    headers = {
        "Authorization": f"Bearer {ConfigManager.get('mistral_key')}",
    }

    @API.endpoint('/v1/chat/completions', method='POST')
    def chat_completion(cls, data, status, **kwargs):
        if status == 200:
            content = data['choices'][0]['message']['content']
            return re.sub(r'<@&?\d+>|@everyone|@here', 'X', content)
        elif status == 422:
            raise ValueError(data['detail'][-1]['msg'])
        else:
            raise RuntimeError(f"API Error {status}: {data.get('message', 'Unknown error')}")


class RootMe(API):
    url = 'https://api.www.root-me.org'
    
    @classmethod
    def setup(cls, api_key: str = None):
        """Configure the RootMe API with an API key."""
        if api_key:
            cls.cookies = {'api_key': api_key}
        else:
            # If no API key provided, check configuration
            from utils import ConfigManager
            cls.cookies = {'api_key': ConfigManager.get('rootme_key')}
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return cls

    @API.endpoint('/challenges')
    def get_challenges(cls, data, status, **kwargs):
        """
        Get challenges data with optional filtering.
        
        Parameters:
        - titre: Filter by title
        - soustitre: Filter by subtitle
        - lang: Filter by language
        - score: Filter by score
        - id_auteur[]: List of author IDs
        """
        if status != 200:
            raise Exception(f"Failed to fetch challenges: Status {status}")
        return data

    @API.endpoint('/challenges/{id_challenge}')
    def get_challenge(cls, data, status, id_challenge, **kwargs):
        """
        Get details for a specific challenge by ID.
        
        Parameters:
        - id_challenge: The challenge ID
        """
        if status != 200:
            raise Exception(f"Failed to fetch challenge {id_challenge}: Status {status}")
        return data

    @API.endpoint('/auteurs')
    def get_authors(cls, data, status, **kwargs):
        """
        Get authors data with optional filtering.
        
        Parameters:
        - nom: Filter by name
        - statut: Filter by status
        - lang: Filter by language
        """
        if status != 200:
            raise Exception(f"Failed to fetch authors: Status {status}")
        return data

    @API.endpoint('/auteurs')
    def get_author(cls, data, status, *, id_author, **kwargs):
        """
        Get details for a specific author by ID.
        
        Parameters:
        - id_author: The author ID
        """
        if status != 200:
            raise Exception(f"Failed to fetch author {id_author}: Status {status}")
        return data

    @API.endpoint('/classement')
    def get_leaderboard(cls, data, status, **kwargs):
        """
        Get leaderboard data.
        
        Parameters:
        - debut_classement: Starting position for pagination
        """
        if status != 200:
            raise Exception(f"Failed to fetch leaderboard: Status {status}")
        return data

    @API.endpoint('/environnements_virtuels')
    def get_virtual_environments(cls, data, status, **kwargs):
        """
        Get virtual environments data with optional filtering.
        
        Parameters:
        - nom: Filter by name
        - os: Filter by operating system
        """
        if status != 200:
            raise Exception(f"Failed to fetch virtual environments: Status {status}")
        return data

    @API.endpoint('/environnements_virtuels/{id_env}')
    def get_virtual_environment(cls, data, status, id_env, **kwargs):
        """
        Get details for a specific virtual environment by ID.
        
        Parameters:
        - id_env: The environment ID
        """
        if status != 200:
            raise Exception(f"Failed to fetch virtual environment {id_env}: Status {status}")
        return data
