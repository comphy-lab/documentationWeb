/**
 * Utility functions for platform-specific operations
 */

function isMacPlatform() {
  return navigator.platform.toUpperCase().indexOf('MAC') >= 0;
}

function updatePlatformSpecificElements() {
  const isMac = isMacPlatform();
  
  document.querySelectorAll('.default-theme-text').forEach(element => {
    element.style.display = isMac ? 'none' : 'inline';
  });
  
  document.querySelectorAll('.mac-theme-text').forEach(element => {
    element.style.display = isMac ? 'inline' : 'none';
  });
}

// Export functions
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    isMacPlatform,
    updatePlatformSpecificElements
  };
}
