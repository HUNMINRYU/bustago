// BUSTAGO map variants.
// Kakao JavaScript key is intentionally not committed. Set it with:
//   window.BUSTAGO_KAKAO_APP_KEY = '...'
// or <meta name="kakao-map-app-key" content="...">
(function () {
  window.BUSTAGO_MAP_CENTER = { lat: 35.1378, lng: 126.8942 };

  // 지도는 운영 대시보드에만 노출 (학생앱·키오스크는 지도 미사용).
  window.BUSTAGO_MAP_VARIANTS = {
    dashboard: {
      center: window.BUSTAGO_MAP_CENTER,
      level: 4,
      markerSize: 28,
      showLabels: true,
      fitBounds: true,
    },
  };
})();
