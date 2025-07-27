// Parking Booking System Service Worker
const CACHE_NAME = 'booking-pwa-v1';
const STATIC_CACHE_URLS = [
  '/',
  '/static/css/bootstrap.min.css',
  '/static/css/main.css',
  '/static/css/mobile.css',
  '/static/css/admin.css',
  '/static/js/bootstrap.bundle.min.js',
  '/static/js/fabric.min.js',
  '/static/js/auth.js',
  '/static/js/booking.js',
  '/static/js/admin.js',
  '/static/favicon-16x16.png',
  '/static/favicon-32x32.png',
  '/static/favicon-96x96.png',
  '/static/manifest.json'
];

// Install event - cache static resources
self.addEventListener('install', event => {
  console.log('Service Worker: Install');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Service Worker: Caching static files');
        return cache.addAll(STATIC_CACHE_URLS);
      })
      .catch(err => {
        console.log('Service Worker: Cache failed', err);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  console.log('Service Worker: Activate');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cache => {
          if (cache !== CACHE_NAME) {
            console.log('Service Worker: Clearing old cache', cache);
            return caches.delete(cache);
          }
        })
      );
    })
  );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', event => {
  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  // Skip requests with non-http(s) schemes
  if (!event.request.url.startsWith('http')) {
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Return cached version or fetch from network
        if (response) {
          console.log('Service Worker: Serving from cache', event.request.url);
          return response;
        }

        console.log('Service Worker: Fetching from network', event.request.url);
        return fetch(event.request)
          .then(response => {
            // Don't cache non-successful responses
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }

            // Clone the response as it can only be consumed once
            const responseToCache = response.clone();

            // Cache dynamic content selectively
            if (shouldCache(event.request.url)) {
              caches.open(CACHE_NAME)
                .then(cache => {
                  cache.put(event.request, responseToCache);
                });
            }

            return response;
          })
          .catch(err => {
            console.log('Service Worker: Fetch failed', err);
            
            // Return offline page for navigation requests
            if (event.request.mode === 'navigate') {
              return caches.match('/');
            }
            
            throw err;
          });
      })
  );
});

// Helper function to determine if URL should be cached
function shouldCache(url) {
  // Cache API responses for a short time
  if (url.includes('/api/')) {
    return false; // Don't cache API responses for now
  }
  
  // Cache static assets
  if (url.includes('/static/')) {
    return true;
  }
  
  // Cache main pages
  if (url.endsWith('/') || url.includes('index.html')) {
    return true;
  }
  
  return false;
}

// Handle background sync (for future implementation)
self.addEventListener('sync', event => {
  console.log('Service Worker: Background sync', event.tag);
  
  if (event.tag === 'booking-sync') {
    event.waitUntil(syncBookings());
  }
});

// Handle push notifications (for future implementation)
self.addEventListener('push', event => {
  console.log('Service Worker: Push received');
  
  const options = {
    body: event.data ? event.data.text() : 'New booking notification',
    icon: '/static/favicon-96x96.png',
    badge: '/static/favicon-32x32.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'explore',
        title: 'View Booking',
        icon: '/static/favicon-32x32.png'
      },
      {
        action: 'close',
        title: 'Close',
        icon: '/static/favicon-32x32.png'
      }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification('Parking Booking', options)
  );
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
  console.log('Service Worker: Notification click', event);
  
  event.notification.close();
  
  if (event.action === 'explore') {
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// Sync bookings function (placeholder for future implementation)
async function syncBookings() {
  try {
    // This would sync any pending bookings when back online
    console.log('Service Worker: Syncing bookings...');
    // Implementation would go here
  } catch (error) {
    console.log('Service Worker: Sync failed', error);
  }
}

// Update check
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
