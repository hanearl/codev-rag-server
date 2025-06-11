#!/usr/bin/env python3
"""
실제 analysis_results JSON 파일들로 배치 인덱싱 테스트
"""

import json
import requests
import os
from pathlib import Path

def load_analysis_file(file_path):
    """분석 결과 JSON 파일 로드"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_batch_request(analysis_files):
    """배치 인덱싱 요청 생성"""
    return {
        "analysis_data_list": analysis_files,
        "force_update": False
    }

def test_batch_indexing():
    """배치 인덱싱 테스트"""
    
    # 분석 결과 파일들 로드
    base_path = Path("data/analysis_results/docs/controller")
    json_files = [
        "BookController.json",
        "MemberController.json", 
        "CategoryController.json"
    ]
    
    analysis_data_list = []
    
    for file_name in json_files:
        file_path = base_path / file_name
        if file_path.exists():
            print(f"📂 로딩: {file_name}")
            data = load_analysis_file(file_path)
            analysis_data_list.append(data)
        else:
            print(f"❌ 파일 없음: {file_path}")
    
    if not analysis_data_list:
        print("❌ 인덱싱할 파일이 없습니다.")
        return
    
    # 배치 요청 생성
    batch_request = create_batch_request(analysis_data_list)
    
    print(f"\n🚀 배치 인덱싱 시작: {len(analysis_data_list)}개 파일")
    
    # API 호출
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/indexing/json/batch",
            json=batch_request,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            print("✅ 배치 인덱싱 성공!")
            print(f"   총 처리된 파일: {result['total_files']}")
            print(f"   총 생성된 청크: {result['total_chunks']}")
            
            # 각 파일별 결과 출력
            for file_result in result.get('results', []):
                print(f"   📄 {file_result['file_path']}: {file_result['chunks_count']}개 청크")
        else:
            print(f"❌ 배치 인덱싱 실패: {response.status_code}")
            print(f"   오류: {response.text}")
            
    except Exception as e:
        print(f"❌ 요청 실패: {e}")

if __name__ == "__main__":
    test_batch_indexing() 