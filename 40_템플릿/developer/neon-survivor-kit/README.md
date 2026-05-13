# 🌌 네온서바이버 샘플팩 — Vampire Survivors + PayPal

네온 비주얼 + 자동 조준 + 레벨업 + 보스 + **PayPal 인앱 결제 통합**.
단일 HTML, 빌드 X, 클릭 한 번이면 작동.

## 게임 구성
- **자동 사격** — 가장 가까운 적 자동 조준
- **레벨업 시스템** — XP 젬 → 3개 강화 중 선택 (10가지 무기·체력·자석 등)
- **6종 적** — basic·fast·shooter·tank·splitter·mini·boss
- **1분마다 보스 출현** — 800 HP, 8발 산탄
- **모바일 지원** — 좌측 가상 조이스틱

## PayPal 결제 통합 (핵심!)
1. **Premium Pack $2.99** — 시작 데미지 +30%, HP +50, 자석 +50%
2. **Revive $0.99** — GAME OVER 후 부활 (HP 풀회복 + 무적 3초)

⚠️ **PayPal client-id 교체 필수**:
```html
<script src="https://www.paypal.com/sdk/js?client-id=YOUR_OWN_CLIENT_ID&currency=USD"></script>
```
샘플의 client-id 는 큐레이터 라이브 계정 — 그대로 두면 결제가 큐레이터에게 갑니다.

## 사용법
1. 코다리에게 "네온 서바이버 게임 만들어줘" 요청
2. ~/connect-ai-projects/neon-survivor/ 에 자동 복사
3. open index.html 또는 python3 -m http.server 8000

## 커스터마이즈 포인트
- **결제 금액·문구**: createOrder 안의 value / description
- **Premium 효과**: resetGame() 의 isPremium 분기
- **적 종류·HP**: spawnEnemyAt() 의 switch 블록
- **강화 옵션**: UPGRADES 배열 (10가지 — 추가/수정 자유)
- **색상 팔레트**: CSS linear-gradient 부분
- **사운드**: beep() 호출부 (Web Audio API)

## 응용 아이디어
- 광고 보고 부활 (AdMob/AdSense 추가)
- 캐릭터 스킨 $1.99 추가 상품
- 일일 미션 + 리더보드 (Firebase / Supabase)
- 멀티플레이 (WebRTC / WebSocket)
