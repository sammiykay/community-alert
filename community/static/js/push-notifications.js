/**
 * Push Notification Service for Community Alert System
 * Uses Firebase Cloud Messaging (FCM) for web push notifications
 */

class PushNotificationService {
    constructor() {
        this.messaging = null;
        this.currentToken = null;
        this.isSupported = false;
        this.isPermissionGranted = false;
        
        this.init();
    }
    
    async init() {
        try {
            // Check if Firebase is loaded and service worker is supported
            if (typeof firebase === 'undefined' || !('serviceWorker' in navigator)) {
                console.warn('Push notifications not supported: Firebase or Service Worker unavailable');
                return;
            }
            
            // Initialize Firebase (config should be loaded in template)
            if (window.firebaseConfig) {
                if (!firebase.apps.length) {
                    firebase.initializeApp(window.firebaseConfig);
                }
                
                this.messaging = firebase.messaging();
                this.isSupported = true;
                
                // Set up background message handler
                this.setupMessageHandlers();
                
                console.log('Push notification service initialized');
            } else {
                console.warn('Firebase config not found');
            }
        } catch (error) {
            console.error('Failed to initialize push notification service:', error);
        }
    }
    
    setupMessageHandlers() {
        // Handle foreground messages
        this.messaging.onMessage((payload) => {
            console.log('Foreground message received:', payload);
            this.showNotification(payload);
        });
        
        // Handle token refresh
        this.messaging.onTokenRefresh(() => {
            console.log('Token refreshed');
            this.requestPermissionAndGetToken();
        });
    }
    
    async requestPermissionAndGetToken() {
        try {
            if (!this.isSupported) {
                throw new Error('Push notifications not supported');
            }
            
            // Request notification permission
            const permission = await Notification.requestPermission();
            
            if (permission === 'granted') {
                console.log('Notification permission granted');
                this.isPermissionGranted = true;
                
                // Get FCM token
                const token = await this.messaging.getToken({
                    vapidKey: window.vapidKey // Should be set in template
                });
                
                if (token) {
                    console.log('FCM token received:', token);
                    this.currentToken = token;
                    
                    // Register device with backend
                    await this.registerDevice(token);
                    
                    return token;
                } else {
                    console.warn('No registration token available');
                    return null;
                }
            } else {
                console.warn('Notification permission denied');
                this.isPermissionGranted = false;
                return null;
            }
        } catch (error) {
            console.error('Failed to get notification permission/token:', error);
            return null;
        }
    }
    
    async registerDevice(token) {
        try {
            const deviceInfo = this.getDeviceInfo();
            
            const response = await fetch('/push/register/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify({
                    device_token: token,
                    device_type: 'web',
                    device_name: deviceInfo
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                console.log('Device registered successfully:', result.message);
                localStorage.setItem('fcm_token', token);
                return true;
            } else {
                console.error('Failed to register device:', result.error);
                return false;
            }
        } catch (error) {
            console.error('Device registration error:', error);
            return false;
        }
    }
    
    async unregisterDevice() {
        try {
            if (!this.currentToken) {
                console.warn('No token to unregister');
                return true;
            }
            
            const response = await fetch('/push/unregister/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify({
                    device_token: this.currentToken
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                console.log('Device unregistered successfully');
                localStorage.removeItem('fcm_token');
                this.currentToken = null;
                return true;
            } else {
                console.error('Failed to unregister device:', result.error);
                return false;
            }
        } catch (error) {
            console.error('Device unregistration error:', error);
            return false;
        }
    }
    
    showNotification(payload) {
        const { notification, data } = payload;
        
        // Create notification options
        const options = {
            body: notification.body,
            icon: '/static/images/notification-icon.png',
            badge: '/static/images/badge-icon.png',
            tag: data?.alert_id || 'general',
            requireInteraction: true,
            actions: [
                {
                    action: 'view',
                    title: 'View Alert',
                    icon: '/static/images/view-icon.png'
                },
                {
                    action: 'dismiss',
                    title: 'Dismiss',
                    icon: '/static/images/dismiss-icon.png'
                }
            ],
            data: data
        };
        
        // Show notification
        if (Notification.permission === 'granted') {
            const notif = new Notification(notification.title, options);
            
            notif.onclick = () => {
                // Handle notification click
                if (data?.url) {
                    window.open(data.url, '_blank');
                }
                notif.close();
            };
            
            // Auto-close after 10 seconds
            setTimeout(() => {
                notif.close();
            }, 10000);
        }
    }
    
    async testNotification() {
        try {
            const response = await fetch('/test-notification/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                }
            });
            
            const result = await response.json();
            return result;
        } catch (error) {
            console.error('Test notification error:', error);
            return { success: false, error: error.message };
        }
    }
    
    getDeviceInfo() {
        const browser = this.getBrowserInfo();
        const os = this.getOSInfo();
        return `${browser} on ${os}`;
    }
    
    getBrowserInfo() {
        const ua = navigator.userAgent;
        if (ua.includes('Chrome')) return 'Chrome';
        if (ua.includes('Firefox')) return 'Firefox';
        if (ua.includes('Safari')) return 'Safari';
        if (ua.includes('Edge')) return 'Edge';
        return 'Unknown Browser';
    }
    
    getOSInfo() {
        const ua = navigator.userAgent;
        if (ua.includes('Windows')) return 'Windows';
        if (ua.includes('Mac')) return 'macOS';
        if (ua.includes('Linux')) return 'Linux';
        if (ua.includes('Android')) return 'Android';
        if (ua.includes('iOS')) return 'iOS';
        return 'Unknown OS';
    }
    
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
    
    // Public API methods
    async enableNotifications() {
        const token = await this.requestPermissionAndGetToken();
        return token !== null;
    }
    
    async disableNotifications() {
        return await this.unregisterDevice();
    }
    
    isEnabled() {
        return this.isPermissionGranted && this.currentToken !== null;
    }
    
    getStatus() {
        return {
            supported: this.isSupported,
            permissionGranted: this.isPermissionGranted,
            tokenAvailable: this.currentToken !== null,
            currentToken: this.currentToken
        };
    }
}

// Global instance
window.pushNotificationService = new PushNotificationService();

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Check if user wants push notifications enabled
    const savedToken = localStorage.getItem('fcm_token');
    if (savedToken && window.pushNotificationService.isSupported) {
        // Try to restore previous registration
        window.pushNotificationService.requestPermissionAndGetToken();
    }
});

// Export for use in templates
window.enablePushNotifications = async function() {
    const success = await window.pushNotificationService.enableNotifications();
    if (success) {
        showToast('Push notifications enabled successfully!', 'success');
        updateNotificationUI();
    } else {
        showToast('Failed to enable push notifications', 'error');
    }
    return success;
};

window.disablePushNotifications = async function() {
    const success = await window.pushNotificationService.disableNotifications();
    if (success) {
        showToast('Push notifications disabled', 'info');
        updateNotificationUI();
    } else {
        showToast('Failed to disable push notifications', 'error');
    }
    return success;
};

window.testPushNotifications = async function() {
    const result = await window.pushNotificationService.testNotification();
    
    if (result.success) {
        showToast(result.message, 'success');
        
        // Show detailed results if available
        if (result.results) {
            const details = result.results.join('<br>');
            setTimeout(() => {
                showDetailedToast('Test Results', details);
            }, 1000);
        }
    } else {
        showToast(`Test failed: ${result.error}`, 'error');
    }
    
    return result;
};

function updateNotificationUI() {
    const status = window.pushNotificationService.getStatus();
    
    // Update UI elements based on status
    const pushToggle = document.getElementById('push-notification-toggle');
    const statusText = document.getElementById('push-status-text');
    
    if (pushToggle) {
        pushToggle.checked = status.permissionGranted && status.tokenAvailable;
    }
    
    if (statusText) {
        if (!status.supported) {
            statusText.textContent = 'Not supported';
            statusText.className = 'text-muted';
        } else if (status.permissionGranted && status.tokenAvailable) {
            statusText.textContent = 'Enabled';
            statusText.className = 'text-success';
        } else {
            statusText.textContent = 'Disabled';
            statusText.className = 'text-warning';
        }
    }
}

// Utility functions for notifications
function showToast(message, type = 'info') {
    // Implementation depends on your toast system
    // This is a basic version
    const toast = document.createElement('div');
    toast.className = `alert alert-${type === 'error' ? 'danger' : type} toast-notification`;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        padding: 12px 20px;
        border-radius: 6px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    toast.innerHTML = `<strong>${type.charAt(0).toUpperCase() + type.slice(1)}:</strong> ${message}`;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 5000);
}

function showDetailedToast(title, content) {
    const toast = document.createElement('div');
    toast.className = 'alert alert-info toast-notification-detailed';
    toast.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        z-index: 9999;
        max-width: 400px;
        padding: 15px 20px;
        border-radius: 6px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    toast.innerHTML = `
        <h6>${title}</h6>
        <div style="font-size: 0.9em;">${content}</div>
        <button onclick="this.parentElement.remove()" style="float: right; background: none; border: none; font-size: 1.2em;">&times;</button>
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        if (toast.parentElement) {
            toast.remove();
        }
    }, 10000);
}