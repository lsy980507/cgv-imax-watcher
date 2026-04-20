# CGV 용산아이파크몰 IMAX 감시 봇 - 설치 가이드

현재 완료된 것:
- ✅ Git 설치 확인 (2.53.0)
- ⬜ gh CLI 설치
- ⬜ GitHub 로그인
- ⬜ Git 리포 초기화
- ⬜ GitHub에 Public 리포 생성 & 푸시
- ⬜ Secrets 등록
- ⬜ 첫 실행 트리거
- ⬜ 텔레그램 메시지 확인

---

## 단계 1. (완료) Git 설치 확인

`git version 2.53.0.windows.3` 확인됨.

---

## 단계 2. GitHub CLI(`gh`) 설치

터미널(PowerShell 또는 CMD 또는 Git Bash)에서:

```
winget install --id GitHub.cli
```

설치 후 **터미널 창을 닫고 새로 열어야** PATH가 반영됩니다.

새 터미널에서 확인:

```
gh --version
```

버전 출력되면 OK. (winget이 안 되면 https://cli.github.com/ 에서 MSI 수동 설치)

---

## 단계 3. GitHub 로그인

```
gh auth login
```

대화형 프롬프트 선택 순서:

1. `GitHub.com` 선택 → Enter
2. `HTTPS` 선택 → Enter
3. `Y` (Git Credential Manager로 인증 저장) → Enter
4. `Login with a web browser` 선택 → Enter
5. 화면에 8자리 코드 표시됨 (예: `A1B2-C3D4`) → **그 코드를 복사**
6. Enter 누르면 브라우저 자동으로 열림
7. 브라우저에서 코드 붙여넣기 → Continue → Authorize github
8. 터미널로 돌아와서 `✓ Logged in as lsy980507` 비슷한 메시지 뜨면 성공

확인:

```
gh auth status
```

---

## 단계 4. 프로젝트 폴더로 이동

```
cd C:\Users\lsy98\cgv-imax-watcher
```

(Git Bash라면 `cd /c/Users/lsy98/cgv-imax-watcher`)

파일 구조 확인:

```
dir
```

`poll.py`, `requirements.txt`, `.github\`, `.gitignore`, `SETUP.md` 보여야 함.

---

## 단계 5. Git 초기화 & 첫 커밋

아래 명령을 순서대로 실행:

```
git init -b main
git config user.name "lsy980507"
git config user.email "lsy980507@gmail.com"
git add .
git commit -m "init: CGV 용산 IMAX watcher"
```

마지막 명령 끝에 `main (root-commit)` 비슷한 메시지 + 변경된 파일 개수 나오면 성공.

---

## 단계 6. GitHub에 Public 리포 생성 & 푸시

```
gh repo create cgv-imax-watcher --public --source=. --push
```

성공 시 출력:
```
✓ Created repository lsy980507/cgv-imax-watcher on GitHub
✓ Added remote https://github.com/lsy980507/cgv-imax-watcher.git
✓ Pushed commits to https://github.com/lsy980507/cgv-imax-watcher.git
```

이 URL(`https://github.com/lsy980507/cgv-imax-watcher`)을 브라우저에서 열어두세요. 다음 단계에서 씁니다.

---

## 단계 7. Secrets 등록 (브라우저)

리포 페이지에서:

1. 상단 메뉴 **Settings** 클릭
2. 왼쪽 사이드바 → **Secrets and variables** 섹션 → **Actions** 클릭
3. 초록색 **New repository secret** 버튼 클릭

### 첫 번째 시크릿

- **Name**: `TELEGRAM_BOT_TOKEN`
- **Secret**: BotFather가 준 토큰 전체 (예: `8123456789:AAH...xyz`)
- **Add secret** 클릭

### 두 번째 시크릿

다시 **New repository secret** 클릭:

- **Name**: `TELEGRAM_CHAT_ID`
- **Secret**: getUpdates로 확인한 숫자 chat_id (예: `123456789`)
- **Add secret** 클릭

목록에 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` 둘 다 보이면 완료.

**주의**: Secret 값 앞뒤에 공백이나 따옴표가 섞이면 인증 실패합니다. 붙여넣을 때 깔끔하게.

---

## 단계 8. 첫 실행 (수동 트리거)

리포 페이지에서:

1. 상단 **Actions** 탭 클릭
2. 만약 "Workflows aren't being run on this forked repository" 또는 유사 메시지가 뜨면 **"I understand my workflows, go ahead and enable them"** 클릭
3. 왼쪽 사이드바에서 **CGV IMAX Watcher** 클릭
4. 오른쪽에 "This workflow has a `workflow_dispatch` event trigger." 문구 옆 **Run workflow** 드롭다운
5. 드롭다운 열고 초록색 **Run workflow** 버튼 클릭
6. 몇 초 뒤 새로고침 → 새 실행이 목록에 뜸 (노란 동그라미 = 실행 중)
7. 1분 정도 기다리면 초록 체크로 바뀜
8. **텔레그램에 "🎬 CGV 용산아이파크몰 IMAX 감시 시작" 메시지 도착** → 성공

---

## 단계 9. 최종 확인

- [ ] 텔레그램 초기 메시지 받음
- [ ] 리포 파일 목록에 `state.json` 자동 생성됨 (커밋 메시지: "chore: update IMAX state [skip ci]")
- [ ] Actions 탭에 1분 간격(실제로는 1~3분)으로 새 실행이 쌓이기 시작

이후로는 그냥 놔두면 됩니다. 용산 IMAX에 새 영화/새 날짜 오픈 시 텔레그램으로 자동 알림.

---

## 문제 해결

### Actions 실행이 빨간 X (실패)

1. Actions 탭 → 실패한 실행 클릭
2. `poll` job 클릭 → 빨간 step 클릭 → 로그 확인
3. 주요 패턴:
   - **`HTTP 403` + HTML 응답**: Cloudflare 차단 (재요청하라고 말해주세요)
   - **`HTTP 401 Unauthorized`**: Telegram 토큰이 잘못됨 → Secrets 재확인
   - **`chat not found`**: chat_id 잘못됨 → 봇과 대화 시작했는지 확인 후 getUpdates 재확인
   - **`502/503`**: CGV 서버 일시 장애 → 자동 재시도되므로 무시

### 텔레그램 메시지 안 옴

- Actions가 초록 체크인데 메시지 안 오면 → 봇이 아직 대화 시작 안 된 상태일 수 있음. 텔레그램에서 봇에게 아무 메시지나 한 번 보내고 "Run workflow" 재실행.

### 1분 주기가 2~3분씩 밀림

- GitHub Actions 스케줄러 정상 동작. 고부하 시 스케줄 코얼레스(합치기)됩니다. 평균 1~3분 간격으로 작동.

### 60일 이상 리포 활동 없으면 Actions 자동 중단

- 리포가 60일 비활성 상태면 GitHub이 scheduled workflow를 끕니다.
- Actions 탭 → "Re-enable scheduled workflows" 버튼으로 재활성.
- 예방: 가끔 "Run workflow" 수동 트리거 or 리포에 뭐든 커밋.

---

## 참고 정보

- **폴링 주기**: 1분 (cron `* * * * *`)
- **조회 범위**: 오늘 + 향후 30일
- **감지 대상**: 새 날짜 오픈 OR 기존 날짜에 새 IMAX 영화 추가
- **극장 코드**: `0013` (용산아이파크몰)
- **화면 코드**: `018` (IMAX관, 624석)
- **API**: `https://api.cgv.co.kr/cnm/atkt/searchMovScnInfo` (HMAC-SHA256 서명, curl_cffi로 Cloudflare 우회)
