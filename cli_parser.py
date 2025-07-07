# cli_parser.py

import argparse
from pathlib import Path

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="GitHub 리포지토리 Secrets 및 Variables 관리 도구",
        formatter_class=argparse.RawTextHelpFormatter
    )

    # 필수 인자
    parser.add_argument(
        "-o", "--organization",
        required=True,
        help="대상 GitHub 조직 또는 사용자 이름 (예: my-org)"
    )

    # 옵션 인자: 설정 파일 경로
    parser.add_argument(
        "-s", "--secrets-file",
        type=Path,
        dest="secrets_file", # 명시적으로 dest 지정
        help="설정할 GitHub Secrets가 포함된 파일 경로 (key=value 형식)"
    )
    parser.add_argument(
        "-v", "--values-file",
        type=Path,
        dest="values_file", # 명시적으로 dest 지정
        help="설정할 GitHub Variables가 포함된 파일 경로 (key=value 형식)"
    )

    # 옵션 인자: 삭제 목록 파일 경로
    parser.add_argument(
        "-ds", "--delete-secrets",
        type=Path,
        dest="ds", # 명시적으로 dest 지정 (args.ds로 접근 가능)
        help="삭제할 GitHub Secrets 이름 목록이 포함된 파일 경로 (한 줄에 하나씩)"
    )
    parser.add_argument(
        "-dv", "--delete-variables",
        type=Path,
        dest="dv", # 명시적으로 dest 지정 (args.dv로 접근 가능)
        help="삭제할 GitHub Variables 이름 목록이 포함된 파일 경로 (한 줄에 하나씩)"
    )

    # 옵션 인자: 특정 리포지토리만 대상
    parser.add_argument(
        "-tr", "--target-repos",
        type=Path,
        dest="tr", # 명시적으로 dest 지정 (args.tr로 접근 가능)
        help="""특정 리포지토리만 대상으로 지정합니다.
파일 형식: 한 줄에 하나씩 'org/repo' 또는 'repo' 이름.
'repo'만 지정 시 '-o'의 조직 이름이 앞에 붙습니다.
(예: my-org/repo1, my-org/repo2 또는 repo1, repo2)"""
    )

    # 병렬 처리 및 대기 시간 옵션
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=1,
        help="동시에 처리할 리포지토리 수 (기본값: 1, 즉 순차 처리)"
    )
    parser.add_argument(
        "-z", "--sleep",
        type=int,
        default=0,
        help="각 리포지토리 처리 후 대기할 시간(초) (기본값: 0, --workers가 1일 때만 유효)"
    )
    
    # --- 새로 추가할 --force 옵션 ---
    parser.add_argument(
        "-f", "--force",
        action="store_true", 
        default=False,
        help="""Secrets 또는 Variables 설정 시, 이미 존재하는 항목은 건너뛰고 없는 항목만 추가합니다.
이 옵션이 없으면 (기본값 False), 이미 존재하는 항목도 덮어씁니다.
'--delete-secrets' 및 '--delete-variables'에는 적용되지 않습니다."""
    )
    # --- 여기까지 ---

    args = parser.parse_args()
    return args