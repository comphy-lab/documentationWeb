// Check if we're on localhost
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
  // Load only specific Font Awesome styles needed for local development
  const createStylesheet = (href) => {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = href;
    link.crossOrigin = 'anonymous';
    document.head.appendChild(link);
    return link;
  };

  // Load the base styles first, then brands and solid variants
  const FA_VERSION = '6.7.2';
  createStylesheet(`https://use.fontawesome.com/releases/v${FA_VERSION}/css/fontawesome.css`);
  createStylesheet(`https://use.fontawesome.com/releases/v${FA_VERSION}/css/brands.css`);
  createStylesheet(`https://use.fontawesome.com/releases/v${FA_VERSION}/css/solid.css`);
} else {
  // Use Kit for production with defer
  const script = document.createElement('script');
  script.src = 'https://kit.fontawesome.com/b1cfd9ca75.js';
  script.crossOrigin = 'anonymous';
  script.defer = true;
  document.head.appendChild(script);
}