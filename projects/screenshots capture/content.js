chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
  if (request.action === "DISPLAY_IMAGE") {
    // Create a new image element to display the screenshot
    var img = document.createElement('img');
    img.src = request.data;
    img.style.position = 'fixed';
    img.style.bottom = '0';
    img.style.right = '0';
    img.style.zIndex = '1000';
    img.style.border = '1px solid #ddd';
    img.style.borderRadius = '4px';
    img.style.boxShadow = '0 2px 10px rgba(0,0,0,0.2)';
    document.body.appendChild(img);
  }
});