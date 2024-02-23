// Background script can listen to browser events if needed
chrome.runtime.onInstalled.addListener(function() {
  console.log("Screenshot Capture extension installed.");
});