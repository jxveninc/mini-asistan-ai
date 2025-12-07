# my_smart_assistant/knowledge_base.py
import json
import os
import datetime

class KnowledgeBase:
    def __init__(self, filename="knowledge_base.json"):
        self.filename = filename
        self.data = self._load_data()

    def _load_data(self):
        """JSON dosyasını yükler veya yoksa/boşsa boş bir yapı oluşturur."""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if not isinstance(data, dict) or "bilgiler" not in data:
                        return {"bilgiler": []}
                    return data
            except json.JSONDecodeError:
                return {"bilgiler": []}
            except Exception:
                return {"bilgiler": []}
        else:
            return {"bilgiler": []}

    def _save_data(self):
        """Veriyi JSON dosyasına kaydeder."""
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def add_knowledge(self, kaynak, soru, cevap):
        """Hafızaya yeni bir bilgi (Soru-Cevap çifti) ekler."""
        new_entry = {
            "kaynak": kaynak,
            "soru": soru,
            "cevap": cevap,
            "tarih": self.get_current_date()
        }
        # Tekrar eden bilgiyi eklememek için basit kontrol
        if not any(entry['soru'].lower() == soru.lower() for entry in self.data['bilgiler']):
            self.data["bilgiler"].append(new_entry)
            self._save_data()
            return True
        return False

    def get_knowledge_count(self):
        """Hafızadaki bilgi sayısını döndürür."""
        return len(self.data["bilgiler"])
    
    def get_current_date(self):
        """Anlık tarihi döndürür."""
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def get_all_knowledge(self):
        """Tüm bilgi tabanını döndürür."""
        return self.data["bilgiler"]