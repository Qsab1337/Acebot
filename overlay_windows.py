"""
Overlay Window - PyQt5 Implementation (Fixed with Screenshot Toggle)
"""
import sys
import os
import ctypes
import json
import re
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QPropertyAnimation, QRect, QEasingCurve, pyqtSlot, QEvent
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
                             QTextEdit, QScrollArea, QFrame, QGraphicsOpacityEffect,
                             QPushButton, QLineEdit, QSlider, QComboBox, QDialog, QGridLayout,
                             QCheckBox)
from PyQt5.QtGui import QFont, QFontDatabase, QClipboard, QKeySequence, QFontMetrics


# Global QApplication instance
_qt_app = None


class HotkeyInput(QLineEdit):
    """Custom input field for capturing hotkeys"""
    def __init__(self, default_key=""):
        super().__init__()
        self.setPlaceholderText("Click and press keys...")
        self.setText(default_key)
        self.setReadOnly(False)
        self.captured_keys = []
        self.installEventFilter(self)
        
    def eventFilter(self, obj, event):
        """Capture and block ALL keyboard events when focused"""
        if obj == self and self.hasFocus():
            if event.type() in [QEvent.KeyPress, QEvent.KeyRelease]:
                if event.type() == QEvent.KeyPress:
                    self.handleKeyPress(event)
                return True
        return False
    
    def handleKeyPress(self, event):
        """Handle key press for hotkey capture"""
        key = event.key()
        modifiers = event.modifiers()
        
        if key in [Qt.Key_Control, Qt.Key_Alt, Qt.Key_Shift, Qt.Key_Meta]:
            return
        
        key_sequence = []
        
        if modifiers & Qt.ControlModifier:
            key_sequence.append("Ctrl")
        if modifiers & Qt.AltModifier:
            key_sequence.append("Alt")
        if modifiers & Qt.ShiftModifier:
            key_sequence.append("Shift")
        
        if key == Qt.Key_Escape:
            key_sequence.append("Esc")
        elif key == Qt.Key_Return or key == Qt.Key_Enter:
            key_sequence.append("Enter")
        elif key == Qt.Key_Space:
            key_sequence.append("Space")
        elif key == Qt.Key_Tab:
            key_sequence.append("Tab")
        elif key == Qt.Key_Backspace:
            key_sequence.append("Backspace")
        elif key == Qt.Key_Delete:
            key_sequence.append("Delete")
        elif key >= Qt.Key_F1 and key <= Qt.Key_F12:
            key_sequence.append(f"F{key - Qt.Key_F1 + 1}")
        elif 32 <= key <= 126:
            key_sequence.append(chr(key).upper())
        else:
            seq = QKeySequence(key).toString()
            if seq:
                key_sequence.append(seq)
        
        if key_sequence:
            self.setText("+".join(key_sequence))
            self.clearFocus()
    
    def mousePressEvent(self, event):
        """Clear on click and make ready for input"""
        super().mousePressEvent(event)
        self.clear()
        self.setPlaceholderText("Press new hotkey combination...")
        
    def focusOutEvent(self, event):
        """Reset placeholder when losing focus"""
        super().focusOutEvent(event)
        if not self.text():
            self.setPlaceholderText("Click and press keys...")


class SettingsDialog(QDialog):
    """Settings dialog for configuring the app"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setFixedSize(520, 800)  # Increased height for screenshot toggle
        
        if parent:
            parent.settings_dialog_open = True
        
        self.installEventFilter(self)
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.load_settings()
        
        # Get the current theme
        theme = self.settings.get('theme', 'dark')
        if parent and hasattr(parent, 'current_theme'):
            theme = parent.current_theme
        
        # Store the initial theme
        self.current_theme = theme
        
        self.create_ui()
        
        # Apply theme after UI creation
        self.apply_theme(theme)
        
        # Force a style update
        QTimer.singleShot(0, lambda: self.update_styles())
    
    def eventFilter(self, obj, event):
        """Block keyboard events from reaching the main app"""
        if event.type() in [QEvent.KeyPress, QEvent.KeyRelease]:
            for input_widget in getattr(self, 'hotkey_inputs', {}).values():
                if input_widget.hasFocus():
                    return True
        return False
    
    def create_ui(self):
        """Create all UI elements"""
        main_widget = QWidget(self)
        main_widget.setObjectName("settingsContainer")
        main_widget.setGeometry(0, 0, 520, 800)
        
        dialog_layout = QVBoxLayout(main_widget)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.setSpacing(0)
        
        # Header
        header_widget = QWidget()
        header_widget.setObjectName("headerWidget")
        header_widget.setFixedHeight(60)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 20, 20, 10)
        
        self.title_label = QLabel("Settings")
        self.title_label.setObjectName("titleLabel")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        self.close_btn_label = QLabel("×")
        self.close_btn_label.setObjectName("closeButton")
        self.close_btn_label.setCursor(Qt.PointingHandCursor)
        self.close_btn_label.mousePressEvent = lambda e: self.close()
        header_layout.addWidget(self.close_btn_label)
        
        dialog_layout.addWidget(header_widget)
        
        # Separator
        separator = QFrame()
        separator.setFrameStyle(QFrame.HLine)
        separator.setObjectName("separator")
        separator.setFixedHeight(2)
        dialog_layout.addWidget(separator)
        
        # Scroll area
        scroll_area = QScrollArea()
        scroll_area.setObjectName("scrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(25, 20, 25, 20)
        content_layout.setSpacing(20)
        
        # Model Information
        self.model_label = QLabel("AI Model:")
        self.model_label.setObjectName("sectionLabel")
        content_layout.addWidget(self.model_label)
        
        self.model_info = QLabel("🤖 Gemini 2.5 Pro (Latest)")
        self.model_info.setObjectName("infoLabel")
        self.model_info.setStyleSheet("font-size: 11pt; padding: 10px; background-color: rgba(14, 165, 233, 20); border-radius: 6px;")
        content_layout.addWidget(self.model_info)
        
        # Theme selection
        self.theme_label = QLabel("Theme:")
        self.theme_label.setObjectName("sectionLabel")
        content_layout.addWidget(self.theme_label)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        
        # Set the current theme in the combo box
        current_theme = getattr(self, 'current_theme', self.settings.get('theme', 'dark'))
        self.theme_combo.setCurrentText("Dark" if current_theme == 'dark' else "Light")
        
        # Connect AFTER setting the current value
        self.theme_combo.currentTextChanged.connect(self.preview_theme)
        self.theme_combo.setMinimumHeight(45)
        content_layout.addWidget(self.theme_combo)
        
        # Transparency with live update
        self.trans_label = QLabel("Window Transparency:")
        self.trans_label.setObjectName("sectionLabel")
        content_layout.addWidget(self.trans_label)
        
        trans_container = QHBoxLayout()
        self.trans_slider = QSlider(Qt.Horizontal)
        self.trans_slider.setMinimum(20)
        self.trans_slider.setMaximum(100)
        
        # Get current value
        current_opacity = self.settings.get('opacity', 93)
        self.trans_slider.setValue(current_opacity)
        self.trans_slider.setMinimumHeight(30)
        
        # Create value label with current value
        self.trans_value = QLabel(f"{current_opacity}%")
        self.trans_value.setObjectName("valueLabel")
        self.trans_value.setMinimumWidth(50)
        self.trans_value.setAlignment(Qt.AlignCenter)
        
        # Connect slider to update label AND window opacity in real-time
        def update_transparency(value):
            self.trans_value.setText(f"{value}%")
            # Update window opacity in real-time
            if self.parent:
                self.parent.setWindowOpacity(value / 100.0)
            # Also update the stored value
            self.settings['opacity'] = value
        
        self.trans_slider.valueChanged.connect(update_transparency)
        
        trans_container.addWidget(self.trans_slider)
        trans_container.addWidget(self.trans_value)
        content_layout.addLayout(trans_container)
        
        # Screenshot Debug Toggle
        self.screenshot_label = QLabel("Debug Features:")
        self.screenshot_label.setObjectName("sectionLabel")
        content_layout.addWidget(self.screenshot_label)
        
        screenshot_container = QHBoxLayout()
        self.screenshot_checkbox = QCheckBox("Save Screenshots (Debug)")
        self.screenshot_checkbox.setObjectName("screenshotCheckbox")
        self.screenshot_checkbox.setChecked(self.settings.get('save_screenshots', False))
        self.screenshot_checkbox.setMinimumHeight(30)
        screenshot_container.addWidget(self.screenshot_checkbox)
        
        self.screenshot_info = QLabel("(Saves to 'screenshots' folder)")
        self.screenshot_info.setObjectName("infoLabel")
        screenshot_container.addWidget(self.screenshot_info)
        screenshot_container.addStretch()
        
        content_layout.addLayout(screenshot_container)
        
        # API Key Section
        self.api_label = QLabel("Gemini API Key:")
        self.api_label.setObjectName("sectionLabel")
        content_layout.addWidget(self.api_label)
        
        # API Status Display
        self.api_status_display = QLabel("Status: Checking...")
        self.api_status_display.setObjectName("apiStatusLabel")
        content_layout.addWidget(self.api_status_display)
        
        # API input with proper height to show full text
        self.api_input = QLineEdit()
        self.api_input.setPlaceholderText("Enter your Gemini API key...")
        self.api_input.setEchoMode(QLineEdit.Password)
        self.api_input.setMinimumHeight(45)
        # Force monospace font
        mono_font = QFont("Consolas", 11)
        mono_font.setStyleHint(QFont.Monospace)
        mono_font.setFixedPitch(True)
        self.api_input.setFont(mono_font)
        content_layout.addWidget(self.api_input)
        
        self.show_api_btn = QPushButton("Show")
        self.show_api_btn.clicked.connect(self.toggle_api_visibility)
        self.show_api_btn.setFixedSize(90, 35)
        content_layout.addWidget(self.show_api_btn)
        
        self.load_api_key()
        
        # Hotkeys
        self.hotkeys_label = QLabel("Customize Hotkeys:")
        self.hotkeys_label.setObjectName("sectionLabel")
        content_layout.addWidget(self.hotkeys_label)
        
        self.info_label = QLabel("(Click on a field and press your desired key combination)")
        self.info_label.setObjectName("infoLabel")
        content_layout.addWidget(self.info_label)
        
        default_hotkeys = self.settings.get('hotkeys', {
            'add_screenshot': 'Ctrl+Alt+A',
            'analyze_multiple': 'Ctrl+Alt+M',
            'clear_all': 'Ctrl+Alt+C',
            'settings': 'Ctrl+Alt+S',
            'exit': 'Ctrl+Alt+X'
        })
        
        hotkey_data = [
            ('Add Screenshot:', 'add_screenshot'),
            ('Analyze Multiple:', 'analyze_multiple'),
            ('Clear All:', 'clear_all'),
            ('Settings:', 'settings'),
            ('Exit:', 'exit')
        ]
        
        self.hotkey_inputs = {}
        self.hotkey_labels_list = []
        
        for label_text, key in hotkey_data:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(15)
            
            label_widget = QLabel(label_text)
            label_widget.setObjectName("hotkeyLabel")
            label_widget.setFixedWidth(150)
            label_widget.setMinimumHeight(40)
            label_widget.setAlignment(Qt.AlignVCenter)
            self.hotkey_labels_list.append(label_widget)
            row_layout.addWidget(label_widget)
            
            input_widget = HotkeyInput(default_hotkeys.get(key, ''))
            input_widget.setMinimumHeight(45)
            self.hotkey_inputs[key] = input_widget
            row_layout.addWidget(input_widget)
            
            content_layout.addLayout(row_layout)
        
        content_layout.addSpacing(20)
        
        scroll_area.setWidget(scroll_content)
        dialog_layout.addWidget(scroll_area)
        
        # Buttons
        buttons_widget = QWidget()
        buttons_widget.setObjectName("buttonsWidget")
        buttons_widget.setFixedHeight(70)
        buttons_layout = QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(25, 15, 25, 20)
        buttons_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.close)
        self.cancel_btn.setMinimumSize(100, 40)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_settings)
        self.save_btn.setMinimumSize(100, 40)
        
        buttons_layout.addWidget(self.cancel_btn)
        buttons_layout.addSpacing(10)
        buttons_layout.addWidget(self.save_btn)
        
        dialog_layout.addWidget(buttons_widget)
    
    def showEvent(self, event):
        """Update values when dialog is shown"""
        super().showEvent(event)
        
        # Load and display current API key
        self.load_api_key()
        
        # Update transparency value display
        if hasattr(self, 'trans_slider') and hasattr(self, 'trans_value'):
            current_opacity = self.settings.get('opacity', 93)
            self.trans_slider.setValue(current_opacity)
            self.trans_value.setText(f"{current_opacity}%")
        
        # Update screenshot checkbox
        if hasattr(self, 'screenshot_checkbox'):
            self.screenshot_checkbox.setChecked(self.settings.get('save_screenshots', False))
        
        # Apply current theme
        if hasattr(self, 'current_theme'):
            self.apply_theme(self.current_theme)
        
        # Force update
        self.update()
        QApplication.processEvents()
    
    def closeEvent(self, event):
        """Re-enable hotkeys when dialog closes"""
        if self.parent:
            self.parent.settings_dialog_open = False
        super().closeEvent(event)
    
    def close(self):
        """Override close to reset flag"""
        if self.parent:
            self.parent.settings_dialog_open = False
        super().close()
    
    def load_settings(self):
        """Load settings from file"""
        self.settings = {
            'theme': 'dark',
            'opacity': 93,
            'save_screenshots': False,  # Default to False
            'hotkeys': {
                'add_screenshot': 'Ctrl+Alt+A',
                'analyze_multiple': 'Ctrl+Alt+M',
                'clear_all': 'Ctrl+Alt+C',
                'settings': 'Ctrl+Alt+S',
                'exit': 'Ctrl+Alt+X'
            }
        }
        try:
            # Try to load from app's data directory first
            if self.parent and hasattr(self.parent, 'app_reference'):
                app = self.parent.app_reference
                if hasattr(app, 'settings_file') and os.path.exists(app.settings_file):
                    with open(app.settings_file, 'r') as f:
                        saved_settings = json.load(f)
                        self.settings.update(saved_settings)
                    return
            
            # Fallback to local settings.json
            if os.path.exists('settings.json'):
                with open('settings.json', 'r') as f:
                    saved_settings = json.load(f)
                    self.settings.update(saved_settings)
        except:
            pass
    
    def save_settings_to_file(self):
        """Save settings to file"""
        try:
            with open('settings.json', 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Could not save settings: {e}")
    
    def apply_theme(self, theme):
        """Apply theme with PROPER colors"""
        self.current_theme = theme
        
        if theme == 'dark':
            # DARK theme - Dark background with light text
            self.bg_color = '#1a1a1a'
            self.text_color = '#FFFFFF'
            self.label_color = '#E0E0E0'
            self.muted_color = '#A0A0A0'
            self.border_color = '#404040'
            self.input_bg = '#2d2d2d'
            self.button_bg = '#404040'
            self.button_hover_bg = '#505050'
            self.accent_color = '#0ea5e9'
            self.scrollbar_bg = '#2d2d2d'
        else:
            # LIGHT theme - Light background with dark text
            self.bg_color = '#f5f5f5'
            self.text_color = '#000000'
            self.label_color = '#1a1a1a'
            self.muted_color = '#666666'
            self.border_color = '#cccccc'
            self.input_bg = '#ffffff'
            self.button_bg = '#e0e0e0'
            self.button_hover_bg = '#d0d0d0'
            self.accent_color = '#0284c7'
            self.scrollbar_bg = '#e0e0e0'
        
        self.update_styles()
    
    def update_styles(self):
        """Update all widget styles"""
        # Main stylesheet
        self.setStyleSheet(f"""
            #settingsContainer {{
                background-color: {self.bg_color};
                border: 2px solid {self.border_color};
                border-radius: 8px;
            }}
            
            #headerWidget, #buttonsWidget {{
                background-color: {self.bg_color};
            }}
            
            #titleLabel {{
                color: {self.text_color};
                font-size: 18pt;
                font-weight: bold;
            }}
            
            #closeButton {{
                color: {self.muted_color};
                font-size: 24px;
                padding: 4px;
            }}
            
            #separator {{
                background-color: {self.border_color};
                max-height: 2px;
            }}
            
            #scrollArea {{
                background: transparent;
                border: none;
            }}
            
            #scrollContent {{
                background-color: {self.bg_color};
            }}
            
            #sectionLabel {{
                color: {self.label_color};
                font-size: 11pt;
                font-weight: bold;
            }}
            
            #valueLabel {{
                color: {self.label_color};
                font-size: 10pt;
            }}
            
            #infoLabel {{
                color: {self.muted_color};
                font-size: 9pt;
                font-style: italic;
            }}
            
            #hotkeyLabel {{
                color: {self.label_color};
                font-size: 10pt;
            }}
            
            #apiStatusLabel {{
                color: {self.accent_color};
                font-size: 10pt;
                padding: 5px;
                background-color: rgba(14, 165, 233, 10);
                border-radius: 4px;
            }}
            
            #screenshotCheckbox {{
                color: {self.text_color};
                font-size: 10pt;
            }}
            
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {self.border_color};
                border-radius: 3px;
                background-color: {self.input_bg};
            }}
            
            QCheckBox::indicator:checked {{
                background-color: {self.accent_color};
                border-color: {self.accent_color};
            }}
            
            QScrollBar:vertical {{
                background: {self.scrollbar_bg};
                width: 12px;
                border-radius: 6px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.accent_color};
                border-radius: 6px;
                min-height: 30px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        
        # Theme combo
        if hasattr(self, 'theme_combo'):
            self.theme_combo.setStyleSheet(f"""
                QComboBox {{
                    background-color: {self.input_bg};
                    color: {self.text_color};
                    border: 2px solid {self.border_color};
                    padding: 8px 12px;
                    border-radius: 6px;
                    font-size: 11pt;
                    min-height: 25px;
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: 30px;
                }}
                QComboBox::down-arrow {{
                    image: none;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-top: 5px solid {self.text_color};
                    margin-right: 5px;
                }}
                QComboBox QAbstractItemView {{
                    background-color: {self.input_bg};
                    color: {self.text_color};
                    selection-background-color: {self.accent_color};
                    border: 2px solid {self.border_color};
                }}
            """)
        
        # Transparency slider
        if hasattr(self, 'trans_slider'):
            self.trans_slider.setStyleSheet(f"""
                QSlider::groove:horizontal {{
                    background: {self.border_color};
                    height: 10px;
                    border-radius: 5px;
                }}
                QSlider::handle:horizontal {{
                    background: {self.accent_color};
                    width: 20px;
                    height: 20px;
                    border-radius: 10px;
                    margin: -5px 0;
                    border: 2px solid {self.bg_color};
                }}
            """)
        
        # API input
        if hasattr(self, 'api_input'):
            self.api_input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {self.input_bg};
                    color: {self.text_color};
                    border: 2px solid {self.border_color};
                    padding: 8px 12px;
                    border-radius: 6px;
                    font-family: Consolas, 'Courier New', monospace;
                    font-size: 11pt;
                    letter-spacing: 1px;
                    min-height: 25px;
                }}
                QLineEdit:focus {{
                    border-color: {self.accent_color};
                }}
            """)
        
        # Hotkey inputs
        if hasattr(self, 'hotkey_inputs'):
            for input_widget in self.hotkey_inputs.values():
                input_widget.setStyleSheet(f"""
                    QLineEdit {{
                        background-color: {self.input_bg};
                        color: {self.text_color};
                        border: 2px solid {self.border_color};
                        padding: 8px 12px;
                        border-radius: 6px;
                        font-size: 10pt;
                        min-height: 25px;
                    }}
                    QLineEdit:focus {{
                        border-color: {self.accent_color};
                    }}
                """)
        
        # Buttons
        if hasattr(self, 'show_api_btn'):
            self.show_api_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.button_bg};
                    color: {self.text_color};
                    border: 2px solid {self.border_color};
                    padding: 8px 16px;
                    border-radius: 6px;
                    font-size: 10pt;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {self.button_hover_bg};
                }}
            """)
        
        if hasattr(self, 'save_btn'):
            self.save_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.accent_color};
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 6px;
                    font-weight: bold;
                    font-size: 11pt;
                }}
                QPushButton:hover {{
                    background-color: {self.accent_color};
                    opacity: 0.9;
                }}
            """)
        
        if hasattr(self, 'cancel_btn'):
            self.cancel_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.button_bg};
                    color: {self.text_color};
                    border: 2px solid {self.border_color};
                    padding: 12px 24px;
                    border-radius: 6px;
                    font-size: 11pt;
                }}
                QPushButton:hover {{
                    background-color: {self.button_hover_bg};
                }}
            """)
    
    def preview_theme(self, theme_text):
        """Preview theme change"""
        theme = 'dark' if theme_text == "Dark" else 'light'
        self.apply_theme(theme)
    
    def load_api_key(self):
        """Load API key from app's storage"""
        try:
            # Try to load from app's storage first
            if self.parent and hasattr(self.parent, 'app_reference'):
                app = self.parent.app_reference
                
                # Load from API manager if available
                if hasattr(app, 'api_manager'):
                    api_key = app.api_manager.load_key()
                    if api_key:
                        # Show full key in input but masked placeholder
                        masked_key = api_key[:10] + "..." + api_key[-4:] if len(api_key) > 14 else api_key
                        self.api_input.setText(api_key)
                        self.api_input.setPlaceholderText(f"Current: {masked_key}")
                        self.api_status_display.setText(f"Status: ✅ API Key Set ({masked_key})")
                        self.api_status_display.setStyleSheet("color: #10b981; font-weight: bold;")
                        return
                
                # Try current API key
                elif hasattr(app, 'current_api_key') and app.current_api_key:
                    api_key = app.current_api_key
                    masked_key = api_key[:10] + "..." + api_key[-4:] if len(api_key) > 14 else api_key
                    self.api_input.setText(api_key)
                    self.api_input.setPlaceholderText(f"Current: {masked_key}")
                    self.api_status_display.setText(f"Status: ✅ API Key Set ({masked_key})")
                    self.api_status_display.setStyleSheet("color: #10b981; font-weight: bold;")
                    return
            
            # No API key found
            self.api_status_display.setText("Status: ❌ No API Key Set")
            self.api_status_display.setStyleSheet("color: #ef4444; font-weight: bold;")
            
        except:
            self.api_status_display.setText("Status: ⚠️ Error Loading Key")
            self.api_status_display.setStyleSheet("color: #f59e0b; font-weight: bold;")
    
    def toggle_api_visibility(self):
        """Toggle API key visibility"""
        if self.api_input.echoMode() == QLineEdit.Password:
            self.api_input.setEchoMode(QLineEdit.Normal)
            self.show_api_btn.setText("Hide")
        else:
            self.api_input.setEchoMode(QLineEdit.Password)
            self.show_api_btn.setText("Show")
    
    @pyqtSlot()
    def save_settings(self):
        """Save all settings including API key"""
        # Save API key
        api_key = self.api_input.text().strip()
        if api_key:
            # Save to app's data directory
            if self.parent and hasattr(self.parent, 'app_reference'):
                app = self.parent.app_reference
                if hasattr(app, 'save_api_key'):
                    app.save_api_key(api_key)
                    print(f"[OK] API key saved and Gemini reinitialized")
        
        # Save other settings
        self.settings['theme'] = 'dark' if self.theme_combo.currentText() == "Dark" else 'light'
        self.settings['opacity'] = self.trans_slider.value()
        self.settings['save_screenshots'] = self.screenshot_checkbox.isChecked()
        
        self.settings['hotkeys'] = {}
        for key, input_widget in self.hotkey_inputs.items():
            if input_widget.text():
                self.settings['hotkeys'][key] = input_widget.text()
        
        # Save to persistent storage
        if self.parent and hasattr(self.parent, 'app_reference'):
            app = self.parent.app_reference
            if hasattr(app, 'save_settings'):
                app.save_settings(self.settings)
                # Update the app's screenshot setting
                if hasattr(app, 'capture'):
                    app.capture.debug_screenshots = self.settings['save_screenshots']
        else:
            self.save_settings_to_file()
        
        # Apply settings
        if self.parent:
            self.parent.apply_theme(self.settings['theme'])
            self.parent.setWindowOpacity(self.settings['opacity'] / 100.0)
            if hasattr(self.parent, 'app_reference') and self.parent.app_reference:
                self.parent.app_reference.update_hotkeys(self.settings.get('hotkeys', {}))
        
        print(f"[OK] All settings applied")
        print(f"[OK] Save screenshots: {self.settings['save_screenshots']}")
        self.close()


class OverlayWindow(QWidget):
    def __init__(self):
        global _qt_app
        
        # Create QApplication in main thread if needed
        if QApplication.instance() is None:
            _qt_app = QApplication([])
        else:
            _qt_app = QApplication.instance()
        
        self.app = _qt_app
        
        super().__init__()
        
        self.visible = False
        self.app_reference = None
        self.capture_protection_active = False
        self.settings_dialog_open = False
        
        self.load_settings()
        
        self.setWindowTitle("AI Assistant")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        self.collapsed_height = 145  # Reduced height (no API status)
        self.expanded_height = 320   # Reduced height (no API status)
        self.resize(420, self.collapsed_height)
        screen = self.app.primaryScreen().geometry()
        self.move(screen.width() - 445, 25)
        
        self.setWindowOpacity(self.settings.get('opacity', 93) / 100.0)
        
        self.content_shown = False
        self.current_answer = ""
        
        self.current_theme = self.settings.get('theme', 'dark')
        self.apply_theme(self.current_theme)
        
        self.setup_ui()
        
        self.drag_position = None
        self.current_status = "Ready"
        
        self.hide()
    
    def load_settings(self):
        """Load settings from file"""
        self.settings = {
            'theme': 'dark',
            'opacity': 93,
            'save_screenshots': False,  # Default to False
            'hotkeys': {
                'add_screenshot': 'Ctrl+Alt+A',
                'analyze_multiple': 'Ctrl+Alt+M',
                'clear_all': 'Ctrl+Alt+C',
                'settings': 'Ctrl+Alt+S',
                'exit': 'Ctrl+Alt+X'
            }
        }
        try:
            # Try to load from app's data directory
            if hasattr(self, 'app_reference') and self.app_reference:
                if hasattr(self.app_reference, 'settings_file') and os.path.exists(self.app_reference.settings_file):
                    with open(self.app_reference.settings_file, 'r') as f:
                        saved_settings = json.load(f)
                        self.settings.update(saved_settings)
                    return
            
            # Fallback to local settings.json
            if os.path.exists('settings.json'):
                with open('settings.json', 'r') as f:
                    saved_settings = json.load(f)
                    self.settings.update(saved_settings)
        except:
            pass
    
    def apply_theme(self, theme):
        """Apply color theme"""
        self.current_theme = theme
        
        if theme == 'dark':
            self.bg_color = 'rgba(13, 13, 13, 237)'
            self.text_color = '#ffffff'
            self.muted_color = '#888888'
            self.accent_color = '#0ea5e9'
            self.border_color = 'rgba(26, 26, 26, 255)'
            self.input_bg = 'rgba(42, 42, 42, 255)'
        else:
            self.bg_color = 'rgba(245, 245, 245, 237)'
            self.text_color = '#1a1a1a'
            self.muted_color = '#666666'
            self.accent_color = '#0284c7'
            self.border_color = 'rgba(200, 200, 200, 255)'
            self.input_bg = 'rgba(255, 255, 255, 255)'
        
        if hasattr(self, 'main_container'):
            self.update_theme_styles()
    
    def update_theme_styles(self):
        """Update all styles based on current theme"""
        self.setStyleSheet(f"""
            QWidget#mainContainer {{
                background-color: {self.bg_color};
                border: 1px solid {self.border_color};
            }}
            QLabel {{
                color: {self.text_color};
            }}
            QTextEdit {{
                background-color: {self.input_bg if self.current_theme == 'light' else self.bg_color};
                color: {self.text_color};
                border: 1px solid {self.border_color};
                padding: 10px;
            }}
            QScrollBar:vertical {{
                background: {self.border_color};
                width: 12px;
                border-radius: 6px;
                margin: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.accent_color};
                border-radius: 6px;
                min-height: 30px;
            }}
        """)
        
        if hasattr(self, 'capture_label'):
            self.capture_label.setStyleSheet(f"color: {self.accent_color}; font-weight: bold; font-size: 9pt;")
        
        if hasattr(self, 'instruction_labels'):
            for label in self.instruction_labels:
                label.setStyleSheet(f"color: {self.text_color}; font-family: Consolas, monospace; font-size: 10pt;")
        
        if hasattr(self, 'separator'):
            self.separator.setStyleSheet(f"background-color: {self.border_color}; max-height: 1px;")
        
        if hasattr(self, 'close_btn'):
            self.close_btn.setStyleSheet(f"color: {self.muted_color}; font-size: 18px; padding: 4px;")
        
        if hasattr(self, 'settings_btn'):
            self.settings_btn.setStyleSheet(f"color: {self.muted_color}; font-size: 16px; padding: 4px;")
    
    def setup_ui(self):
        """Create the UI layout"""
        self.main_container = QWidget(self)
        self.main_container.setObjectName("mainContainer")
        self.main_container.setGeometry(0, 0, 420, self.collapsed_height)
        
        self.layout = QVBoxLayout(self.main_container)
        self.layout.setContentsMargins(1, 1, 1, 1)
        self.layout.setSpacing(0)
        
        header = QWidget()
        header.setFixedHeight(28)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 0, 10, 0)
        
        self.settings_btn = QLabel("⚙")
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.mousePressEvent = self.open_settings
        header_layout.addWidget(self.settings_btn)
        
        header_layout.addStretch()
        
        self.close_btn = QLabel("×")
        self.close_btn.setCursor(Qt.PointingHandCursor)
        header_layout.addWidget(self.close_btn)
        
        self.layout.addWidget(header)
        
        instructions_widget = QWidget()
        instructions_widget.setFixedHeight(110)  # Reduced height (no API status)
        instructions_layout = QVBoxLayout(instructions_widget)
        instructions_layout.setContentsMargins(12, 4, 12, 4)
        instructions_layout.setSpacing(2)
        
        self.capture_label = QLabel("CAPTURE → Hold right mouse button (2 sec)")
        instructions_layout.addWidget(self.capture_label)
        
        self.separator = QFrame()
        self.separator.setFrameStyle(QFrame.HLine)
        instructions_layout.addWidget(self.separator)
        
        self.instruction_labels = []
        hotkeys = self.settings.get('hotkeys', {})
        shortcuts_text = [
            f"{hotkeys.get('add_screenshot', 'Ctrl+Alt+A')} = Save screenshot",
            f"{hotkeys.get('analyze_multiple', 'Ctrl+Alt+M')} = Check all saved",
            f"{hotkeys.get('clear_all', 'Ctrl+Alt+C')} = Clear saved",
            f"{hotkeys.get('settings', 'Ctrl+Alt+S')} = Settings",
            f"{hotkeys.get('exit', 'Ctrl+Alt+X')} = Exit program"
        ]
        
        for shortcut in shortcuts_text:
            shortcut_label = QLabel(shortcut)
            self.instruction_labels.append(shortcut_label)
            instructions_layout.addWidget(shortcut_label)
        
        # NO API STATUS LABEL HERE - REMOVED
        
        self.layout.addWidget(instructions_widget)
        
        self.content_container = QWidget()
        content_layout = QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        content_inner = QWidget()
        content_inner_layout = QHBoxLayout(content_inner)
        content_inner_layout.setContentsMargins(0, 0, 0, 0)
        content_inner_layout.setSpacing(0)
        
        self.content_text = QTextEdit()
        self.content_text.setReadOnly(True)
        self.content_text.setPlainText("")
        self.content_text.setFont(QFont("Segoe UI", 11))
        self.content_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.content_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        content_inner_layout.addWidget(self.content_text)
        
        self.copy_btn = QPushButton("📋")
        self.copy_btn.clicked.connect(self.copy_answer)
        self.copy_btn.setFixedSize(25, 25)
        self.copy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(14, 165, 233, 180);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 12px;
                margin: 3px;
            }}
            QPushButton:hover {{
                background-color: rgba(14, 165, 233, 230);
            }}
        """)
        self.copy_btn.setToolTip("Copy answer")
        self.copy_btn.hide()
        
        content_layout.addWidget(content_inner)
        
        self.copy_btn.setParent(self.content_container)
        self.copy_btn.raise_()
        
        self.content_container.hide()
        self.layout.addWidget(self.content_container)
        
        self.close_btn.mousePressEvent = self.close_application
        
        self.setup_animations()
        self.update_theme_styles()
    
    def open_settings(self, event=None):
        """Open settings dialog - THIS IS THE MISSING METHOD"""
        self.settings_dialog_open = True
        settings = SettingsDialog(self)
        settings.exec_()
        self.settings_dialog_open = False
        self.load_settings()
        self.update_hotkey_display()
    
    def update_hotkey_display(self):
        """Update displayed hotkeys"""
        hotkeys = self.settings.get('hotkeys', {})
        shortcuts_text = [
            f"{hotkeys.get('add_screenshot', 'Ctrl+Alt+A')} = Save screenshot",
            f"{hotkeys.get('analyze_multiple', 'Ctrl+Alt+M')} = Check all saved",
            f"{hotkeys.get('clear_all', 'Ctrl+Alt+C')} = Clear saved",
            f"{hotkeys.get('settings', 'Ctrl+Alt+S')} = Settings",
            f"{hotkeys.get('exit', 'Ctrl+Alt+X')} = Exit program"
        ]
        
        for i, label in enumerate(self.instruction_labels):
            if i < len(shortcuts_text):
                label.setText(shortcuts_text[i])
    
    def setup_animations(self):
        """Setup animations"""
        self.window_animation = QPropertyAnimation(self, b"geometry")
        self.window_animation.setDuration(400)
        self.window_animation.setEasingCurve(QEasingCurve.OutBounce)
        
        self.container_animation = QPropertyAnimation(self.main_container, b"geometry")
        self.container_animation.setDuration(400)
        self.container_animation.setEasingCurve(QEasingCurve.OutBounce)
        
        self.opacity_effect = QGraphicsOpacityEffect()
        self.content_container.setGraphicsEffect(self.opacity_effect)
        self.opacity_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_animation.setDuration(300)
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
    
    def copy_answer(self):
        """Copy only the answer text to clipboard"""
        if self.current_answer:
            answer_only = self.extract_answer_only(self.current_answer)
            
            clipboard = QApplication.clipboard()
            clipboard.setText(answer_only)
            
            original_text = self.copy_btn.text()
            self.copy_btn.setText("✓")
            self.copy_btn.setStyleSheet(self.copy_btn.styleSheet().replace("rgba(14, 165, 233, 180)", "rgba(34, 197, 94, 180)"))
            
            QTimer.singleShot(1000, lambda: self.reset_copy_button(original_text))
    
    def extract_answer_only(self, full_text):
        """Extract just the answer from the full response"""
        if not full_text:
            return ""
        
        answer_match = re.search(r'Answer:\s*(.+?)(?:\n|$)', full_text, re.IGNORECASE | re.DOTALL)
        if answer_match:
            return answer_match.group(1).strip()
        
        letter_match = re.search(r'\b([A-D])\b', full_text)
        if letter_match:
            return letter_match.group(1)
        
        option_match = re.search(r'([A-D])[\)\.]', full_text)
        if option_match:
            return option_match.group(1)
        
        first_line = full_text.split('\n')[0].strip()
        return first_line if first_line else full_text.strip()
    
    def reset_copy_button(self, original_text):
        """Reset copy button to original state"""
        if hasattr(self, 'copy_btn'):
            self.copy_btn.setText(original_text)
            self.copy_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(14, 165, 233, 180);
                    color: white;
                    border: none;
                    border-radius: 12px;
                    font-size: 12px;
                    margin: 3px;
                }}
                QPushButton:hover {{
                    background-color: rgba(14, 165, 233, 230);
                }}
            """)
    
    def update_capture_status(self, text):
        """Update capture status"""
        if hasattr(self, 'capture_label'):
            self.capture_label.setText(text)
            if "Holding..." in text or "Ready..." in text:
                self.capture_label.setStyleSheet(f"color: #fbbf24; font-weight: bold; font-size: 9pt;")
            elif "Capturing now!" in text:
                self.capture_label.setStyleSheet(f"color: #10b981; font-weight: bold; font-size: 9pt;")
            elif "Getting Answer" in text:
                self.capture_label.setStyleSheet(f"color: #a78bfa; font-weight: bold; font-size: 9pt;")
            else:
                self.capture_label.setStyleSheet(f"color: {self.accent_color}; font-weight: bold; font-size: 9pt;")
    
    def update_text(self, text):
        """Update content text"""
        if "[Getting Answer" in text:
            if not self.content_shown:
                self.show_content_area()
                QTimer.singleShot(150, lambda: self.content_text.setPlainText("🤖 Getting Answer..."))
            else:
                self.content_text.setPlainText("🤖 Getting Answer...")
            self.copy_btn.hide()
            return
        elif "Clear" in text:
            self.hide_content_area()
            self.current_answer = ""
            return
        elif "[Screenshot" in text and "added]" in text:
            if not self.content_shown:
                self.show_content_area()
                QTimer.singleShot(150, lambda: self.content_text.setPlainText(text))
            else:
                self.content_text.setPlainText(text)
            self.copy_btn.hide()
            return
        elif "[Preparing" in text:
            if not self.content_shown:
                self.show_content_area()
                QTimer.singleShot(150, lambda: self.content_text.setPlainText(text))
            else:
                self.content_text.setPlainText(text)
            self.copy_btn.hide()
            return
        
        text = text.replace("[OK]", "").strip()
        text = text.replace("[WARNING]", "").strip()
        text = text.replace("[ERROR]", "").strip()
        text = text.replace("[Capturing...]", "").strip()
        text = text.replace("[Analyzing...]", "").strip()
        
        if text and not text.startswith("["):
            self.current_answer = text
            if not self.content_shown:
                self.show_content_area()
                QTimer.singleShot(150, lambda: self._show_answer_with_button(text))
            else:
                self._show_answer_with_button(text)
        
        if not self.visible:
            self.show()
        
        self.raise_()
        self.activateWindow()
    
    def _show_answer_with_button(self, text):
        """Show answer with copy button"""
        self.content_text.setPlainText(text)
        QTimer.singleShot(50, lambda: self._position_copy_button())
    
    def _position_copy_button(self):
        """Position copy button"""
        if self.content_container.isVisible():
            self.copy_btn.show()
            self.copy_btn.raise_()
            btn_x = self.content_container.width() - 30
            self.copy_btn.move(btn_x, 5)
    
    def show_content_area(self):
        """Show content area with animation"""
        if not self.content_shown:
            self.content_shown = True
            self.content_container.show()
            self.opacity_effect.setOpacity(0.0)
            
            current_x = self.x()
            current_y = self.y()
            
            self.window_animation.setStartValue(QRect(current_x, current_y, 420, self.collapsed_height))
            self.window_animation.setEndValue(QRect(current_x, current_y, 420, self.expanded_height))
            
            self.container_animation.setStartValue(QRect(0, 0, 420, self.collapsed_height))
            self.container_animation.setEndValue(QRect(0, 0, 420, self.expanded_height))
            
            self.window_animation.start()
            self.container_animation.start()
            QTimer.singleShot(100, lambda: self.opacity_animation.start())
    
    def hide_content_area(self):
        """Hide content area with animation"""
        if self.content_shown:
            self.content_shown = False
            self.copy_btn.hide()
            
            if hasattr(self, 'opacity_effect'):
                self.opacity_effect.setOpacity(1.0)
            
            current_x = self.x()
            current_y = self.y()
            
            self.window_animation.setStartValue(QRect(current_x, current_y, 420, self.expanded_height))
            self.window_animation.setEndValue(QRect(current_x, current_y, 420, self.collapsed_height))
            
            self.container_animation.setStartValue(QRect(0, 0, 420, self.expanded_height))
            self.container_animation.setEndValue(QRect(0, 0, 420, self.collapsed_height))
            
            try:
                self.window_animation.finished.disconnect()
            except:
                pass
            
            self.window_animation.finished.connect(lambda: self.content_container.hide() if hasattr(self, 'content_container') else None)
            self.window_animation.start()
            self.container_animation.start()
    
    def resizeEvent(self, event):
        """Handle resize"""
        super().resizeEvent(event)
        if hasattr(self, 'copy_btn') and self.copy_btn.isVisible():
            btn_x = self.content_container.width() - 30
            self.copy_btn.move(btn_x, 5)
    
    def mousePressEvent(self, event):
        """Handle mouse press"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Handle window dragging"""
        if event.buttons() == Qt.LeftButton and self.drag_position:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def showEvent(self, event):
        """Apply screen capture protection"""
        super().showEvent(event)
        
        try:
            hwnd = int(self.winId())
            WDA_EXCLUDEFROMCAPTURE = 0x00000011
            
            result = ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
            
            if result:
                print("[OK] Window HIDDEN from captures - Protection Active")
                self.capture_protection_active = True
            else:
                WDA_MONITOR = 0x00000001
                result = ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_MONITOR)
                if result:
                    print("[OK] Window HIDDEN from captures - Monitor Mode")
                    self.capture_protection_active = True
                else:
                    self.capture_protection_active = False
        except Exception as e:
            self.capture_protection_active = False
        
        self.raise_()
        self.activateWindow()
    
    def close_application(self, event=None):
        """Close application"""
        if self.app_reference:
            self.app_reference.running = False
        
        if self.app:
            self.app.quit()
        
        sys.exit(0)
    
    def show(self):
        """Show window"""
        super().show()
        self.visible = True
        self.raise_()
        self.activateWindow()
    
    def hide(self):
        """Hide window"""
        super().hide()
        self.visible = False
    
    def toggle(self):
        """Toggle visibility"""
        if self.visible:
            self.hide()
        else:
            self.show()
    
    def destroy(self):
        """Clean shutdown"""
        self.close()
    
    @property
    def root(self):
        return self
    
    def update(self):
        if self.app:
            self.app.processEvents()
    
    def winfo_exists(self):
        return not self.isHidden()
    
    def lift(self):
        self.raise_()
        self.activateWindow()