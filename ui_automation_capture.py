"""
UI Automation for extracting text when screenshots fail
Works as fallback when screen capture is blocked
"""
import win32gui
import win32con


class UIAutomationCapture:
    def __init__(self):
        print("UI Automation fallback initialized")
    
    def get_active_window_text(self):
        """Extract all text from active window using Windows API"""
        try:
            # Get active window
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return "No active window"
            
            # Get window title
            window_title = win32gui.GetWindowText(hwnd)
            
            # Get all child windows
            child_windows = []
            
            def enum_child_callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    # Get window text
                    text = win32gui.GetWindowText(hwnd)
                    if text:
                        windows.append(text)
                    
                    # Try to get text using SendMessage
                    try:
                        length = win32gui.SendMessage(hwnd, win32con.WM_GETTEXTLENGTH, 0, 0)
                        if length > 0:
                            buffer = win32gui.PyMakeBuffer(length + 1)
                            win32gui.SendMessage(hwnd, win32con.WM_GETTEXT, length + 1, buffer)
                            text = buffer[:length]
                            if text and text not in windows:
                                windows.append(text)
                    except:
                        pass
                    
                return True
            
            # Enumerate child windows
            win32gui.EnumChildWindows(hwnd, enum_child_callback, child_windows)
            
            # Combine all text
            all_text = [window_title] + child_windows
            all_text = [t for t in all_text if t and len(t) > 3]
            
            # Remove duplicates while preserving order
            seen = set()
            unique_text = []
            for text in all_text:
                if text not in seen:
                    seen.add(text)
                    unique_text.append(text)
            
            combined = '\n'.join(unique_text)
            
            # If very little text found, try clipboard as last resort
            if len(combined) < 50:
                try:
                    import win32clipboard
                    win32clipboard.OpenClipboard()
                    if win32clipboard.IsClipboardFormatAvailable(win32con.CF_TEXT):
                        clip_text = win32clipboard.GetClipboardData()
                        if clip_text and len(clip_text) > len(combined):
                            combined = f"[From clipboard]\n{clip_text}"
                    win32clipboard.CloseClipboard()
                except:
                    pass
            
            return combined if combined else "No text found"
            
        except Exception as e:
            print(f"Text extraction error: {e}")
            return "Text extraction failed"
