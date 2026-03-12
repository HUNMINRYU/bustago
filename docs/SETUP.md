# ⚙️ 개발환경 세팅 가이드

> bustago 프로젝트 팀원 전용 개발환경 설정 가이드입니다.  
> 아래 순서대로 따라하면 개발 준비 완료!

---

## 1. 🐍 Python 설치

### 설치
1. [https://www.python.org/downloads/](https://www.python.org/downloads/) 접속
2. **Python 3.11.x** 다운로드 (3.11 권장)
3. 설치 시 **"Add Python to PATH"** 반드시 체크 ✅

### 설치 확인
```bash
python --version
# Python 3.11.x 출력되면 성공
```

---

## 2. 🗂️ Git 브랜치 전략

### 브랜치 구조
```
main        → 최종 완성본만 (직접 push 금지 🚫)
develop     → 통합 테스트용
feat/이름   → 각자 기능 개발
```

### 작업 순서
```bash
# 1. develop 최신화
git checkout develop
git pull origin develop

# 2. 본인 브랜치로 이동
git checkout feat/본인이름

# 3. develop 내용 가져오기
git merge develop

# 4. 작업 후 push
git add .
git commit -m "feat: 기능 설명"
git push origin feat/본인이름

# 5. GitHub에서 develop으로 PR 생성
```

### 커밋 메시지 규칙
| 태그 | 설명 |
|------|------|
| `feat:` | 새 기능 추가 |
| `fix:` | 버그 수정 |
| `docs:` | 문서 수정 |
| `style:` | 코드 스타일 변경 |
| `refactor:` | 코드 리팩토링 |

---

## 3. 💻 VSCode 추천 익스텐션

VSCode 설치 후 아래 익스텐션을 설치하세요.  
`Ctrl + Shift + X` → 검색 후 설치

| 익스텐션 | 용도 |
|----------|------|
| **Python** (Microsoft) | Python 개발 필수 |
| **Pylance** | Python 자동완성 |
| **GitLens** | Git 히스토리 시각화 |
| **Git Graph** | 브랜치 그래프 확인 |
| **MySQL** (cweijan) | DB 연결 및 쿼리 |
| **REST Client** | API 테스트 |
| **Prettier** | 코드 자동 정렬 |
| **indent-rainbow** | 들여쓰기 가독성 |

---

## 4. 🌶️ Flask 실행 방법

### 가상환경 생성 및 활성화
```bash
cd backend

# 가상환경 생성
python -m venv venv

# 가상환경 활성화
# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate

# 활성화 확인 → 터미널 앞에 (venv) 표시됨
```

### 패키지 설치
```bash
pip install -r requirements.txt
```

### Flask 서버 실행
```bash
python app.py
# http://127.0.0.1:5000 에서 확인
```

### 서버 종료
```bash
Ctrl + C
```

---

## 5. 🐬 MySQL 세팅

### MySQL 설치
1. [https://dev.mysql.com/downloads/installer/](https://dev.mysql.com/downloads/installer/) 접속
2. **MySQL Installer** 다운로드 및 실행
3. **Developer Default** 선택 후 설치
4. root 비밀번호 설정 (팀 공통 비밀번호 사용 - 팀장에게 문의)

### 설치 확인
```bash
mysql -u root -p
# 비밀번호 입력 후 mysql> 프롬프트 나오면 성공
```

### DB 생성
```sql
CREATE DATABASE bustago;
USE bustago;
```

### VSCode에서 MySQL 연결
1. MySQL 익스텐션 설치 (cweijan)
2. 왼쪽 DB 아이콘 클릭
3. `+` 버튼 → 아래 정보 입력
```
Host     : 127.0.0.1
Port     : 3306
User     : root
Password : (설정한 비밀번호)
Database : bustago
```

---

## ✅ 세팅 완료 체크리스트

- [ ] Python 3.11 설치 및 PATH 등록
- [ ] Git 사용자 정보 설정 (`git config --global`)
- [ ] VSCode 익스텐션 설치
- [ ] 레포 클론 및 본인 브랜치 생성
- [ ] 가상환경 생성 및 Flask 실행 확인
- [ ] MySQL 설치 및 bustago DB 생성

---

> 문제가 생기면 팀장(@HUNMINRYU)에게 문의하세요! 💬
