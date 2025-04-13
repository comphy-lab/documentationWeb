// Check if we're on localhost
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
  // Load only specific Font Awesome icons for local development
  var icons = ['github', 'search', 'arrow-up-right-from-square', 'bluesky', 'youtube', 'arrow-up'];
  var link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = 'https://use.fontawesome.com/releases/v6.7.2/css/solid.css';
  link.crossOrigin = 'anonymous';
  document.head.appendChild(link);
  
  var link2 = document.createElement('link');
  link2.rel = 'stylesheet';
  link2.href = 'https://use.fontawesome.com/releases/v6.7.2/css/brands.css';
  link2.crossOrigin = 'anonymous';
  document.head.appendChild(link2);
  
  var link3 = document.createElement('link');
  link3.rel = 'stylesheet';
  link3.href = 'https://use.fontawesome.com/releases/v6.7.2/css/fontawesome.css';
  link3.crossOrigin = 'anonymous';
  document.head.appendChild(link3);
} else {
  // Use Kit for production with defer
  var script = document.createElement('script');
  script.src = 'https://kit.fontawesome.com/b1cfd9ca75.js';
  script.crossOrigin = 'anonymous';
  script.defer = true;
  document.head.appendChild(script);
}