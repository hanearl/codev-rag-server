#!/usr/bin/env python3

import json
import os

# JSON 파일에서 코드 추출 및 Java 파일 생성
json_files = [
    '../data/analysis_results/docs/controller/BookController.json',
    '../data/analysis_results/docs/dto/BookDto.json',
    '../data/analysis_results/docs/model/Book.json',
    '../data/analysis_results/docs/impl/BookServiceImpl.json',
    '../data/analysis_results/docs/controller/MemberController.json',
    '../data/analysis_results/docs/dto/MemberDto.json'
]

os.makedirs('temp_test_files', exist_ok=True)

for json_file in json_files:
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'code' in data and data['code']:
            # 파일명 추출
            base_name = os.path.basename(json_file).replace('.json', '.java')
            java_file_path = f'temp_test_files/{base_name}'
            
            # Java 코드 파일 생성
            with open(java_file_path, 'w', encoding='utf-8') as f:
                f.write(data['code'])
            
            print(f'Generated: {java_file_path}')
        else:
            print(f'No code found in: {json_file}')
    except Exception as e:
        print(f'Error processing {json_file}: {e}')

print(f'\nGenerated files:')
os.system('ls -la temp_test_files/') 