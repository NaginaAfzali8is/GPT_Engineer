from PIL import ImageGrab
import datetime
import os

class ScreenshotTaker:
    def __init__(self):
        """Initialize the screenshot taker with a directory for saving screenshots."""
        self.screenshots_dir = "screenshots"
        if not os.path.exists(self.screenshots_dir):
            os.makedirs(self.screenshots_dir)

    def capture_and_save(self):
        """Capture the screen and save it to a file."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        screenshot = ImageGrab.grab()
        filename = f"{self.screenshots_dir}/screenshot_{timestamp}.png"
        screenshot.save(filename)
        print(f"Screenshot saved as {filename}")