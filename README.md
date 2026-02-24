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
python3 plane_migrate.py --dry-run --module "ETC"

# 프로젝트 명시적 지정 (이름 또는 ID)
python3 plane_migrate.py --dry-run --source "prj1" --target "prj2" --module "ETC"
```

### 2. 실제 복제 실행
특정 모듈을 지정하여 마이그레이션을 진행합니다.
```bash
python3 plane_migrate.py --source "소스프로젝트명" --target "대상프로젝트명" --module "모듈명"
```

### 3. 대화형 실행
모듈 이름을 지정하지 않으면 사용 가능한 모듈 목록이 출력되며 번호를 선택할 수 있습니다.
```bash
python3 plane_migrate.py
```

## 📂 파일 구조 및 설명
- `plane_migrate.py`: **메인 마이그레이션 스크립트**. 모듈 및 하위 이슈 복제 로직의 핵심입니다.
- `check_projects.py`: 워크스페이스 내 프로젝트 목록 및 특정 프로젝트의 모듈 정보를 조회합니다.
- `check_api_data.py`: 사용자(Member), 주기(Cycle), 추정치(Estimate) 등 API 연동 데이터를 사전에 검증합니다.
- `debug_ids.py`: 소스 프로젝트와 대상 프로젝트 간의 데이터 매핑 상태를 디버깅하는 도구입니다.
- `logs/`: 마이그레이션 실행 결과(`*.txt`) 및 분석용 샘플 데이터(`*.json`)가 보관되는 폴더입니다.

## 💡 주의 및 참고 사항
- **사용자 매핑**: 소스 프로젝트와 대상 프로젝트에 참여한 사용자의 **이메일**이 일치해야 담당자가 정상적으로 지정됩니다.
- **상태 및 레이블**: 이름이 동일한 경우에만 매핑됩니다. (예: 'Todo' -> 'Todo')
- **댓글 작성자**: 전체 API 권한 문제로 인해 댓글은 스크립트를 실행한 사람의 이름으로 작성되지만, 내용 상단에 **[원본 작성자 이름]**이 명시됩니다.
- **실행 로그**: 모든 실행 결과는 `logs/` 폴더 내에 텍스트 파일로 기록하여 추적할 수 있습니다.
