/**
 * North Carolina Student Voting Platform - Client Interactions
 * Minimal, dependency-free script for campus switching, on-click geolocation, directory filtering, and QR portal.
 */

function calculateDistance(lat1, lon1, lat2, lon2) {
  const R = 3958.8; // miles
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return Math.round(R * c * 10) / 10;
}

document.addEventListener('DOMContentLoaded', function() {
  // Campus dropdown navigation
  const campusSelect = document.getElementById('campus-select');
  if (campusSelect) {
    campusSelect.addEventListener('change', function() {
      if (this.value) {
        window.location.href = this.value;
      }
    });
  }

  // Geolocation button for nearest voting site or precinct (runs only on explicit user click)
  const geoBtn = document.getElementById('find-nearest-btn');
  const geoResult = document.getElementById('nearest-result');
  if (geoBtn && geoResult && window.NC_SITES_DATA) {
    geoBtn.addEventListener('click', function() {
      if (!navigator.geolocation) {
        geoResult.innerText = 'Geolocation is not supported by your browser.';
        return;
      }
      geoBtn.disabled = true;
      geoBtn.innerText = 'Locating...';

      navigator.geolocation.getCurrentPosition(
        function(pos) {
          geoBtn.disabled = false;
          geoBtn.innerText = 'Find nearest voting site';

          const uLat = pos.coords.latitude;
          const uLon = pos.coords.longitude;
          let closest = null;
          let minD = 999999;

          for (let s of window.NC_SITES_DATA) {
            if (s.lat && s.lon) {
              let d = calculateDistance(uLat, uLon, s.lat, s.lon);
              if (d < minD) {
                minD = d;
                closest = s;
              }
            }
          }

          if (closest) {
            const mapQuery = encodeURIComponent(closest.name + ' ' + (closest.address || ''));
            const codeLabel = closest.code ? `Precinct ${closest.code}: ` : '';
            geoResult.innerHTML = `
              <strong>Nearest location:</strong> ${codeLabel}${closest.name}<br>
              ${closest.address || ''} (${minD} miles away)<br>
              <a href="https://maps.google.com/?q=${mapQuery}" target="_blank" rel="noopener">Get directions on Google Maps</a>
            `;
          } else {
            geoResult.innerText = 'Could not determine nearest location from county list.';
          }
        },
        function(err) {
          geoBtn.disabled = false;
          geoBtn.innerText = 'Find nearest voting site';
          geoResult.innerText = 'Unable to access your location. Please check browser permissions.';
        },
        { enableHighAccuracy: true, timeout: 8000 }
      );
    });
  }

  // Directory search filter
  const searchInput = document.getElementById('directory-search');
  if (searchInput) {
    searchInput.addEventListener('input', function() {
      const q = this.value.toLowerCase().trim();
      const items = document.querySelectorAll('.directory-item');
      let visible = 0;
      items.forEach(function(item) {
        const text = item.textContent.toLowerCase();
        if (!q || text.includes(q)) {
          item.style.display = 'block';
          visible++;
        } else {
          item.style.display = 'none';
        }
      });
      const countEl = document.getElementById('directory-count');
      if (countEl) {
        countEl.innerText = `Showing ${visible} of ${items.length} institutions`;
      }
    });
  }

  // Support modal open / close
  const supportLink = document.getElementById('support-link');
  const supportDialog = document.getElementById('support-dialog');
  const supportClose = document.getElementById('support-dialog-close');
  if (supportLink && supportDialog) {
    supportLink.addEventListener('click', function(e) {
      e.preventDefault();
      supportDialog.showModal();
    });
  }
  if (supportClose && supportDialog) {
    supportClose.addEventListener('click', function() {
      supportDialog.close();
    });
  }
  if (supportDialog) {
    supportDialog.addEventListener('click', function(e) {
      if (e.target === supportDialog) {
        supportDialog.close();
      }
    });
  }

  // Portal QR code & campus selection
  if (document.getElementById('qrcode-box') && window.QRCode) {
    let currentQR = null;
    const box = document.getElementById('qrcode-box');
    const targetText = document.getElementById('qr-target-text');

    function setQR(url) {
      box.innerHTML = '';
      currentQR = new QRCode(box, {
        text: url,
        width: 180,
        height: 180,
        colorDark: "#0f172a",
        colorLight: "#ffffff",
        correctLevel: QRCode.CorrectLevel.M
      });
      if (targetText) targetText.innerText = 'Target: ' + url;
    }

    setQR('https://rannbar-on.com/dukevote');

    const picker = document.getElementById('campus-picker');
    if (picker) {
      picker.addEventListener('change', function() {
        if (this.value) {
          setQR('https://rannbar-on.com' + this.value);
        }
      });
    }

    const portalGeoBtn = document.getElementById('portal-geolocate-btn');
    const portalGeoStatus = document.getElementById('portal-geo-status');
    if (portalGeoBtn && portalGeoStatus && window.CAMPUS_LIST) {
      portalGeoBtn.addEventListener('click', function() {
        if (!navigator.geolocation) {
          portalGeoStatus.innerText = 'Geolocation is not supported by your browser.';
          return;
        }
        portalGeoBtn.disabled = true;
        portalGeoStatus.innerText = 'Locating closest campus...';
        navigator.geolocation.getCurrentPosition(
          function(pos) {
            portalGeoBtn.disabled = false;
            const uLat = pos.coords.latitude;
            const uLon = pos.coords.longitude;
            let closest = null;
            let minD = 999999;
            for (let c of window.CAMPUS_LIST) {
              if (c.lat && c.lon) {
                let d = calculateDistance(uLat, uLon, c.lat, c.lon);
                if (d < minD) {
                  minD = d;
                  closest = c;
                }
              }
            }
            if (closest) {
              const url = 'https://rannbar-on.com/' + closest.key;
              setQR(url);
              portalGeoStatus.innerHTML = `Closest campus: <strong>${closest.name}</strong> (${minD} miles away). <a href="${url}">Open guide</a>`;
            } else {
              portalGeoStatus.innerText = 'Could not determine closest campus.';
            }
          },
          function(err) {
            portalGeoBtn.disabled = false;
            portalGeoStatus.innerText = 'Unable to access your location. Please choose from the dropdown or enter your ZIP code.';
          },
          { timeout: 8000 }
        );
      });
    }

    const zipBtn = document.getElementById('zip-btn');
    const zipInput = document.getElementById('zip-input');
    const zipStatus = document.getElementById('zip-status');
    const zipMap = {
      '27708': 'dukevote', '27705': 'dukevote', '27701': 'dukevote', '27707': 'nccuvote', '27703': 'durhamtechvote',
      '27514': 'uncvote', '27515': 'uncvote', '27516': 'uncvote', '27517': 'uncvote',
      '27607': 'ncsuvote', '27695': 'ncsuvote', '27606': 'ncsuvote', '27601': 'shawvote', '27604': 'peacevote',
      '28223': 'unccvote', '28202': 'cpccvote', '28207': 'queensvote', '28216': 'jcsuvote',
      '27411': 'ncatvote', '27412': 'uncgvote', '27401': 'bennettvote', '27410': 'guilfordvote',
      '27109': 'wfuvote', '27110': 'wssuvote', '27101': 'salemvote', '27103': 'forsythtechvote',
      '28608': 'appstatevote', '27858': 'ecuvote', '28403': 'uncwvote', '28804': 'uncavote',
      '28723': 'wcuvote', '28372': 'uncpvote', '27909': 'ecsuvote', '27244': 'elonvote'
    };

    if (zipBtn && zipInput && zipStatus) {
      zipBtn.addEventListener('click', function() {
        const val = zipInput.value.trim();
        if (!val || val.length !== 5) {
          zipStatus.innerText = 'Please enter a valid 5-digit ZIP code.';
          return;
        }
        let targetKey = zipMap[val];
        if (!targetKey) {
          let prefix = val.substring(0, 3);
          if (prefix === '277') targetKey = 'dukevote';
          else if (prefix === '275') targetKey = 'uncvote';
          else if (prefix === '276') targetKey = 'ncsuvote';
          else if (prefix === '282') targetKey = 'unccvote';
          else if (prefix === '274') targetKey = 'uncgvote';
          else if (prefix === '271') targetKey = 'wfuvote';
          else if (prefix === '286') targetKey = 'appstatevote';
          else if (prefix === '278') targetKey = 'ecuvote';
          else if (prefix === '284') targetKey = 'uncwvote';
          else if (prefix === '288') targetKey = 'uncavote';
        }

        if (targetKey && window.CAMPUS_LIST) {
          const found = window.CAMPUS_LIST.find(c => c.key === targetKey);
          const name = found ? found.name : targetKey;
          const url = 'https://rannbar-on.com/' + targetKey;
          setQR(url);
          zipStatus.innerHTML = `Found institution for ZIP ${val}: <strong>${name}</strong>. <a href="${url}">Open guide</a>`;
        } else {
          zipStatus.innerText = `No direct campus match found for ZIP ${val}. Please pick from the dropdown list.`;
        }
      });
    }
  }
});

