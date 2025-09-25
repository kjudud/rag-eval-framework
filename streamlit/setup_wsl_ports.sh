#!/bin/bash
# WSL 환경에서 포트 포워딩 설정 스크립트

echo "🔧 WSL 포트 포워딩 설정 시작..."

# WSL IP 주소 확인
WSL_IP=$(hostname -I | awk '{print $1}')
echo "📍 WSL IP 주소: $WSL_IP"

# Windows에서 포트 포워딩 설정
echo "🔗 Windows에서 포트 포워딩 설정 중..."

# PowerShell 명령어로 포트 포워딩 설정
powershell.exe -Command "
    # 관리자 권한으로 실행 확인
    if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] 'Administrator')) {
        Write-Host '❌ 관리자 권한이 필요합니다. PowerShell을 관리자로 실행해주세요.' -ForegroundColor Red
        exit 1
    }
    
    # 기존 포트 포워딩 규칙 삭제
    netsh interface portproxy delete v4tov4 listenport=5000
    netsh interface portproxy delete v4tov4 listenport=8501
    
    # 새로운 포트 포워딩 규칙 추가
    netsh interface portproxy add v4tov4 listenport=5000 listenaddress=0.0.0.0 connectport=5000 connectaddress=$WSL_IP
    netsh interface portproxy add v4tov4 listenport=8501 listenaddress=0.0.0.0 connectport=8501 connectaddress=$WSL_IP
    
    # 포트 포워딩 규칙 확인
    netsh interface portproxy show all
    
    Write-Host '✅ 포트 포워딩 설정 완료!' -ForegroundColor Green
    Write-Host '🌐 API 서버: http://localhost:5000' -ForegroundColor Cyan
    Write-Host '🌐 Streamlit: http://localhost:8501' -ForegroundColor Cyan
"

echo "🎉 WSL 포트 포워딩 설정 완료!"
echo "📝 사용 방법:"
echo "1. python academic_rag_api.py  # API 서버 시작"
echo "2. streamlit run streamlit_page.py  # Streamlit 시작"
echo "3. 브라우저에서 http://localhost:5000 (API), http://localhost:8501 (Streamlit) 접속"
