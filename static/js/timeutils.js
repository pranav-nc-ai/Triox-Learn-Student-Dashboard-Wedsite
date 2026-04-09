// Correct IST Time Utilities
const TrioxTime = {
    // Get current IST time as Date object
    now: function() {
        const now = new Date();
        const istOffsetMs = 5.5 * 60 * 60 * 1000;
        return new Date(now.getTime() + istOffsetMs);
    },
    
    // Format date as DD/MM/YYYY
    formatDate: function(date) {
        const d = date || this.now();
        const day = String(d.getUTCDate()).padStart(2, '0');
        const month = String(d.getUTCMonth() + 1).padStart(2, '0');
        const year = d.getUTCFullYear();
        return `${day}/${month}/${year}`;
    },
    
    // Format time as HH:MM:SS
    formatTime: function(date) {
        const d = date || this.now();
        const hours = String(d.getUTCHours()).padStart(2, '0');
        const minutes = String(d.getUTCMinutes()).padStart(2, '0');
        const seconds = String(d.getUTCSeconds()).padStart(2, '0');
        return `${hours}:${minutes}:${seconds}`;
    },
    
    // Format full datetime
    formatDateTime: function(date) {
        return `${this.formatDate(date)} ${this.formatTime(date)}`;
    },
    
    // Format relative time (time ago)
    timeAgo: function(dateString) {
        const past = new Date(dateString);
        const now = this.now();
        
        // Add IST offset to past date for comparison
        const istOffsetMs = 5.5 * 60 * 60 * 1000;
        const pastIST = new Date(past.getTime() + istOffsetMs);
        
        const seconds = Math.floor((now - pastIST) / 1000);
        
        if (seconds < 60) return 'just now';
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes} minute${minutes === 1 ? '' : 's'} ago`;
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`;
        const days = Math.floor(hours / 24);
        if (days < 7) return `${days} day${days === 1 ? '' : 's'} ago`;
        const weeks = Math.floor(days / 7);
        return `${weeks} week${weeks === 1 ? '' : 's'} ago`;
    },
    
    // Convert server timestamp to IST display
    toIST: function(timestamp) {
        if (!timestamp) return 'N/A';
        const date = new Date(timestamp);
        const istOffsetMs = 5.5 * 60 * 60 * 1000;
        const istDate = new Date(date.getTime() + istOffsetMs);
        return this.formatDateTime(istDate);
    }
};

// Make it globally available
window.TrioxTime = TrioxTime;