# 🚀 github-config-manager

> **License:** MIT  
> **Python Version:** 3.9+

**`github-config-manager`**는 GitHub CLI(`gh`)를 활용하여 **여러 GitHub 리포지토리의 Secrets 및 Variables를 일괄적으로 관리**하고 자동화할 수 있는 강력한 도구입니다.  
조직 내 리포지토리 설정을 일관되게 유지하거나 대량 업데이트가 필요한 경우에 특히 유용합니다.

---

## ✨ 주요 기능

- 🔐 **Secrets 및 Variables 일괄 삭제**  
  지정된 항목들을 여러 리포지토리에서 한 번에 삭제합니다.

- 🛠️ **Secrets 및 Variables 일괄 설정/업데이트**  
  여러 리포지토리에 동일한 값들을 빠르게 설정하거나 업데이트합니다.  
  `--force` 옵션을 통해 덮어쓰기 여부를 제어할 수 있습니다.

- 🔎 **리포지토리 자동 탐색**  
  GitHub 조직 또는 사용자 계정의 모든 리포지토리를 자동으로 탐색하여 대상 리스트로 사용합니다.

- 🎯 **특정 리포지토리만 지정 가능**  
  파일(`--tr`)을 통해 특정 리포지토리 목록만 대상으로 작업할 수 있습니다.

- ⚙️ **병렬 처리 지원**  
  다수의 리포지토리를 여러 스레드로 병렬 처리하여 작업 속도를 대폭 향상시킵니다.

- ✅ **작업 전 사용자 확인 요청**  
  실제 작업 수행 전, 작업 대상과 내용을 사용자에게 명확히 보여주고 최종 확인을 받습니다.

- 📈 **실시간 진행 상황 및 상세 로그 출력**  
  각 리포지토리의 작업 결과를 확인 가능하며, 전체 진행 상황을 실시간으로 표시합니다.

- 🛑 **작업 중단 기능 제공**  
  실행 도중 언제든지 `'q' + Enter`를 입력하여 안전하게 작업을 중단할 수 있습니다.

---

## 🚀 시작하기

### 📋 전제 조건

- Python 3.9 이상
- GitHub CLI (`gh`) 설치 및 로그인 필요  
  👉 설치 가이드: https://cli.github.com/  
  👉 로그인: `gh auth login`

- 필수 GitHub 권한 (Scopes):**

`github-config-manager`가 Secrets 및 Variables 작업을 성공적으로 수행하려면, `gh auth login` 시 발급받는 GitHub Personal Access Token (PAT)에 다음 권한(Scope)이 부여되어야 합니다.

* `repo`: 리포지토리 Secrets 및 Variables를 읽고, 쓰고, 삭제하는 데 필요합니다.
* `read:org`: (선택 사항) 특정 조직의 모든 리포지토리 목록을 가져올 때 필요합니다. 개인 리포토리만 관리한다면 필수는 아닙니다.

이 권한들은 `gh auth login` 과정에서 GitHub CLI가 자동으로 제안하거나, 사용자가 명시적으로 선택할 수 있습니다.


### 📦 설치

```bash
git clone https://github.com/your-username/github-config-manager.git
cd github-config-manager
pip install -r requirements.txt
```



---

### 사용법

'main.py' 스크립트를 사용하여 작업을 수행합니다. 다양한 명령줄 인자를 통해 Secret 및 Variable 작업 방식을 제어할 수 있습니다.
```bash
python main.py --help
```

예시:

1. 특정 조직의 모든 리포지토리에서 Secret 삭제:
   'my-org' 조직의 모든 리포지토리에서 'OLD_SECRET'이라는 Secret을 삭제합니다.

   echo "OLD_SECRET" > secrets_to_delete.txt
   python main.py -o my-org -ds secrets_to_delete.txt

2. 새로운 Secret 및 Variable 설정/업데이트 (기존 존재 시 건너뛰기):
   'my-org' 조직의 모든 리포지토리에 'NEW_SECRET=value1' Secret과 'APP_VERSION=1.0' Variable을 설정합니다. 이미 존재하면 건너뜁니다.

   echo "NEW_SECRET=value1" > secrets.env
   echo "APP_VERSION=1.0" > variables.env
   python main.py -o my-org -s secrets.env -v variables.env

3. 특정 리포지토리 목록에 Secret 강제 업데이트:
   'target_repos.txt'에 나열된 리포지토리에서 'API_KEY' Secret을 강제로 업데이트합니다.

```bash
   # target_repos.txt 예시:
   # my-org/repo-a
   # another-org/repo-b
```

```bash
   echo "API_KEY=new_super_secret" > api_key.env
   python main.py -tr target_repos.txt -s api_key.env --force
```

4. 다중 워커(병렬 처리)를 사용하여 Secret 및 Variable 삭제/설정:
   'my-org' 조직의 리포지토리를 5개의 워커(스레드)로 병렬 처리합니다.

```bash
   echo "SECRET_TO_DELETE" > delete_secrets.txt
   echo "VAR_TO_SET=value" > set_vars.txt
   python main.py -o my-org -ds delete_secrets.txt -v set_vars.txt -w 5
```

### 인자 (Arguments)

단축 | 전체 인자 | 설명 | 필수
:--- | :--------------- | :----------------------------------------------------------------------------- | :---
-o | --organization | 작업할 GitHub 조직 또는 사용자 이름 (예: 'my-org' 또는 'my-username') | 예
-s | --secrets-file | 설정할 Secret 이름과 값을 포함하는 파일 경로 (예: 'SECRET_NAME=VALUE') | 아니오
-v | --values-file | 설정할 Variable 이름과 값을 포함하는 파일 경로 (예: 'VAR_NAME=VALUE') | 아니오
-ds | --ds | 삭제할 Secret 이름 목록을 포함하는 파일 경로 (한 줄에 하나씩) | 아니오
-dv | --dv | 삭제할 Variable 이름 목록을 포함하는 파일 경로 (한 줄에 하나씩) | 아니오
-tr | --tr | 작업을 수행할 특정 리포지토리 목록을 포함하는 파일 경로 (한 줄에 하나씩, 'repo' 형식). 지정하지 않으면 organization내의 모든 repo에 적용 | 아니오
-w | --workers | 동시에 처리할 최대 워커(스레드) 수 (기본값: '1' - 순차 처리) | 아니오
-sl | --sleep | 각 리포지토리 처리 후 대기 시간(초) (순차 처리 시 적용, 기본값: '0') | 아니오
-f | --force | Secret/Variable 설정 시 기존 값을 강제로 덮어쓸지 여부 (기본값: 'False') | 아니오

---

### 파일 포맷
1. --secrets-file, --values-file 포맷
```txt
# secrets.env 파일 예시:
MY_API_KEY=your_secret_or_value_here
DATABASE_URL=postgres://user:pass@host:port/dbname
```

2. --ds, --dv 포맷
```txt
# secrets_to_delete.txt 파일 예시:
MY_API_KEY
DATABASE_URL
```

3. --tr
```txt
repo-name1
repo-name2
repo-name3
```


## 기여하기

기여는 언제나 환영입니다! 버그 보고, 기능 제안, 코드 개선 등 어떤 형태의 기여라도 좋습니다.

1. 이 저장소를 Fork 합니다.
2. 새로운 Feature Branch를 생성합니다 ('git checkout -b feature/AmazingFeature').
3. 변경 사항을 Commit 합니다 ('git commit -m 'Add some AmazingFeature'').
4. Branch를 Push 합니다 ('git push origin feature/AmazingFeature').
5. Pull Request를 엽니다.

---

## 이 프로젝트가 유용하다면 Star를 눌러주세요!

---

## 라이선스

이 프로젝트는 MIT 라이선스에 따라 배포됩니다. 자세한 내용은 'LICENSE' 파일을 참조하세요.