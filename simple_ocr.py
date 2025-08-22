"""
Simple OCR - Enhanced for nursing questions with PSM 6 priority
"""
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import os
import re


class SimpleOCR:
    def __init__(self):
        # Set Tesseract path for Windows
        tesseract_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            r'C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe'.format(os.environ.get('USERNAME', '')),
            r'C:\tesseract\tesseract.exe'
        ]
        
        # Find Tesseract
        tesseract_found = False
        for path in tesseract_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                tesseract_found = True
                print(f"Tesseract found at: {path}")
                break
        
        if not tesseract_found:
            print("[WARNING] Tesseract not found! OCR will not work.")
            print("Please install from: https://github.com/UB-Mannheim/tesseract/wiki")
    
    def extract_text(self, image):
        """Extract text with preprocessing for nursing content"""
        try:
            # Enhanced preprocessing for better OCR accuracy
            processed_img = self._preprocess_for_nursing(image)
            
            # Try PSM 6 first (uniform block - best for exam questions)
            try:
                text = pytesseract.image_to_string(processed_img, config='--oem 3 --psm 6')
                if len(text.strip()) > 20:  # Good result
                    return self._clean_nursing_text(text)
            except:
                pass
            
            # Fallback to PSM 3 if PSM 6 fails
            text = pytesseract.image_to_string(processed_img, config='--oem 3 --psm 3')
            
            # Clean and return
            cleaned_text = self._clean_nursing_text(text)
            return cleaned_text
            
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""
    
    def _preprocess_for_nursing(self, image):
        """Preprocess image for better OCR of nursing questions"""
        try:
            # Convert to grayscale
            gray = image.convert('L')
            
            # Enhance contrast (helps with screen captures)
            enhancer = ImageEnhance.Contrast(gray)
            enhanced = enhancer.enhance(2.0)
            
            # Apply sharpening
            sharpened = enhanced.filter(ImageFilter.SHARPEN)
            
            # Resize if too small (helps with small text)
            width, height = sharpened.size
            if width < 800:
                scale = 800 / width
                new_size = (int(width * scale), int(height * scale))
                sharpened = sharpened.resize(new_size, Image.Resampling.LANCZOS)
            
            return sharpened
            
        except Exception as e:
            print(f"Preprocessing error: {e}")
            return image
    
    def _clean_nursing_text(self, text):
        """Clean OCR text for nursing questions"""
        if not text:
            return ""
        
        # Fix common OCR errors in nursing/medical terms
        replacements = {
            # Medical terms
            'mi/h': 'mL/h',
            'mi/hr': 'mL/hr',
            'mgimi': 'mg/mL',
            'miimin': 'mL/min',
            'IVPB': 'IVPB',
            'PRBC5': 'PRBCs',
            '02': 'O2',
            'C02': 'CO2',
            'mmHQ': 'mmHg',
            'BPIM': 'BPM',
            'IIV': 'IV',
            'S02': 'SO2',
            'Na+': 'Na+',
            'K+': 'K+',
            'Ca2+': 'Ca2+',
            'mcg': 'mcg',
            'mglkg': 'mg/kg',
            
            # Question indicators
            'SEIECT': 'SELECT',
            'alll': 'all',
            'thiat': 'that',
            
            # Common nursing abbreviations
            'qtt': 'gtt',
            'Qtt': 'gtt',
            'unlt': 'unit',
            'mEqIL': 'mEq/L',
            'mg1dL': 'mg/dL',
            'bld': 'bid',  # twice daily
            'tld': 'tid',  # three times daily
            'qld': 'qid',  # four times daily
        }
        
        cleaned = text
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)
        
        # Fix spacing around punctuation
        cleaned = re.sub(r'\s+([.,;:])', r'\1', cleaned)
        cleaned = re.sub(r'([.,;:])\s*', r'\1 ', cleaned)
        
        # Fix question numbering
        cleaned = re.sub(r'(\d+)\s*\.\s*', r'\1. ', cleaned)
        
        # Fix option letters
        cleaned = re.sub(r'([A-Da-d])\s*\)\s*', r'\1) ', cleaned)
        cleaned = re.sub(r'([A-Da-d])\s*\.\s*', r'\1. ', cleaned)
        
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)
        
        # Ensure we capture SATA indicators
        if 'SELECT ALL THAT APPLY' in cleaned.upper():
            cleaned = cleaned.replace('SELECT ALL THAT APPLY', '**SELECT ALL THAT APPLY**')
        
        # Highlight priority indicators
        priority_words = ['FIRST', 'PRIORITY', 'IMMEDIATE', 'MOST appropriate', 'BEST']
        for word in priority_words:
            if word in cleaned:
                cleaned = cleaned.replace(word, f'**{word}**')
        
        return cleaned.strip()
