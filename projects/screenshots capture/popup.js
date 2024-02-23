document.getElementById('capture-btn').addEventListener('click', function() {
  chrome.tabs.captureVisibleTab(null, {}, function(imageUrl) {
    if (chrome.runtime.lastError) {
      console.error(chrome.runtime.lastError.message);
      return;
    }
    // Send the image URL to the content script to be displayed or processed
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      chrome.tabs.sendMessage(tabs[0].id, {action: "DISPLAY_IMAGE", data: imageUrl});
    });
  });
});