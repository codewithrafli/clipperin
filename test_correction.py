
import re

# Mock TextProcessor with the same logic as in tasks.py
class TextProcessor:
    """Handles text normalization and correction"""
    
    # Common Indonesian Slang Dictionary
    SLANG_DICT = {
        r"\bgak\b": "tidak",
        r"\bnggak\b": "tidak",
        r"\bga\b": "tidak",
        r"\btak\b": "tidak",
        r"\bgk\b": "tidak",
        r"\byg\b": "yang",
        r"\bak\b": "aku",
        r"\baqu\b": "aku",
        r"\bgw\b": "gue",
        r"\blu\b": "lo",
        r"\budh\b": "sudah",
        r"\bdah\b": "sudah",
        r"\bblm\b": "belum",
        r"\bkrn\b": "karena",
        r"\bkalo\b": "kalau",
        r"\bkl\b": "kalau",
        r"\bjd\b": "jadi",
        r"\bjg\b": "juga",
        r"\bbr\b": "baru",
        r"\bspt\b": "seperti",
        r"\bgmn\b": "gimana",
        r"\bpd\b": "pada",
        r"\bdlm\b": "dalam",
        r"\bdr\b": "dari",
        r"\butk\b": "untuk",
        r"\bny\b": "nya",
        r"\bbgt\b": "banget",
        r"\baja\b": "saja",
        r"\baj\b": "saja",
        r"\bsama\b": "sama",
        r"\bsm\b": "sama",
        r"\bthx\b": "makasih",
        r"\bmkasih\b": "makasih",
        r"\bjan\b": "jangan",
        r"\bjgn\b": "jangan",
        r"\btdk\b": "tidak",
        # Specific Phonetic Fixes (Whisper Hallucinations)
        r"\bmasyumis\b": "masih bisa",
        r"\bpisot\b": "episode",
        r"\bcukali\b": "lucu kali",
        r"\bcukam\b": "cuma",
        r"\bkarus\b": "kadang",
        r"\byonobak\b": "yono bakri",
        r"\byonobakri\b": "yono bakri",
        r"\bdirilus\b": "diri lu",
        r"\bresulusinya\b": "resolusinya",
    }

    @staticmethod
    def normalize(text: str) -> str:
        """Basic normalization: trim, lowercase first char if needed"""
        if not text:
            return ""
        text = text.strip()
        # Ensure only one space between words
        text = re.sub(r'\s+', ' ', text)
        return text

    @staticmethod
    def correct_slang(text: str) -> str:
        """Rule-based replacement of slang words"""
        if not text:
            return ""
        
        corrected = text
        for pattern, replacement in TextProcessor.SLANG_DICT.items():
            corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
            
        # Fix common punctuation issues
        corrected = re.sub(r'\s+([,.?!])', r'\1', corrected) # Remove space before punct
        
        return corrected

# Sample inputs from user (New Batch)
inputs = [
    "Dari sekian banyak resolusi yang lu jalanin",
    "Ada berapa sih?",
    "Yang berjalan dengan baik",
    "Coba",
    "Crosscheck",
    "Perna ga lo?",
    "Meng Crosscheck dirilus diri",
    "Lari lu jalanin",
    "Terjadi apa tidak?",
    "Orang banyak orang sekedar nulis doang",
    "Dan dari suruh pengguliat ya",
    "Di padahal udah masuk ke tahun 2025",
    "Paling banyak orang tuh apa?",
    "Paganya apa? Lebih sehat",
    "Kemudian gue liat tuh, temen gue",
    "Resulusinya, lari pagi, lebih konsisten",
    "Ah, begitu"
]

print("=== Text Correction Test (Batch 2) ===\n")
for original in inputs:
    step1 = TextProcessor.normalize(original)
    corrected = TextProcessor.correct_slang(step1)
    
    print(f"Original: {original}")
    if corrected != original:
        print(f"✅ Corrected: {corrected}")
    else:
        print(f"⚪ No change: {corrected}")
    print("-" * 40)
