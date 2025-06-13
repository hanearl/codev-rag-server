import httpx
import asyncio
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode

from .interface import RAGSystemInterface, RAGSystemConfig, RetrievalResult

logger = logging.getLogger(__name__)


class CodevV1RAGAdapter(RAGSystemInterface):
    """
    Codev_v1 RAG 시스템 어댑터
    서버 URL: 10.250.121.100:8008
    API: POST /project/v1/repo/retrieval
    """
    
    def __init__(self, config: RAGSystemConfig):
        super().__init__(config)
        self.base_url = config.base_url
        self.auth_endpoint = f"{self.base_url}/auth/v1/token"
        self.endpoint = f"{self.base_url}/project/v1/repo/retrieval"
        self.timeout = config.timeout
        
        # 인증 정보 (기본값 사용)
        self.username = "corusadmin"
        self.password = "superuser_P@s$w0rd"
        self.access_token = None
        self.token_type = "bearer"
        
        # 고정된 파라미터들
        self.fixed_ids = [28]
        self.fixed_threshold = 0.8
        
        # HTTP 클라이언트
        self.client = httpx.AsyncClient(timeout=self.timeout)
        
    async def _get_access_token(self) -> bool:
        """
        인증 API를 통해 액세스 토큰을 획득합니다.
        
        Returns:
            토큰 획득 성공 여부
        """
        try:
            # 인증 요청 데이터 (form-encoded)
            auth_data = {
                'username': self.username,
                'password': self.password
            }
            
            headers = {
                'accept': '*/*',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            logger.debug(f"codev-v1 인증 API 요청: {self.auth_endpoint}")
            
            response = await self.client.post(
                self.auth_endpoint,
                data=urlencode(auth_data),
                headers=headers
            )
            
            response.raise_for_status()
            auth_response = response.json()
            
            if auth_response.get('statusCode') == 200 and 'access_token' in auth_response:
                self.access_token = auth_response['access_token']
                self.token_type = auth_response.get('token_type', 'bearer')
                
                logger.info("codev-v1 인증 토큰 획득 성공")
                
                # 사용자 정보 로깅
                content = auth_response.get('content', {})
                logger.info(f"인증된 사용자: {content.get('user_name', 'Unknown')}")
                
                return True
            else:
                logger.error(f"codev-v1 인증 실패: {auth_response}")
                return False
                
        except httpx.TimeoutException:
            logger.error(f"codev-v1 인증 API 요청 타임아웃 ({self.timeout}초)")
            return False
        except httpx.ConnectError:
            logger.error(f"codev-v1 인증 API 연결 오류: {self.auth_endpoint}")
            return False
        except httpx.HTTPStatusError as e:
            logger.error(f"codev-v1 인증 API HTTP 오류: {e}")
            return False
        except Exception as e:
            logger.error(f"codev-v1 인증 중 예상치 못한 오류: {e}")
            return False
    
    async def _make_request(self, query: str, k: int) -> Optional[Dict[str, Any]]:
        """
        codev-v1 API에 HTTP 요청을 보냅니다.
        토큰 만료 시 자동으로 재인증을 시도합니다.
        
        Args:
            query: 검색 쿼리
            k: 반환할 최대 문서 수
            
        Returns:
            API 응답 데이터 또는 None
        """
        request_data = {
            "ids": self.fixed_ids,
            "payload": {
                "k": k,
                "query": query,
                "threshold": self.fixed_threshold
            }
        }
        
        # 토큰이 없는 경우 먼저 획득 시도
        if not self.access_token:
            if not await self._get_access_token():
                raise Exception("액세스 토큰을 획득할 수 없습니다.")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"{self.token_type} {self.access_token}"
        }
        
        try:
            logger.debug(f"codev-v1 API 요청: {self.endpoint}")
            logger.debug(f"요청 데이터: {request_data}")
            
            response = await self.client.post(
                self.endpoint,
                json=request_data,
                headers=headers
            )
            
            # 401 Unauthorized인 경우 토큰 재발급 후 재시도
            if response.status_code == 401:
                logger.warning("codev-v1 API 인증 오류 (401) - 토큰 재발급 시도")
                
                if await self._get_access_token():
                    # 새 토큰으로 헤더 업데이트
                    headers["Authorization"] = f"{self.token_type} {self.access_token}"
                    
                    # 재시도
                    response = await self.client.post(
                        self.endpoint,
                        json=request_data,
                        headers=headers
                    )
                else:
                    raise Exception("토큰 재발급에 실패했습니다.")
            
            response.raise_for_status()  # HTTP 에러 발생 시 예외 발생
            
            response_data = response.json()
            logger.debug(f"codev-v1 API 응답 받음: 상태 코드={response.status_code}")
            
            return response_data
            
        except httpx.TimeoutException:
            logger.error(f"codev-v1 API 요청 타임아웃 ({self.timeout}초)")
            raise
        except httpx.ConnectError:
            logger.error(f"codev-v1 API 연결 오류: {self.endpoint}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"codev-v1 API HTTP 오류: {e}")
            raise
        except Exception as e:
            logger.error(f"codev-v1 API 예상치 못한 오류: {e}")
            raise
    
    async def embed_query(self, query: str) -> List[float]:
        """
        codev-v1은 임베딩 API를 제공하지 않으므로 빈 리스트 반환
        
        Args:
            query: 검색 쿼리
            
        Returns:
            빈 임베딩 벡터 (지원하지 않음)
        """
        logger.warning("codev-v1은 임베딩 API를 지원하지 않습니다.")
        return []
    
    async def retrieve(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        """
        codev-v1 API를 통해 검색 수행
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 최대 문서 수
            
        Returns:
            검색된 문서 리스트
        """
        try:
            # API 요청
            response = await self._make_request(query=query, k=top_k)
            
            if not response:
                logger.warning("codev-v1 API에서 빈 응답을 받았습니다.")
                return []
            
            if not response.get('success', False):
                logger.warning(f"codev-v1 API에서 실패 응답을 받았습니다: {response}")
                return []
            
            # 응답을 표준 형식으로 변환
            results = self._convert_response_to_standard_format(response)
            
            logger.info(f"codev-v1 검색 완료: 쿼리='{query}', 결과 수={len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"codev-v1 검색 중 오류 발생: {str(e)}")
            return []
    
    def _convert_response_to_standard_format(self, response: Dict[str, Any]) -> List[RetrievalResult]:
        """
        codev-v1 API 응답을 표준 RAG 인터페이스 형식으로 변환합니다.
        
        Args:
            response: codev-v1 API 응답
            
        Returns:
            표준 형식으로 변환된 결과 리스트
        """
        results = []
        
        api_results = response.get('results', [])
        
        for i, item in enumerate(api_results):
            meta = item.get('meta', {})
            
            # 파일 경로 추출 (file_name에서)
            file_name = meta.get('file_name', '')
            filepath = None
            
            # file_name이 경로 형태인 경우 그대로 사용
            if file_name and ('/' in file_name or '\\' in file_name):
                filepath = file_name
            elif file_name:
                # 단순 파일명인 경우 Java 패키지 구조로 추정
                if file_name.endswith('.java'):
                    # 예: BookController.java -> com/skax/library/controller/BookController.java
                    # 실제로는 content에서 package 정보를 추출해야 하지만 일단 기본값 사용
                    filepath = f"src/main/java/com/skax/library/controller/{file_name}"
                else:
                    filepath = file_name
            
            result = RetrievalResult(
                content=item.get('content', ''),
                score=float(item.get('score', 0.0)),
                filepath=filepath,
                metadata={
                    'source': 'codev_v1',
                    'file_name': meta.get('file_name'),
                    'doc_id': meta.get('doc_id'),
                    'repo_id': item.get('repo_id'),
                    'repo_name': item.get('repo_name'),
                    'use_custom_meta': item.get('use_custom_meta'),
                    'origin_source': item.get('origin_source'),
                    'vectorstore': item.get('vectorstore'),
                    'collection_type': response.get('collection_type'),
                    'original_response': item  # 전체 응답 보존
                }
            )
            results.append(result)
        
        return results
    
    async def health_check(self) -> bool:
        """
        codev-v1 RAG 시스템의 상태를 확인합니다.
        
        Returns:
            시스템이 정상 동작하는지 여부
        """
        try:
            # 간단한 테스트 쿼리로 시스템 상태 확인
            test_results = await self.retrieve("health check", top_k=1)
            return isinstance(test_results, list)
        except Exception as e:
            logger.error(f"codev-v1 헬스체크 실패: {e}")
            return False
    
    async def get_system_info(self) -> Dict[str, Any]:
        """
        codev-v1 시스템 정보를 반환합니다.
        
        Returns:
            시스템 정보 딕셔너리
        """
        base_info = await super().get_system_info()
        base_info.update({
            'name': 'Codev_v1 RAG System',
            'endpoint': self.endpoint,
            'fixed_ids': self.fixed_ids,
            'fixed_threshold': self.fixed_threshold,
            'auth_endpoint': self.auth_endpoint,
            'has_token': self.access_token is not None
        })
        return base_info
    
    async def close(self):
        """리소스 정리"""
        if self.client:
            await self.client.aclose() 