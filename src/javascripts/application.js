/* global fetch, turf */
import * as cookies from './modules/cookies'

window.dptp = {
  cookies: cookies
}

// Initialize cookie banner when the module loads
if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', function() {
    cookies.showCookieBannerIfNotSetAndSetTrackingCookies();
  });
}
