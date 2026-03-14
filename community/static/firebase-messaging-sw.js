/**
 * Firebase Messaging Service Worker
 * Handles background push notifications for Community Alert System
 */

// Import Firebase scripts
importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.0.0/firebase-messaging-compat.js');

// Initialize Firebase with config (this will be set by the main app)
let firebaseConfig = null;

// Listen for messages from main thread to set config
self.addEventListener('message', event => {
    if (event.data && event.data.type === 'FIREBASE_CONFIG') {
        firebaseConfig = event.data.config;
        initializeFirebase();
    }
});

function initializeFirebase() {
    if (firebaseConfig && !firebase.apps.length) {
        firebase.initializeApp(firebaseConfig);
        
        const messaging = firebase.messaging();
        
        // Handle background messages
        messaging.onBackgroundMessage(function(payload) {
            console.log('Background message received:', payload);
            
            const { notification, data } = payload;
            
            // Customize notification
            const notificationTitle = notification.title || 'Community Alert';
            const notificationOptions = {
                body: notification.body || 'New alert notification',
                icon: '/static/images/notification-icon.png',
                badge: '/static/images/badge-icon.png',
                tag: data?.alert_id || `alert-${Date.now()}`,
                requireInteraction: true,
                actions: [
                    {
                        action: 'view',
                        title: 'View Alert'
                    },
                    {
                        action: 'dismiss',
                        title: 'Dismiss'
                    }
                ],
                data: {
                    url: data?.url || '/alerts/',
                    alert_id: data?.alert_id,
                    type: data?.type || 'alert_notification',
                    timestamp: Date.now()
                }
            };
            
            // Show notification
            return self.registration.showNotification(notificationTitle, notificationOptions);
        });
    }
}

// Handle notification clicks
self.addEventListener('notificationclick', function(event) {
    console.log('Notification click received:', event);
    
    event.notification.close();
    
    const action = event.action;
    const data = event.notification.data;
    
    if (action === 'dismiss') {
        // Just close the notification
        return;
    }
    
    // Default action or 'view' action
    let urlToOpen = '/';
    
    if (data && data.url) {
        urlToOpen = data.url;
    } else if (data && data.alert_id) {
        urlToOpen = `/alerts/${data.alert_id}/`;
    }
    
    // Open URL in existing tab or new tab
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
            // Check if there's already a tab open for this URL
            for (let client of clientList) {
                if (client.url.includes(urlToOpen) && 'focus' in client) {
                    return client.focus();
                }
            }
            
            // If no existing tab, open new one
            if (clients.openWindow) {
                const fullUrl = self.location.origin + urlToOpen;
                return clients.openWindow(fullUrl);
            }
        })
    );
});

// Handle notification close
self.addEventListener('notificationclose', function(event) {
    console.log('Notification closed:', event.notification.tag);
    
    // Optional: Send analytics or tracking data
    const data = event.notification.data;
    if (data && data.alert_id) {
        // Could send a request to track notification dismissal
        // fetch('/api/notifications/dismissed/', { ... });
    }
});

// Handle push events (fallback for older browsers)
self.addEventListener('push', function(event) {
    console.log('Push event received:', event);
    
    if (event.data) {
        try {
            const payload = event.data.json();
            console.log('Push payload:', payload);
            
            const { notification, data } = payload;
            
            const notificationTitle = notification?.title || 'Community Alert';
            const notificationOptions = {
                body: notification?.body || 'New notification',
                icon: '/static/images/notification-icon.png',
                badge: '/static/images/badge-icon.png',
                tag: data?.alert_id || `push-${Date.now()}`,
                data: data
            };
            
            event.waitUntil(
                self.registration.showNotification(notificationTitle, notificationOptions)
            );
        } catch (error) {
            console.error('Error parsing push payload:', error);
        }
    }
});

// Service worker install
self.addEventListener('install', function(event) {
    console.log('Firebase messaging service worker installed');
    self.skipWaiting();
});

// Service worker activate
self.addEventListener('activate', function(event) {
    console.log('Firebase messaging service worker activated');
    event.waitUntil(self.clients.claim());
});

// Handle messages from clients
self.addEventListener('message', function(event) {
    console.log('Service worker received message:', event.data);
    
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

console.log('Firebase messaging service worker loaded');