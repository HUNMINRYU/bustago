// BUSTAGO Kakao map adapter.
// 화면별 variant는 map-config.js의 BUSTAGO_MAP_VARIANTS에서 가져온다.
(function () {
  var sdkPromise = null;

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function injectStyle() {
    if (document.getElementById('bustago-kakao-map-style')) return;
    var style = document.createElement('style');
    style.id = 'bustago-kakao-map-style';
    style.textContent =
      '.btg-map-message{height:100%;min-height:180px;display:flex;align-items:center;justify-content:center;text-align:center;padding:18px;color:#757575;background:#f8fafc;border:1px dashed #cbd5e1;border-radius:6px;font-size:13px;line-height:1.45;}' +
      '.btg-map-marker{position:relative;display:flex;align-items:center;justify-content:center;border-radius:999px;border:3px solid #fff;box-shadow:0 3px 10px rgba(15,23,42,.28);color:#fff;font-weight:800;font-size:11px;cursor:pointer;}' +
      '.btg-map-marker-label{position:absolute;left:50%;top:calc(100% + 5px);transform:translateX(-50%);white-space:nowrap;background:#fff;color:#0f172a;border:1px solid #e2e8f0;border-radius:999px;padding:3px 8px;font-size:11px;font-weight:700;box-shadow:0 2px 8px rgba(15,23,42,.18);}' +
      '.btg-map-info{background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:8px 10px;box-shadow:0 6px 18px rgba(15,23,42,.22);font-size:12px;color:#0f172a;white-space:nowrap;}' +
      '.btg-map-info b{display:block;margin-bottom:3px;font-size:13px;}' +
      '.btg-map-info span{color:#475569;}';
    document.head.appendChild(style);
  }

  function getAppKey() {
    var meta = document.querySelector('meta[name="kakao-map-app-key"]');
    return window.BUSTAGO_KAKAO_APP_KEY ||
      (meta ? meta.getAttribute('content') : '') ||
      '';
  }

  function showMessage(container, message) {
    container.innerHTML = '<div class="btg-map-message">' + esc(message) + '</div>';
  }

  function makeNoopController(container, message) {
    showMessage(container, message);
    return {
      setMarkers: function (markers) {
        var names = (markers || []).map(function (m) { return m.name; }).filter(Boolean);
        var suffix = names.length ? '\n표시 대상: ' + names.join(', ') : '';
        showMessage(container, message + suffix);
      },
      resize: function () {},
    };
  }

  function loadSdk(appKey) {
    if (window.kakao && window.kakao.maps) return Promise.resolve();
    if (!appKey) return Promise.reject(new Error('missing kakao app key'));
    if (sdkPromise) return sdkPromise;

    sdkPromise = new Promise(function (resolve, reject) {
      var script = document.createElement('script');
      script.src = 'https://dapi.kakao.com/v2/maps/sdk.js?appkey=' +
        encodeURIComponent(appKey) + '&autoload=false';
      script.async = true;
      script.onload = function () {
        if (!window.kakao || !window.kakao.maps) {
          reject(new Error('kakao maps namespace missing'));
          return;
        }
        window.kakao.maps.load(resolve);
      };
      script.onerror = function () { reject(new Error('kakao sdk load failed')); };
      document.head.appendChild(script);
    });

    return sdkPromise;
  }

  function markerText(level) {
    var labels = ['여유', '보통', '혼잡', '매우'];
    return labels[Math.max(0, Math.min(3, Number(level) || 0))] || '정류장';
  }

  function create(containerId, options) {
    injectStyle();
    options = options || {};
    var container = typeof containerId === 'string'
      ? document.getElementById(containerId)
      : containerId;
    if (!container) return Promise.resolve(null);

    var variants = window.BUSTAGO_MAP_VARIANTS || {};
    var variant = variants[options.variant || 'dashboard'] || {};
    var config = Object.assign({}, variant, options);
    var center = config.center || window.BUSTAGO_MAP_CENTER || { lat: 35.1378, lng: 126.8942 };
    var appKey = getAppKey();

    return loadSdk(appKey).then(function () {
      container.innerHTML = '';
      var kakao = window.kakao;
      var map = new kakao.maps.Map(container, {
        center: new kakao.maps.LatLng(center.lat, center.lng),
        level: config.level || 4,
      });
      var overlays = [];

      function clear() {
        overlays.forEach(function (overlay) { overlay.setMap(null); });
        overlays = [];
      }

      function setMarkers(markers) {
        clear();
        markers = (markers || []).filter(function (m) {
          return Number.isFinite(Number(m.lat)) && Number.isFinite(Number(m.lng));
        });

        if (!markers.length) return;

        var bounds = new kakao.maps.LatLngBounds();
        markers.forEach(function (marker) {
          var pos = new kakao.maps.LatLng(Number(marker.lat), Number(marker.lng));
          bounds.extend(pos);

          var node = document.createElement('button');
          node.type = 'button';
          node.className = 'btg-map-marker';
          node.style.width = (config.markerSize || 26) + 'px';
          node.style.height = (config.markerSize || 26) + 'px';
          node.style.background = marker.color || '#1976D2';
          node.setAttribute('aria-label', marker.name || '정류장');
          node.innerHTML = '<span>' + esc(markerText(marker.level)) + '</span>' +
            (config.showLabels ? '<span class="btg-map-marker-label">' + esc(marker.name) + '</span>' : '');

          var info = new kakao.maps.CustomOverlay({
            position: pos,
            yAnchor: 1.75,
            content: '<div class="btg-map-info"><b>' + esc(marker.name) + '</b><span>' +
              esc(marker.meta || '') + '</span></div>',
          });
          node.addEventListener('click', function () {
            var visible = overlays.indexOf(info) >= 0;
            overlays = overlays.filter(function (overlay) {
              if (overlay === info) return true;
              if (overlay.__isInfo) overlay.setMap(null);
              return !overlay.__isInfo;
            });
            if (visible) {
              info.setMap(null);
              overlays = overlays.filter(function (overlay) { return overlay !== info; });
            } else {
              info.__isInfo = true;
              info.setMap(map);
              overlays.push(info);
            }
          });

          var overlay = new kakao.maps.CustomOverlay({
            position: pos,
            yAnchor: 0.5,
            content: node,
          });
          overlay.setMap(map);
          overlays.push(overlay);
        });

        if (config.fitBounds && markers.length > 1) {
          map.setBounds(bounds);
        } else {
          map.setCenter(bounds.getSouthWest());
        }
      }

      return {
        setMarkers: setMarkers,
        resize: function () { kakao.maps.event.trigger(map, 'resize'); },
      };
    }).catch(function () {
      return makeNoopController(
        container,
        '카카오맵 JavaScript 키가 필요합니다. meta[name="kakao-map-app-key"] 또는 window.BUSTAGO_KAKAO_APP_KEY를 설정하세요.'
      );
    });
  }

  window.BustagoKakaoMap = { create: create };
})();
