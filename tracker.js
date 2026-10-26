/**
 * North Carolina Student Voting Platform - Usage & Campus Tracker
 * Tracks visitors and breaks down traffic by campus and event.
 * Powered by privacy-friendly GoatCounter (cookie-free, GDPR compliant).
 */
(function() {
  // Extract campus metadata from document attributes or URL path
  var campusEl = document.querySelector('[data-campus]');
  var campusName = campusEl ? campusEl.getAttribute('data-campus') : '';
  var campusKey = campusEl ? campusEl.getAttribute('data-key') : window.location.pathname.replace(/^\/|\/index\.html$|\.html$/g, '');
  var county = campusEl ? campusEl.getAttribute('data-county') : '';

  // Fallback campus inference if no data attribute
  if (!campusName && campusKey && campusKey !== 'campuses' && campusKey !== 'vote' && campusKey !== 'stats') {
    campusName = campusKey.replace('vote', '').toUpperCase();
  }

  // Analytics Configuration
  var config = {
    goatCounterCode: 'rannbaron', // Dashboard at https://rannbaron.goatcounter.com
    webhookUrl: ''                // Optional custom webhook (e.g. Google Sheets / Cloudflare Worker)
  };

  // 1. Initialize GoatCounter script asynchronously if not already in document
  try {
    if (!document.querySelector('script[data-goatcounter]')) {
      var gcScript = document.createElement('script');
      gcScript.async = true;
      gcScript.src = '//gc.zgo.at/count.js';
      gcScript.setAttribute('data-goatcounter', 'https://' + config.goatCounterCode + '.goatcounter.com/count');
      gcScript.setAttribute('data-goatcounter-settings', JSON.stringify({
        allow_local: false
      }));
      document.head.appendChild(gcScript);
    }
  } catch(e) {}

  // 2. Telemetry and Event Logging
  function logEvent(name, details) {
    var eventPath = 'campus-' + (campusKey || 'portal') + '-' + name;
    var eventTitle = (campusName || campusKey || 'Statewide Portal') + ' - ' + name;

    // Send to GoatCounter if available
    if (window.goatcounter && typeof window.goatcounter.count === 'function') {
      window.goatcounter.count({
        path: eventPath,
        title: eventTitle,
        event: true
      });
    }

    // Send to Webhook if configured
    if (config.webhookUrl) {
      try {
        var payload = JSON.stringify({
          event: name,
          campus: campusName,
          key: campusKey,
          county: county,
          path: window.location.pathname,
          referrer: document.referrer,
          timestamp: new Date().toISOString(),
          details: details || {}
        });
        if (navigator.sendBeacon) {
          navigator.sendBeacon(config.webhookUrl, payload);
        } else {
          fetch(config.webhookUrl, { method: 'POST', body: payload, mode: 'no-cors' }).catch(function(){});
        }
      } catch(e) {}
    }
  }

  // Log page load once fully ready
  window.addEventListener('load', function() {
    logEvent('visit', { title: document.title });
  });

  // Track interactions (Directions, Geolocation, Voter Guides)
  document.addEventListener('click', function(e) {
    var target = e.target.closest('a, button');
    if (!target) return;
    var href = target.getAttribute('href') || '';
    var text = (target.innerText || '').toLowerCase();

    if (href.includes('maps.google.com') || text.includes('directions')) {
      logEvent('click_directions', { dest: href });
    } else if (text.includes('detect') || text.includes('gps') || text.includes('location')) {
      logEvent('click_geolocation', {});
    } else if (href.includes('bluevoterguide') || href.includes('ivoterguide') || href.includes('vote411')) {
      logEvent('click_voter_guide', { guide: href });
    }
  });

  // Expose global tracker object
  window.NCVotingTracker = {
    logEvent: logEvent,
    getCampus: function() {
      return { name: campusName, key: campusKey, county: county };
    }
  };
})();
