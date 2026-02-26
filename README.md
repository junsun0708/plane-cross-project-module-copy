# Plane Module Migration Tool

이 도구는 Plane(https://plane.so) 인스턴스 내에서 특정 프로젝트의 **모듈(Module)**과 그에 속한 모든 **작업 아이템(Work Items, 하위 이슈 포함)**을 다른 프로젝트로 **복제(Clone)**하는 Python 스크립트입니다.

## 🚀 주요 기능
- **통째 복제**: 지정한 모듈의 모든 티켓과 하위 이슈 구조를 유지하며 복제합니다.
- **원본 보존**: 기존 데이터는 절대 건드리지 않으며, 대상 프로젝트에 새로운 티켓을 생성합니다.
- **상세 정보 유지**: 상태(State), 우선순위, 시작/마감일, 추정치, 레이블을 매핑합니다.
- **협업 데이터 복사**: 담당자(Assignee) 매핑, 모든 댓글(Comment) 복사, 활동(Activity) 내역 요약 기록.
- **원본 정보 기록**: 원본 작성자 정보를 티켓 설명 상단에 자동으로 추가합니다.

## 🛠️ 사전 준비
스크립트를 실행하려면 다음 환경이 필요합니다.

1. **Python 3.x**: 시스템에 설치되어 있어야 합니다.
2. **Requests 라이브러리**:
   ```bash
   pip install requests
   ```

## ⚙️ 환경 설정 (.env)
스크립트와 같은 경로에 `.env` 파일을 만들고 아래 내용을 설정합니다.

```env
PLANE_BASE_URL=https://your-plane-url.com
PLANE_API_KEY=your_api_key_here
PLANE_WORKSPACE_SLUG=your_workspace_slug
PLANE_SOURCE_PROJECT=prj1  # 소스 프로젝트 이름 또는 ID
PLANE_TARGET_PROJECT=prj2         # 대상 프로젝트 이름 또는 ID
```

## 📋 사용 방법

### 1. 테스트 실행 (Dry-run)
실제 데이터를 생성하지 않고 어떤 데이터가 복제될지 목록만 확인합니다. 프로젝트를 생략하면 `.env`에 설정된 기본값이 사용됩니다.
```bash
# 기본 프로젝트 사용
### 1. 프로젝트 진행 현황 리포트
```bash
python3 plane_report.py --project "프로젝트명"
```

### 2. 프로젝트 건강도 (정합성) 체크
데이터 누락이나 지연된 작업을 찾아냅니다. 기본적으로 **마감일이 지난 티켓**만 보여주며, 옵션을 통해 검사 범위를 넓힐 수 있습니다.
```bash
# 기본: 지연된 티켓만 검사
python3 plane_health.py --project "프로젝트명"

# -1: 지연 티켓 + 담당자 누락 추가 검사
python3 plane_health.py --project "프로젝트명" -1

# -2: 지연 티켓 + 담당자 누락 + 설명 부실 추가 검사
python3 plane_health.py --project "프로젝트명" -2

# -3: 전체 검사 (마감일 누락 포함 모든 권고 사항)
python3 plane_health.py --project "프로젝트명" -3
```

| 레벨 | 옵션 | 검사 항목 |
| :--- | :--- | :--- |
| **0** | (기본) | 마감일이 어제보다 이전인 티켓 (일정 지연) |
| **1** | `-1` | 담당자(Assignee)가 지정되지 않은 티켓 추가 |
| **2** | `-2` | 설명(Description)이 없거나 너무 짧은 티켓 추가 |
| **3** | `-3` | 진행 중인데 마감일이 없는 티켓 등 모든 항목 검사 |

### 3. 모듈 마이그레이션
```bash
python3 plane_migrate.py --source "소스프로젝트명" --target "대상프로젝트명" --module "모듈명"
```

### 4. 벌크 작업 (상태별 티켓 조회 및 처리)
특정 상태의 티켓들을 한꺼번에 조회하거나 처리 대상 목록을 확인합니다.
```bash
# 진행 중(In Progress)인 티켓 목록 조회
python3 plane_bulk.py --project "프로젝트명" --action list-started

# 대기 중(Backlog)인 티켓 목록 조회
python3 plane_bulk.py --project "프로젝트명" --action list-backlog

# 시작 전(Todo)인 티켓 목록 조회
python3 plane_bulk.py --project "프로젝트명" --action list-unstarted

# 완료된 티켓 목록 조회
python3 plane_bulk.py --project "프로젝트명" --action list-completed

# 완료된 티켓 아카이브 대상 확인 (Dry-run)
python3 plane_bulk.py --project "프로젝트명" --action archive-completed
```

| 액션명 | 설명 |
| :--- | :--- |
| `list-backlog` | 백로그 상태의 티켓 목록 출력 |
| `list-unstarted` | 아직 시작하지 않은(Todo) 티켓 목록 출력 |
| `list-started` | 진행 중(In Progress)인 티켓 목록 출력 |
| `list-completed` | 완료된 티켓 목록 출력 |
| `archive-completed` | 완료된 티켓의 아카이브/삭제 대상 확인 |

## 📂 파일 구조 및 설명
- `plane_client.py`: **공통 API 클라이언트**. 모든 도구의 기반이 되는 핵심 모듈입니다.
- `plane_migrate.py`: **모듈 및 이슈 복제**. 프로젝트 간 데이터 이전용 도구입니다.
- `plane_report.py`: **진행 현황 리포트**. 프로젝트 요약 및 리포팅 도구입니다.
- `plane_health.py`: **건강도 체크**. 운영 규칙 준수 여부 및 데이터 누락 검사 도구입니다.
- `plane_bulk.py`: **벌크 액션**. 대량 작업(조회/아카이브 대상 확인 등)을 위한 도구입니다.
- `check_projects.py` & `check_api_data.py`: 사전 검증 및 디버깅을 위한 보조 도구입니다.
- `logs/`: 각 도구의 실행 결과 및 분석 데이터가 보관되는 폴더입니다.

## 💡 주의 및 참고 사항
- **사용자 매핑**: 소스 프로젝트와 대상 프로젝트에 참여한 사용자의 **이메일**이 일치해야 담당자가 정상적으로 지정됩니다.
- **상태 및 레이블**: 이름이 동일한 경우에만 매핑됩니다. (예: 'Todo' -> 'Todo')
- **댓글 작성자**: 전체 API 권한 문제로 인해 댓글은 스크립트를 실행한 사람의 이름으로 작성되지만, 내용 상단에 **[원본 작성자 이름]**이 명시됩니다.
- **실행 로그**: 모든 실행 결과는 `logs/` 폴더 내에 텍스트 파일로 기록하여 추적할 수 있습니다.
