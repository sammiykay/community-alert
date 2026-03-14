// PWA Install Prompt functionality
let deferredPrompt;
let installButton;

// Initialize install functionality when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Create install button
    createInstallButton();
    
    // Listen for beforeinstallprompt event
    window.addEventListener('beforeinstallprompt', (e) => {
        console.log('beforeinstallprompt event fired');
        
        // Prevent the mini-infobar from appearing on mobile
        e.preventDefault();
        
        // Store the event for later use
        deferredPrompt = e;
        
        // Show install button
        showInstallButton();
    });
    
    // Listen for app installed event
    window.addEventListener('appinstalled', (evt) => {
        console.log('PWA was installed');
        hideInstallButton();
        showInstallSuccess();
    });
});

function createInstallButton() {
    // Create install button container
    const installContainer = document.createElement('div');
    installContainer.id = 'pwa-install-container';
    installContainer.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 1000;
        display: none;
    `;
    
    // Create install button
    installButton = document.createElement('button');
    installButton.id = 'pwa-install-btn';
    installButton.innerHTML = '<i class="fas fa-download"></i> Install App';
    installButton.className = 'btn btn-primary btn-sm shadow';
    installButton.style.cssText = `
        border-radius: 25px;
        padding: 10px 20px;
        font-weight: 500;
        border: none;
        background: linear-gradient(45deg, #0d6efd, #0b5ed7);
        color: white;
        cursor: pointer;
        transition: all 0.3s ease;
    `;
    
    // Add hover effect
    installButton.addEventListener('mouseenter', function() {
        this.style.transform = 'scale(1.05)';
        this.style.boxShadow = '0 4px 12px rgba(13, 110, 253, 0.4)';
    });
    
    installButton.addEventListener('mouseleave', function() {
        this.style.transform = 'scale(1)';
        this.style.boxShadow = '0 2px 8px rgba(0,0,0,0.2)';
    });
    
    // Add click event listener
    installButton.addEventListener('click', installPWA);
    
    // Append to container and body
    installContainer.appendChild(installButton);
    document.body.appendChild(installContainer);
}

function showInstallButton() {
    const container = document.getElementById('pwa-install-container');
    if (container) {
        container.style.display = 'block';
        
        // Animate in
        setTimeout(() => {
            container.style.animation = 'slideInUp 0.3s ease-out';
        }, 100);
    }
}

function hideInstallButton() {
    const container = document.getElementById('pwa-install-container');
    if (container) {
        container.style.animation = 'slideOutDown 0.3s ease-in';
        setTimeout(() => {
            container.style.display = 'none';
        }, 300);
    }
}

async function installPWA() {
    console.log('Install button clicked');
    
    if (!deferredPrompt) {
        console.log('No deferred prompt available');
        return;
    }
    
    // Show the install prompt
    deferredPrompt.prompt();
    
    // Wait for the user to respond to the prompt
    const { outcome } = await deferredPrompt.userChoice;
    console.log(`User response to the install prompt: ${outcome}`);
    
    if (outcome === 'accepted') {
        console.log('User accepted the install prompt');
    } else {
        console.log('User dismissed the install prompt');
        // Hide button for a while if user dismisses
        hideInstallButton();
        setTimeout(showInstallButton, 300000); // Show again after 5 minutes
    }
    
    // Clear the deferred prompt
    deferredPrompt = null;
}

function showInstallSuccess() {
    // Create success message
    const successDiv = document.createElement('div');
    successDiv.innerHTML = `
        <div class="alert alert-success alert-dismissible fade show position-fixed" 
             style="top: 20px; right: 20px; z-index: 1050; min-width: 300px;">
            <i class="fas fa-check-circle"></i> 
            <strong>Success!</strong> App installed successfully!
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    document.body.appendChild(successDiv);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (successDiv.parentNode) {
            successDiv.remove();
        }
    }, 5000);
}

// Check if app is already installed
function isAppInstalled() {
    // Check if app is running in standalone mode
    return window.matchMedia('(display-mode: standalone)').matches || 
           window.navigator.standalone === true;
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInUp {
        from {
            transform: translateY(100%);
            opacity: 0;
        }
        to {
            transform: translateY(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutDown {
        from {
            transform: translateY(0);
            opacity: 1;
        }
        to {
            transform: translateY(100%);
            opacity: 0;
        }
    }
    
    #pwa-install-btn:active {
        transform: scale(0.95) !important;
    }
`;
document.head.appendChild(style);

// Don't show install button if app is already installed
if (isAppInstalled()) {
    console.log('App is already installed');
} else {
    console.log('App is not installed, install prompt will be available');
}