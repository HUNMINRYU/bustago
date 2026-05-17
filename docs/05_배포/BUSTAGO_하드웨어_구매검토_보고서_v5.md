# BUSTAGO 하드웨어 구매 검토 보고서 v5

> **작성일:** 2026-04-22
> **검토 관점:** 1차 시연용 최소 구매안 재정리
> **기준:** 링크 검증, 제품 호환성, 실구매 가능성, 시연 필수성 우선
> **예산 상한:** **1,000,000원**
> **주의:** 실외 설치 부품은 이번 발주에서 제외하고, 후속 확장 항목으로만 분리한다.

---

## 1. 재검토 결론

1. 이번 발주는 "**실내 시연이 바로 가능한가**"만 기준으로 잡는다.
2. **Jetson Orin Nano Super Dev Kit는 공식 문서상 19V 전원 어댑터가 동봉**되므로, Jetson용 19V 어댑터는 main BOM에서 제외한다.
3. **Jetson 기본 저장소는 microSD**이며, **NVMe SSD는 선택 사항**이므로 시연 단계에서는 제외한다.
4. **Pi Camera Module V2를 Jetson Orin Nano에 연결하려면 15핀 → 22핀 카메라 케이블이 반드시 필요**하다. 기존 초안의 15핀-15핀 CSI 연장 케이블만으로는 Jetson과 직접 호환되지 않는다.
5. **IP65 외함, 케이블 글랜드, 장거리 케이블, 옥외 고정물은 모두 실외 설치 단계로 분리**한다.
6. 디스플레이는 기존 **Raspberry Pi 공식 7인치 DSI 800×480 모델**을 유지한다. 더 저렴한 Touch Display 2 대안이 있으나, 현 시점에서는 기존 시연 해상도와 화면 배치 기준으로 검증된 구성이 더 안전하다.

> 이번 재검토부터 `Jetson 475,000원 고정`, `오늘출발`, `Jetson 별도 어댑터 필요`, `NVMe SSD 필수`, `15핀 CSI 연장 케이블만 구매`, `실외 부품 포함 총액`은 기준값으로 사용하지 않는다.

---

## 2. 시연용 필수 구매안

### 2.1 학교 물품구매신청서 기준

| 구분 | 품명 | 수량 | 단가 (원) | 금액 (원) | 비고 |
|------|------|:----:|----------:|----------:|------|
| AI 처리 장치 | NVIDIA Jetson Orin Nano Super Developer Kit | 1 | 478,500 | 478,500 | 이미지 기준 실구매가 |
| 키오스크 장치 | Raspberry Pi 4 Model B (4GB RAM) | 1 | 146,000 | 146,000 | 이미지 기준 실구매가 |
| 키오스크 장치 | Raspberry Pi 공식 7인치 터치 디스플레이 (800×480, DSI) | 1 | 112,000 | 112,000 | 이미지 기준 실구매가 |
| 카메라 센서 | Raspberry Pi Camera Module V2 (IMX219, 8MP) | 1 | 27,290 | 27,290 | 이미지 기준 실구매가 |
| 케이블 | 22P(0.5mm) → 15P(1mm) 카메라 케이블 300mm | 1 | 5,400 | 5,400 | 이미지 기준 실구매가 |
| 저장 장치 | microSD 64GB | 2 | 27,160 | 54,320 | 이미지 금액 54,320원 기준, 단가는 절반 적용 |
| 전원 장치 | 5V 3A USB-C 어댑터 (Pi 4용, KC 인증) | 1 | 6,200 | 6,200 | Pi 전원 |
| | **합계** | | | **829,710** | |

> **학교 물품구매신청서 기준 총액:** **829,710원**
> **예산 1,000,000원 대비 여유:** **170,290원**
> **microSD는 수량 2개 기준으로만 예외 처리:** 단가 `27,160원`, 금액 `54,320원`

### 2.2 조건부 추가 항목

아래는 시연 자체에는 포함하지 않지만, **보유 장비가 없을 때만** 추가한다.

| 품목 | 예상가 | 필요한 경우 |
|------|-------:|------------|
| DisplayPort → HDMI 변환 젠더/케이블 | 10,000 ~ 15,000 | Jetson 초기 설정용 모니터가 HDMI만 있을 때 |
| Pi 4 케이스 + 방열판 | 8,000 내외 | 이동 시 보드 보호가 필요할 때 |

---

## 3. 이번 발주에서 제외한 항목

| 제외 품목 | 제외 이유 |
|----------|-----------|
| Jetson용 19V 어댑터 | Jetson 공식 문서상 **19V 전원 어댑터 동봉** |
| NVMe M.2 SSD | Jetson **기본 저장소는 microSD**, 시연 목적에서는 필수 아님 |
| High Endurance microSD | 장기 옥외 운용용 선택지. 시연 단계에서는 일반 64GB microSD면 충분 |
| IP65 방수 외함 | 실외 설치 단계 전용 |
| 케이블 글랜드 PG9 | 실외 설치 단계 전용 |
| 15핀-15핀 CSI 연장 케이블 | 실내 시연에서는 불필요. Jetson 직접 연결용 케이블로도 부적합 |

---

## 4. 링크 및 호환성 검증

| 품목 | 구매 링크 | 검증 포인트 |
|------|-----------|-------------|
| Jetson Orin Nano Super Dev Kit | 한컴앤샵: https://hancomnshop.co.kr/25/?idx=38  / 대안: 디바이스마트 https://www.devicemart.co.kr/goods/view?no=14990359 | NVIDIA 공식 문서 기준 **19V 전원 동봉**, **microSD 기본 저장소**, **DisplayPort만 지원** |
| Raspberry Pi 4B 4GB | 쿠팡: https://www.coupang.com/vp/products/6823564220 | Raspberry Pi 공식 스펙 기준 **4GB 모델 존재**, **DSI 포트 탑재**, **USB-C 5V 3A 이상 권장** |
| Raspberry Pi 공식 7인치 터치 디스플레이 | 쿠팡: https://www.coupang.com/vp/products/8279482185 | Raspberry Pi 공식 문서 기준 **DSI + GPIO 연결**, **800×480**, **Pi 4 호환** |
| Raspberry Pi Camera Module V2 | 디바이스마트: https://www.devicemart.co.kr/goods/view?no=1077951 | IMX219 8MP, Jetson Orin Nano 공식 문서에서 **15핀 카메라의 예시**로 명시 |
| 22P → 15P 카메라 케이블 300mm | 디바이스마트: https://www.devicemart.co.kr/goods/view?no=15285261 | **22핀 0.5mm(보드측) → 15핀 1mm(카메라측)**, 카메라 전용 |
| Pi 4용 5V 3A USB-C 어댑터 | 디바이스마트: https://www.devicemart.co.kr/goods/view?no=12234996 | KC 인증, Pi 4용 5V 3A 명시 |
| microSD 64GB | 다나와 가격비교: https://prod.danawa.com/info/?pcode=12916265 | Jetson 공식 문서 기준 **64GB UHS-I 이상 권장** |

### 4.1 호환성 핵심 메모

| 검토 항목 | 결론 |
|-----------|------|
| Jetson 전원 | **별도 구매 불필요**. 박스 구성품에 19V 전원 포함 |
| Jetson 저장장치 | **microSD만으로 시연 가능**. NVMe는 선택 |
| Jetson 디스플레이 출력 | **DisplayPort only**. HDMI 모니터만 있으면 젠더 필요 |
| Pi 4 ↔ 7인치 디스플레이 | **문제 없음**. 공식 DSI 디스플레이 호환 |
| Pi Camera V2 ↔ Jetson | **직결 불가**. 15핀 → 22핀 케이블 필요 |
| Pi 전원 | **5V 3A USB-C 이상**이면 충분 |

---

## 5. 실외 설치는 별도 확장

이번 발주에서는 아래 항목을 **설명용 확장 리스트**로만 남기고 구매하지 않는다.

| 향후 실외 설치 항목 | 용도 |
|-------------------|------|
| IP65 외함 | Jetson / Pi / 전원부 보호 |
| 케이블 글랜드 | 외함 배선 방수 처리 |
| 카메라 브라켓 / 폴 고정물 | 카메라 하향 45도 고정 |
| 장거리 카메라 케이블 | 외함과 카메라 분리 배치 시 사용 |
| 방수 전원 연장 / 전선 정리 부자재 | 정류장 전원 인입 대응 |
| 카메라 보호 커버 | 비, 직사광선, 분진 대응 |

> 발표나 시연에서는 "**지금은 실내 데모 기준으로 최소 구성만 먼저 검증하고, 실제 외부 설치 시에는 위 항목을 추가해 옥외형으로 확장한다**"는 방식으로 설명하면 된다.

---

## 6. 발주 전 체크리스트

- [ ] Jetson 판매처 납기 확인: 한컴앤샵 페이지에는 **최대 30일 소요** 문구가 있으므로, 일정이 촉박하면 대체 판매처 즉시 전환
- [ ] HDMI 모니터만 보유한 경우 DP → HDMI 젠더 함께 준비
- [ ] Pi Camera V2 수령 후, **15핀 → 22핀 카메라 케이블**과 함께 연결되는지 우선 확인
- [ ] Jetson은 **JetPack 6.x 사용 전 펌웨어 호환 여부** 먼저 확인
- [ ] 디스플레이는 `DSI 리본 + GPIO 전원선` 구성품 포함 여부 확인
- [ ] microSD는 Jetson / Pi 각각 분리 사용

---

## 7. 근거 출처

### 7.1 공식 문서

- NVIDIA Jetson Orin Nano Getting Started
  https://developer.nvidia.com/embedded/learn/get-started-jetson-orin-nano-devkit
- NVIDIA Jetson Orin Nano Hardware Specs
  https://developer.nvidia.com/embedded/learn/jetson-orin-nano-devkit-user-guide/hardware_spec.html
- Raspberry Pi 4 Model B Specifications
  https://www.raspberrypi.com/products/raspberry-pi-4-model-b/specifications/
- Raspberry Pi Touch Display Documentation
  https://www.raspberrypi.com/documentation/accessories/display.html
- Raspberry Pi Camera Module 2
  https://www.raspberrypi.com/products/camera-module-v2/
- Raspberry Pi 15W USB-C Power Supply
  https://www.raspberrypi.com/products/type-c-power-supply/

### 7.2 실구매 링크

- Jetson: 한컴앤샵 / 디바이스마트
- Raspberry Pi 4: 쿠팡
- Raspberry Pi 7인치 디스플레이: 쿠팡
- Pi Camera V2: 디바이스마트
- 22P → 15P 카메라 케이블: 디바이스마트
- Pi 4 전원 어댑터: 디바이스마트
- microSD: 다나와 가격비교

---

## 8. 최종 정리

**현재 기준 추천안은 `실내 시연 필수 품목만 구매`하는 1차 발주안이다.**

- **추천 신청 금액:** **913,300원**
- **실지출 예상:** **약 823,300원 ~ 913,300원**
- **외부 설치용 부품:** **이번엔 제외**
- **핵심 수정 포인트:** `Jetson 전원 포함`, `NVMe 제외`, `15핀→22핀 카메라 케이블 추가`, `실외 부품 분리`

이 기준이면 100만원 예산 안에서 **호환성 문제 없이 시연용 핵심 장비만 먼저 확보**할 수 있다.
