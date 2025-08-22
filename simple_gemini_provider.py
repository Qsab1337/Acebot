"""
Simple Gemini Provider - Updated for Gemini 2.5 Pro with MAXIMUM 65,535 Tokens
"""
import requests
import json
import base64
import os
import sys
import time
from PIL import Image
import io


class SimpleGeminiProvider:
    def __init__(self, api_key=None):
        # Validate API key
        if not api_key:
            raise ValueError("[ERROR] No Gemini API key provided!")
        
        # Clean the API key
        self.api_key = api_key.strip()
        
        # Validate key format
        if len(self.api_key) < 30:
            raise ValueError(f"[ERROR] API key too short ({len(self.api_key)} chars)")
        
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        
        # FORCE GEMINI 2.5 PRO - NEVER CHANGE THIS
        self.model = "gemini-2.5-pro"  # DO NOT CHANGE THIS
        
        print(f"[GEMINI] Initialized with model: {self.model}")
        print(f"[GEMINI] API Key: {self.api_key[:10]}...{self.api_key[-4:]}")
        
        # Test the API key
        self.test_api_key()
        
        # Create persistent session
        self.session = requests.Session()
        self.session.headers['Content-Type'] = 'application/json'
        
        # Load prompt
        self.prompt = self.load_prompt()
        print(f"[GEMINI] Loaded prompt: {len(self.prompt)} characters")
        
        # Cache for responses
        self.cache = {}
        self.cache_hits = 0
        
        # Settings - MAXIMUM TOKENS UPDATED
        self.timeout = 120  # Increased timeout for very long responses
        self.max_retries = 3
        self.last_error = None
        
        # TOKEN LIMITS - UPDATED TO ACTUAL MAXIMUM
        self.max_output_tokens = 65535  # Maximum for Gemini 2.5 Pro (65,535 tokens)
        self.temperature = 0.1  # Keep low for accuracy
        
        print(f"[GEMINI] Max output tokens set to: {self.max_output_tokens:,}")
    
    def test_api_key(self):
        """Test if API key is valid"""
        # FORCE gemini-2.5-pro in test URL
        test_url = f"{self.base_url}/gemini-2.5-pro:generateContent?key={self.api_key}"
        
        test_data = {
            "contents": [{
                "parts": [{"text": "Hello"}]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 10
            }
        }
        
        try:
            print("[GEMINI] Testing API key with gemini-2.5-pro...")
            response = requests.post(test_url, json=test_data, timeout=10)
            
            if response.status_code == 200:
                print("[GEMINI] ✅ API key valid for gemini-2.5-pro!")
                print(f"[GEMINI] Model supports up to 65,535 output tokens")
                return True
            elif response.status_code == 400:
                error = response.json()
                if 'API_KEY_INVALID' in str(error):
                    raise ValueError(f"[ERROR] Invalid API key!")
            elif response.status_code == 403:
                raise ValueError(f"[ERROR] API key not authorized for gemini-2.5-pro")
            else:
                print(f"[WARNING] API test returned status {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print("[WARNING] No internet connection for API test")
        except requests.exceptions.Timeout:
            print("[WARNING] API test timed out")
        except Exception as e:
            print(f"[WARNING] API test error: {e}")
    
    def load_prompt(self):
        """Load prompt from file or use default"""
        try:
            prompt_locations = [
                'prompt.txt',
                os.path.join(os.path.dirname(__file__), 'prompt.txt'),
                os.path.join(os.path.dirname(sys.executable), 'prompt.txt')
            ]
            
            for location in prompt_locations:
                if os.path.exists(location):
                    with open(location, 'r', encoding='utf-8') as f:
                        prompt = f.read().strip()
                        if prompt:
                            print(f"[GEMINI] Prompt loaded from: {location}")
                            return prompt
            
            # Default prompt - CONCISE for more answer space
            print("[GEMINI] Using default prompt")
            return """Analyze this nursing exam question.
For 'Select all that apply': identify ALL correct options.
Provide complete, accurate answers.
With 65,535 max tokens available, provide comprehensive explanations."""
            
        except Exception as e:
            print(f"[ERROR] Loading prompt: {e}")
            return "Answer this nursing exam question completely."
    
    def get_cache_key(self, data):
        """Generate cache key"""
        import hashlib
        if isinstance(data, bytes):
            return hashlib.md5(data).hexdigest()[:12]
        elif isinstance(data, list):
            combined = b''.join(data)
            return hashlib.md5(combined).hexdigest()[:12]
        else:
            return hashlib.md5(str(data).encode()).hexdigest()[:12]
    
    def make_request_with_retry(self, data, attempt=1):
        """Make API request with proper response handling"""
        # ALWAYS use gemini-2.5-pro
        url = f"{self.base_url}/gemini-2.5-pro:generateContent?key={self.api_key}"
        
        try:
            print(f"[GEMINI] Making request to gemini-2.5-pro (attempt {attempt}/{self.max_retries})...")
            print(f"[GEMINI] Max output tokens: {data['generationConfig']['maxOutputTokens']:,}")
            
            response = self.session.post(url, json=data, timeout=self.timeout)
            
            # Success
            if response.status_code == 200:
                result = response.json()
                
                # Check for valid response with proper handling for MAX_TOKENS
                if 'candidates' in result and result['candidates']:
                    candidate = result['candidates'][0]
                    
                    # Check finish reason
                    finish_reason = candidate.get('finishReason', '')
                    print(f"[GEMINI] Finish reason: {finish_reason}")
                    
                    # Check token usage if available
                    if 'usageMetadata' in result:
                        usage = result['usageMetadata']
                        prompt_tokens = usage.get('promptTokenCount', 0)
                        output_tokens = usage.get('candidatesTokenCount', 0)
                        total_tokens = usage.get('totalTokenCount', 0)
                        print(f"[GEMINI] Token usage - Prompt: {prompt_tokens:,}, Output: {output_tokens:,}, Total: {total_tokens:,}")
                    
                    # Handle MAX_TOKENS case - still return partial response
                    if finish_reason == 'MAX_TOKENS':
                        print(f"[GEMINI] Response hit token limit (65,535) - returning partial answer")
                    elif finish_reason == 'STOP':
                        print("[GEMINI] Response completed normally")
                    
                    # Extract text from response
                    if 'content' in candidate:
                        content = candidate['content']
                        if 'parts' in content:
                            parts = content['parts']
                            if parts and isinstance(parts, list):
                                # Combine all text parts
                                text_parts = []
                                for part in parts:
                                    if isinstance(part, dict) and 'text' in part:
                                        text_parts.append(part['text'])
                                
                                if text_parts:
                                    full_text = '\n'.join(text_parts).strip()
                                    if full_text:
                                        if finish_reason == 'MAX_TOKENS':
                                            full_text += "\n\n[Note: Response reached maximum token limit of 65,535]"
                                        print(f"[GEMINI] ✅ Got response ({len(full_text)} chars)")
                                        return full_text
                    
                    # If we have content but no text, check for safety blocks
                    if 'content' in candidate and 'role' in candidate['content']:
                        if candidate['content']['role'] == 'model':
                            # Model responded but no text - likely safety block
                            safety_ratings = candidate.get('safetyRatings', [])
                            if safety_ratings:
                                print(f"[GEMINI] Safety ratings: {safety_ratings}")
                                return "⚠️ Response blocked by safety filters. Try rephrasing the question."
                
                # Response structure issue
                print(f"[GEMINI] Unexpected response structure")
                print(f"[GEMINI] Full response: {json.dumps(result, indent=2)[:500]}")
                self.last_error = "Invalid response format"
                
                # Try to extract any available text
                if 'candidates' in result and result['candidates']:
                    for candidate in result['candidates']:
                        if 'content' in candidate and 'parts' in candidate['content']:
                            for part in candidate['content']['parts']:
                                if 'text' in part and part['text'].strip():
                                    return part['text'].strip()
                
                return "❌ Received response but couldn't extract answer. Try again."
            
            # Error handling for other status codes
            elif response.status_code == 400:
                error = response.json()
                error_msg = str(error)
                
                if 'API_KEY_INVALID' in error_msg:
                    self.last_error = "Invalid API key"
                    return "❌ Invalid API key. Please check your key in settings (Ctrl+Alt+S)"
                else:
                    self.last_error = f"Bad request: {response.status_code}"
                    print(f"[ERROR] Bad request: {error_msg[:200]}")
                    
            elif response.status_code == 403:
                self.last_error = "API not enabled"
                return "❌ Gemini 2.5 Pro API not enabled. Check Google Cloud Console."
                
            elif response.status_code == 429:
                # Rate limited - retry with backoff
                if attempt < self.max_retries:
                    wait_time = min(2 ** attempt, 30)
                    print(f"[GEMINI] Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    return self.make_request_with_retry(data, attempt + 1)
                else:
                    self.last_error = "Rate limited"
                    return "⏳ Rate limited. Please wait a moment and try again."
                    
            elif response.status_code in [500, 502, 503]:
                # Server error - retry
                if attempt < self.max_retries:
                    print(f"[GEMINI] Server error {response.status_code}, retrying...")
                    time.sleep(2)
                    return self.make_request_with_retry(data, attempt + 1)
                else:
                    self.last_error = f"Server error {response.status_code}"
                    return "⚠️ Google server error. Please try again."
                    
            else:
                self.last_error = f"HTTP {response.status_code}"
                print(f"[ERROR] Unexpected status: {response.status_code}")
                print(f"[ERROR] Response: {response.text[:500]}")
                
        except requests.exceptions.ConnectionError:
            self.last_error = "No internet connection"
            return "❌ No internet connection. Please check your connection."
            
        except requests.exceptions.Timeout:
            if attempt < self.max_retries:
                print(f"[GEMINI] Timeout, retrying...")
                return self.make_request_with_retry(data, attempt + 1)
            else:
                self.last_error = "Request timeout"
                return "⏱️ Request timed out. Please try again."
                
        except Exception as e:
            self.last_error = str(e)[:50]
            print(f"[ERROR] Unexpected error: {e}")
            return f"❌ Error: {str(e)[:100]}"
        
        return None
    
    def analyze_image(self, image_bytes):
        """Analyze single image with maximum token output"""
        # Check cache
        cache_key = self.get_cache_key(image_bytes)
        if cache_key in self.cache:
            self.cache_hits += 1
            print(f"[GEMINI] Cache hit! (Total: {self.cache_hits})")
            return self.cache[cache_key]
        
        print("[GEMINI] Analyzing image with gemini-2.5-pro...")
        print(f"[GEMINI] Using maximum tokens: {self.max_output_tokens:,}")
        
        # Prepare image
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Build request with MAXIMUM tokens (65,535)
        data = {
            "contents": [{
                "parts": [
                    {"text": self.prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": image_base64
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_output_tokens,  # 65,535 - MAXIMUM
                "topK": 1,
                "topP": 1.0,
                "candidateCount": 1
            },
            "safetySettings": [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE"
                }
            ]
        }
        
        # Make request
        result = self.make_request_with_retry(data)
        
        if result and not result.startswith("❌") and not result.startswith("⏳") and not result.startswith("⚠️"):
            # Cache successful response
            self.cache[cache_key] = result
            if len(self.cache) > 50:
                # Remove oldest entries
                for key in list(self.cache.keys())[:10]:
                    del self.cache[key]
            return result
        elif result:
            return result
        else:
            error_msg = self.last_error or "Unknown error"
            return f"❌ Unable to analyze image: {error_msg}\nCheck your API key in settings (Ctrl+Alt+S)"
    
    def analyze_multiple_images(self, image_bytes_list):
        """Analyze multiple images with maximum token output"""
        print(f"[GEMINI] Analyzing {len(image_bytes_list)} images with gemini-2.5-pro...")
        print(f"[GEMINI] Using maximum tokens: {self.max_output_tokens:,}")
        
        # Check cache
        cache_key = self.get_cache_key(image_bytes_list)
        if cache_key in self.cache:
            self.cache_hits += 1
            print(f"[GEMINI] Cache hit for multiple images!")
            return self.cache[cache_key]
        
        # Build request with all images
        parts = [{"text": self.prompt + f"\n\nAnalyzing {len(image_bytes_list)} images. With 65,535 tokens available, provide comprehensive analysis for all questions shown."}]
        
        for i, img_bytes in enumerate(image_bytes_list):
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')
            parts.append({
                "inline_data": {
                    "mime_type": "image/png",
                    "data": img_base64
                }
            })
        
        data = {
            "contents": [{
                "parts": parts
            }],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_output_tokens,  # 65,535 - MAXIMUM
                "topK": 1,
                "topP": 1.0,
                "candidateCount": 1
            },
            "safetySettings": [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE"
                }
            ]
        }
        
        # Make request
        result = self.make_request_with_retry(data)
        
        if result and not result.startswith("❌") and not result.startswith("⏳") and not result.startswith("⚠️"):
            # Cache successful response
            self.cache[cache_key] = result
            return result
        elif result:
            return result
        else:
            # If multiple fails, try just the first image
            print("[GEMINI] Multiple image analysis failed, trying first image only...")
            return self.analyze_image(image_bytes_list[0])
    
    def analyze_text(self, text):
        """Analyze text with maximum token output"""
        print("[GEMINI] Analyzing extracted text with gemini-2.5-pro...")
        print(f"[GEMINI] Using maximum tokens: {self.max_output_tokens:,}")
        
        # Check cache
        cache_key = self.get_cache_key(text)
        if cache_key in self.cache:
            self.cache_hits += 1
            return self.cache[cache_key]
        
        data = {
            "contents": [{
                "parts": [{
                    "text": f"{self.prompt}\n\nExtracted text:\n{text}\n\nWith 65,535 tokens available, provide a comprehensive analysis."
                }]
            }],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_output_tokens,  # 65,535 - MAXIMUM
                "topK": 1,
                "topP": 1.0,
                "candidateCount": 1
            },
            "safetySettings": [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE"
                }
            ]
        }
        
        result = self.make_request_with_retry(data)
        
        if result and not result.startswith("❌"):
            self.cache[cache_key] = result
            return result
        elif result:
            return result
        else:
            return "❌ Unable to analyze text. Check API key in settings."
    
    def get_stats(self):
        """Get provider statistics"""
        return {
            "cache_size": len(self.cache),
            "cache_hits": self.cache_hits,
            "model": "gemini-2.5-pro",  # ALWAYS gemini-2.5-pro
            "max_tokens": self.max_output_tokens,  # 65,535
            "last_error": self.last_error
        }