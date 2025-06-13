import requests
import time
from typing import List, Dict, Any, Optional
import logging
from urllib.parse import urlencode

from ..interfaces.rag_interface import RAGInterface


class Codev_v1_RAGSystem(RAGInterface):
    """
    Codev_v1 Retrieval API와 연동하는 RAG 시스템
    서버 URL: 10.250.121.100:8008
    API: POST /project/v1/repo/retrieval
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', 'http://10.250.121.100:8008')
        self.auth_endpoint = f"{self.base_url}/auth/v1/token"
        self.endpoint = f"{self.base_url}/project/v1/repo/retrieval"
        self.default_k = config.get('k', 5)
        self.timeout = config.get('timeout', 30)
        
        # 인증 정보
        self.username = config.get('username', 'corusadmin')
        self.password = config.get('password', 'superuser_P@s$w0rd')
        self.access_token = None
        self.token_type = 'bearer'
        
        # 고정된 파라미터들
        self.fixed_ids = [28]
        self.fixed_threshold = 0.8
        
        # 로거 설정
        self.logger = logging.getLogger(__name__)
        
    def get_access_token(self) -> bool:
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
            
            self.logger.debug(f"인증 API 요청: {self.auth_endpoint}")
            
            response = requests.post(
                self.auth_endpoint,
                data=urlencode(auth_data),
                headers=headers,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            auth_response = response.json()
            
            if auth_response.get('statusCode') == 200 and 'access_token' in auth_response:
                self.access_token = auth_response['access_token']
                self.token_type = auth_response.get('token_type', 'bearer')
                
                self.logger.info("Codev_v1 인증 토큰 획득 성공")
                self.logger.debug(f"토큰 타입: {self.token_type}")
                
                # 사용자 정보 로깅
                content = auth_response.get('content', {})
                self.logger.info(f"인증된 사용자: {content.get('user_name', 'Unknown')}")
                
                return True
            else:
                self.logger.error(f"인증 실패: {auth_response}")
                return False
                
        except requests.exceptions.Timeout:
            self.logger.error(f"인증 API 요청 타임아웃 ({self.timeout}초)")
            return False
        except requests.exceptions.ConnectionError:
            self.logger.error(f"인증 API 연결 오류: {self.auth_endpoint}")
            return False
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"인증 API HTTP 오류: {e}")
            return False
        except Exception as e:
            self.logger.error(f"인증 중 예상치 못한 오류: {e}")
            return False
    
    def initialize(self) -> bool:
        """
        Codev_v1 RAG 시스템 초기화 및 상태 확인
        
        Returns:
            초기화 성공 여부
        """
        try:
            # 1. 먼저 액세스 토큰 획득
            if not self.get_access_token():
                self.logger.error("Codev_v1 RAG 시스템 초기화 실패: 토큰 획득 실패")
                return False
            
            # 2. 간단한 테스트 쿼리로 서버 연결 확인
            test_response = self._make_request(
                query="test",
                k=1
            )
            
            if test_response and test_response.get('success', False):
                self.logger.info(f"Codev_v1 RAG 시스템 초기화 성공: {self.base_url}")
                return True
            else:
                self.logger.error("Codev_v1 RAG 시스템 초기화 실패: 잘못된 응답 형식")
                return False
                
        except Exception as e:
            self.logger.error(f"Codev_v1 RAG 시스템 초기화 실패: {str(e)}")
            return False
    
    def retrieve(self, query: str, top_k: int = 10, **kwargs) -> List[Dict[str, Any]]:
        """
        Codev_v1 API를 통해 검색 수행
        
        Args:
            query: 검색 쿼리
            top_k: 반환할 최대 문서 수 (k 파라미터로 사용)
            **kwargs: 추가 파라미터 (현재는 사용되지 않음)
            
        Returns:
            검색된 문서 리스트
        """
        try:
            # API 요청
            response = self._make_request(
                query=query,
                k=top_k
            )
            
            if not response:
                self.logger.warning("Codev_v1 API에서 빈 응답을 받았습니다.")
                return []
            
            if not response.get('success', False):
                self.logger.warning(f"Codev_v1 API에서 실패 응답을 받았습니다: {response}")
                return []
            
            # 응답을 표준 형식으로 변환
            results = self._convert_response_to_standard_format(response)
            
            self.logger.info(f"Codev_v1 검색 완료: 쿼리='{query}', 결과 수={len(results)}")
            return results
            
        except Exception as e:
            self.logger.error(f"Codev_v1 검색 중 오류 발생: {str(e)}")
            return []
    
    def _make_request(self, query: str, k: int) -> Optional[Dict[str, Any]]:
        """
        Codev_v1 API에 HTTP 요청을 보냅니다.
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
            if not self.get_access_token():
                raise Exception("액세스 토큰을 획득할 수 없습니다.")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"{self.token_type} {self.access_token}"
        }
        
        try:
            self.logger.debug(f"Codev_v1 API 요청: {self.endpoint}")
            self.logger.debug(f"요청 데이터: {request_data}")
            
            response = requests.post(
                self.endpoint,
                json=request_data,
                headers=headers,
                timeout=self.timeout
            )
            
            # 401 Unauthorized인 경우 토큰 재발급 후 재시도
            if response.status_code == 401:
                self.logger.warning("Codev_v1 API 인증 오류 (401) - 토큰 재발급 시도")
                
                if self.get_access_token():
                    # 새 토큰으로 헤더 업데이트
                    headers["Authorization"] = f"{self.token_type} {self.access_token}"
                    
                    # 재시도
                    response = requests.post(
                        self.endpoint,
                        json=request_data,
                        headers=headers,
                        timeout=self.timeout
                    )
                else:
                    raise Exception("토큰 재발급에 실패했습니다.")
            
            response.raise_for_status()  # HTTP 에러 발생 시 예외 발생
            
            response_data = response.json()
            self.logger.debug(f"API 응답 받음: 상태 코드={response.status_code}")
            
            return response_data
            
        except requests.exceptions.Timeout:
            self.logger.error(f"Codev_v1 API 요청 타임아웃 ({self.timeout}초)")
            raise
        except requests.exceptions.ConnectionError:
            self.logger.error(f"Codev_v1 API 연결 오류: {self.endpoint}")
            raise
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"Codev_v1 API HTTP 오류: {e}")
            raise
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Codev_v1 API 요청 오류: {e}")
            raise
        except Exception as e:
            self.logger.error(f"예상치 못한 오류: {e}")
            raise
    
    def _convert_response_to_standard_format(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Codev_v1 API 응답을 표준 RAG 인터페이스 형식으로 변환합니다.
        
        Args:
            response: Codev_v1 API 응답
            
        Returns:
            표준 형식으로 변환된 결과 리스트
        """
        results = []
        
        api_results = response.get('results', [])
        
        for i, item in enumerate(api_results):
            meta = item.get('meta', {})
            
            standard_item = {
                'id': str(meta.get('doc_id', f"codev_v1_doc_{i}")),
                'content': item.get('content', ''),
                'score': item.get('score', 0.0),
                'metadata': {
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
            }
            results.append(standard_item)
        
        return results
    
    def health_check(self) -> bool:
        """
        Codev_v1 RAG 시스템의 상태를 확인합니다.
        
        Returns:
            시스템이 정상 동작하는지 여부
        """
        try:
            # 간단한 테스트 쿼리로 시스템 상태 확인
            test_results = self.retrieve("health check", top_k=1)
            return isinstance(test_results, list)
        except Exception:
            return False
    
    def get_api_info(self) -> Dict[str, Any]:
        """
        Codev_v1 API 정보를 반환합니다.
        
        Returns:
            API 정보 딕셔너리
        """
        return {
            'name': 'Codev_v1 RAG System',
            'base_url': self.base_url,
            'endpoint': self.endpoint,
            'fixed_ids': self.fixed_ids,
            'fixed_threshold': self.fixed_threshold,
            'default_k': self.default_k,
            'timeout': self.timeout
        } 