
# 📌 코드 어시스턴트: 코드 간 연관성 검색 한계 및 개선 방안

---

## 1. ⚠️ 현재 구조의 한계점

현재 LlamaIndex + LangChain 기반 코드 어시스턴트는 **개별 파일/메서드 단위 chunk**를 기반으로 벡터 인덱스를 생성하고 검색한다. 그러나 다음과 같은 한계가 존재한다:

### ✅ 예시 시나리오
```text
UserService.java 에서 UserDto 를 import 해서 사용
→ 사용자는 "UserService의 사용자 등록 로직에서 어떤 DTO를 사용하는가?" 라고 질문
→ 하지만 검색 결과에는 UserDto.java 내용이 포함되지 않음
```

### ❗ 주요 한계

| 항목 | 설명 |
|------|------|
| **코드 간 연결 정보 미반영** | `import`, `extends`, `@Autowired` 등으로 연결된 클래스 정보가 검색에 반영되지 않음 |
| **DTO, Util 클래스 정보 누락** | 서비스 클래스 내에서 참조되는 DTO/Util의 내부 필드나 주석 내용 검색 불가 |
| **LLM 추론 과부하** | LLM이 문맥 없이 불완전한 chunk만 보고 답변해야 하므로 정확도 저하 |
| **유사 코드 추천 기능 약화** | 실제로 연관된 파일끼리 묶이지 않으면 비슷한 코드 검색 기능이 약화됨 |

---

## 2. 🔧 개선해야 할 구조적 변경점

### ✅ 목표
> **"코드 상의 논리적 연결 관계까지 고려한 RAG 검색 체계" 구현**

---

### 🧩 개선 방안 1: `import`, `extends` 기반 메타데이터 강화

- AST 파싱 시 각 파일의 `import`, `extends`, `implements`, `annotation` 등을 추출하여 `metadata`에 저장
- 예시:

```python
Document(
    text="public class UserService { ... }",
    metadata={
        "file": "UserService.java",
        "imports": ["UserDto", "ValidationUtil"],
        "extends": ["BaseService"]
    }
)
```

- 검색 시 쿼리 + 연관 클래스 이름을 확장하여 **더 많은 관련 문서 검색**

---

### 🧩 개선 방안 2: 하이브리드 리트리버 개선 (연관 문서 검색 확장)

- LlamaIndex의 `Retriever`를 커스터마이징하여:
  1. 쿼리에서 검색된 문서의 `imports` 항목 추출
  2. 해당 class명을 포함하는 다른 문서도 함께 검색

```python
def expand_query_with_imports(query, top_docs):
    related_classes = []
    for d in top_docs:
        related_classes += d.metadata.get("imports", [])
    return query + " " + " ".join(set(related_classes))
```

---

### 🧩 개선 방안 3: `ComposableGraph` 활용한 계층적 문서 구조

- LlamaIndex의 `ComposableGraph`를 활용해 연관 문서를 상하위 노드로 구성
- 예시:

```text
UserService.java
 └─ uses → UserDto.java
           └─ uses → UserRole Enum
```

- Graph 기반으로 LLM 질의 시 관련 문서를 자동 탐색

---

### 🧩 개선 방안 4: DTO 필드 기반 응답 생성 구조

- DTO 클래스에서 필드 정보, 주석 등을 `metadata`에 구조화하여 저장
- LLM 프롬프트에서 이를 활용한 템플릿 생성

```text
UserDto 필드:
- name: 사용자 이름
- email: 이메일 주소
- age: 나이 (Range: 0~120)

→ "이 DTO는 어떤 유효성 검사가 필요한가?" 질문에 직접 사용 가능
```

---

## 3. ✅ 요약

| 개선 항목 | 기대 효과 |
|-----------|------------|
| `import` 분석 | 연관된 문서까지 포함한 정확도 높은 검색 |
| 하이브리드 retriever 확장 | 의존성 있는 클래스 자동 검색 |
| ComposableGraph 도입 | 코드 구조를 반영한 계층 질의 가능 |
| DTO 주석 구조화 | 코드 생성/유효성 검사 기능에 바로 활용 가능 |

---

## 4. 🏁 결론

기존 LlamaIndex 기반 chunking + 벡터 검색은 **정적 분석 수준의 코드 이해 부족**  
→ **연결 관계 기반 RAG 구조**로 확장해야 실제 "IDE 수준의 코드 어시스턴트" 기능 가능
