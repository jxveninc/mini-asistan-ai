# my_smart_assistant/assistant_core.py
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
import wikipedia # Wikipedia API kütüphanesi
import time 
from fuzzywuzzy import fuzz, process # <-- BU İKİ SATIRI EKLEYİN
import re # Metin temizleme için

from knowledge_base import KnowledgeBase
from web_scraper import fetch_and_clean_text # Bu sadece yapısal olarak duruyor

class SmartAssistant:
    def __init__(self, kb_filename="knowledge_base.json", feedback_callback=None):
        self.kb = KnowledgeBase(kb_filename)
        self.feedback = feedback_callback
        
        try:
            nltk.download('punkt', quiet=True) 
        except Exception as e:
             self._send_feedback(f"NLTK indirme hatası: {e}. Lütfen internet bağlantınızı kontrol edin.")
             
        # Q&A çifti üretim kuralları (sabit ve Wikipedia uyumlu)
        self.qa_rules_config = {'min_sentence_len': 20} 

    def _send_feedback(self, message):
        """Geri bildirim fonksiyonu tanımlıysa mesajı GUI'ye gönderir."""
        if self.feedback:
            # GUI main thread'inde çalışması için bu mekanizma kullanılır
            self.feedback(message)

    def _clean_text(self, text):
        """
        Metni küçük harfe çevirir, noktalama ve gereksiz boşlukları kaldırır.
        """
        # Sadece harf, rakam ve boşlukları tut
        cleaned = re.sub(r'[^\w\s]', '', text).lower()
        # Fazla boşlukları tek boşluğa düşür
        return re.sub(r'\s+', ' ', cleaned).strip()

    def _generate_qa_from_sentence(self, sentence):
        """
        Gelen cümleden Soru-Cevap çifti üretir. Kontrol mekanizması gevşetildi.
        """
        
        if len(sentence) < 20: 
             return None, None
             
        tokens = word_tokenize(sentence)
        
        if len(tokens) > 3:
            # Soru için cümlenin ilk 4 kelimesini alıyoruz
            limit = min(4, len(tokens) - 1)
            keyword_phrase = ' '.join(tokens[:limit]).lower()
            
            # Soru formatını doğrudan anahtar kelimeden türet.
            soru = f"{keyword_phrase} nedir?"
            cevap = sentence.capitalize()
            
            # KONTROL GEVŞETİLİYOR: Artık sadece ilk kelimeyi kontrol etmiyoruz,
            # cevap olarak kaydetmeyi deniyoruz. Zaten tek cümlelik özet olduğu için
            # alakasız olma ihtimali çok düşüktür.
            # Anahtar kelimenin ilk token'ının cevapta geçmesi yeterli.
            
            first_keyword = keyword_phrase.split()[0].lower()
            
            if len(first_keyword) > 2 and first_keyword in self._clean_text(cevap).lower():
                return soru.capitalize(), cevap
            
        return None, None

    def learn_from_text(self, text, source_name="Wikipedia Kaynağı"):
        """Verilen metinden Soru-Cevap çiftleri üretir ve hafızaya kaydeder."""
        if not text:
            return 0 

        try:
            # Türkçe metin için 'turkish' dilini kullanmayı deneriz
            sentences = sent_tokenize(text, language='turkish')
        except LookupError:
            sentences = sent_tokenize(text, language='english') 
        
        new_knowledge_count = 0
        for sentence in sentences:
            soru, cevap = self._generate_qa_from_sentence(sentence)
            
            if soru and cevap and len(soru) > 10:
                if self.kb.add_knowledge(source_name, soru, cevap):
                    new_knowledge_count += 1
        return new_knowledge_count

    
    def search_and_learn_online(self, query, num_results=1):
        """
        Doğrudan Wikipedia API'sini kullanarak arama yapar ve öğrenir.
        """
        self._send_feedback(f"Wikipedia Arama başlatıldı: '{query}'")
        total_learned = 0
        
        # YENİ KOD: Sorgudan gereksiz kelimeleri (nedir, kimdir vb.) ve noktalama işaretlerini kaldır
        cleaned_search_query = query.lower().replace('nedir', '').replace('kimdir', '').replace('?', '').strip()
        
        if not cleaned_search_query: # Eğer sadece "nedir?" sorulmuşsa
             cleaned_search_query = query 
             
        try:
            wikipedia.set_lang("tr") 
            
            # Sorguyu temizlenmiş haliyle gönderiyoruz.
            raw_text = wikipedia.summary(cleaned_search_query, sentences=1, auto_suggest=True) 
            
            # Sayfa başlığını çekelim (auto_suggest olduğu için doğru başlık bulunur)
            page = wikipedia.page(cleaned_search_query, auto_suggest=True)
            page_title = page.title

            self._send_feedback(f"Sayfa özeti çekiliyor: '{page_title}'")
            
            if not raw_text:
                self._send_feedback("Sayfadan içerik çekilemedi (boş metin).")
                return 0
            
            learned_from_wiki = self.learn_from_text(raw_text, f"Wikipedia Özeti: {page_title}")
            
            self._send_feedback(f"-> {page_title} özetinden {learned_from_wiki} adet bilgi öğrenildi.")
            total_learned += learned_from_wiki

        except wikipedia.exceptions.PageError:
            self._send_feedback("Wikipedia Sayfa Hatası: Sayfa içeriği çekilemedi.")
            return 0
        except Exception as e:
            self._send_feedback(f"Wikipedia Bağlantı/API Hatası: {e}")
            return 0
        
        return total_learned


    def get_response(self, user_input):
        
        user_input_lower = user_input.lower()
        
        # 1. Aşama: Bulanık Eşleştirme ile Hafızayı Kontrol Et
        
        # Kullanıcı girdisini temizle (yazım/noktalama hatalarını ignore etmek için)
        cleaned_input = self._clean_text(user_input_lower)
        
        # Hafızadaki tüm soruları al
        all_questions = [entry['soru'] for entry in self.kb.get_all_knowledge()]
        
        if all_questions:
            # Bulanık eşleştirme yap: Temizlenmiş girdiye en çok benzeyen soruyu bul
            # Score eşiğini 85 olarak belirle (%85 benzerlik yeterli)
            match_result = process.extractOne(cleaned_input, all_questions, scorer=fuzz.ratio)
            
            best_match_question = match_result[0] # En iyi eşleşen soru
            best_score = match_result[1]         # Benzerlik puanı

            if best_score >= 85: # Eşik değeri: %85 ve üzeri kabul
                
                # Eşleşen soruyu kullanarak bilgiyi KnowledgeBase'ten bul
                for entry in self.kb.get_all_knowledge():
                    if entry['soru'] == best_match_question:
                        self._send_feedback(f"🧠 Hafıza eşleşti: '{best_match_question}' (%{best_score} benzerlik)")
                        return f"🤖 Cevap: {entry['cevap']} (Kaynak: {entry['kaynak']})"
        
        # Eğer sohbet kalıplarından bir cevap bulunamazsa, Wikipedia arama ve öğrenmeye devam et
        self._send_feedback("🔍 Hafızada net eşleşme bulunamadı. Wikipedia araştırması başlıyor...")
        
        # 2. Aşama: Wikipedia'dan araştır ve öğren (Kalan kod aynı)
        try:
            wikipedia.set_lang("tr") 
            
            # Wikipedia, arama terimini otomatik olarak düzeltir ve en iyi başlığı döndürür
            corrected_query = wikipedia.search(user_input, results=1)
            
            if corrected_query:
                # Düzeltilmiş başlığı/sorguyu kullan
                search_query = corrected_query[0]
                self._send_feedback(f"💡 Sorgu Düzeltildi: '{user_input}' yerine '{search_query}' aranacak.")
            else:
                search_query = user_input # Başlık bulunamazsa orijinalini kullan
                
        except Exception:
            search_query = user_input # Hata olursa orijinalini 
            
        learned_count = self.search_and_learn_online(search_query)
        
        if learned_count > 0:
            # Yeni öğrenilen bilgiyi kullanarak tekrar cevap ara
            for entry in self.kb.get_all_knowledge():
                if user_input.lower() in entry['soru'].lower() or \
                   user_input.lower() in entry['cevap'].lower():
                    return f"💡 Yeni öğrendiğim bilgiye göre: {entry['cevap']} "
            else:
                 return f"💡 Yeni bir şeyler öğrendim ({learned_count} yeni bilgi), ancak sorunuzun spesifik cevabını henüz çıkaramadım."
        else:
            # Öğrenme başarısız oldu
            return "😔 Üzgünüm, bu konuyu henüz bilmiyorum ve Wikipedia'da da anlamlı bir bilgi bulamadım."
        
    def generate_self_query(self):
        """
        Hafızadaki mevcut bilgileri kullanarak yeni bir arama sorgusu üretir.
        """
        all_knowledge = self.kb.get_all_knowledge()
        if not all_knowledge:
            return "Genel kültür nedir?" # Başlangıç sorgusu

        # Hafızadaki rastgele bir bilgiyi çek
        import random
        random_entry = random.choice(all_knowledge)

        # Yeni sorguyu, mevcut bilginin kaynağına veya cevabına dayandır
        query_type = random.choice(['kaynak', 'cevap'])
        
        if query_type == 'kaynak' and 'Wikipedia' in random_entry['kaynak']:
            # Wikipedia'nın öğrendiği sayfa adını alıp, 'nedir?' ekle
            base_query = random_entry['kaynak'].replace("Wikipedia: ", "").strip()
            self._send_feedback(f"🧠 İç sorgu: '{base_query}' bilgisinin derinleştirilmesi...")
            return base_query + " tarihçesi" # Konuyu derinleştir

        elif query_type == 'cevap':
            # Cevabın ilk 4 kelimesini alıp "ne işe yarar?" diye sor
            tokens = word_tokenize(random_entry['cevap'])
            if len(tokens) > 5:
                base_query = ' '.join(tokens[:4])
                self._send_feedback(f"🧠 İç sorgu: '{base_query}' hakkında ek bilgi aranıyor...")
                return base_query + " faydaları"
                
        # Hiçbiri tutmazsa, rastgele bir popüler konuya dön
        return random.choice(["Küresel ısınma nedir?", "Kara delikler nasıl oluşur?", "İnsan beyni hakkında bilgi"])
    
    
    def self_learn_cycle(self):
        """
        Asistanın kendi kendine bir sorgu ürettiği ve öğrendiği ana döngü.
        """
        query = self.generate_self_query()
        
        self._send_feedback("--------------------------------------------------")
        self._send_feedback(f"🤖 KENDİ KENDİNE ÖĞRENME BAŞLATILDI. Yeni sorgu: {query}")
        
        initial_count = self.kb.get_knowledge_count()
        
        # Sorguyu Wikipedia'ya gönder
        learned_count = self.search_and_learn_online(query)
        
        final_count = self.kb.get_knowledge_count()

        if learned_count > 0:
            self._send_feedback(f"✅ Öğrenme tamamlandı. {learned_count} yeni bilgi eklendi. Toplam bilgi: {final_count}")
        else:
            self._send_feedback("❌ Kendi kendine öğrenme başarılı olamadı veya yeni bilgi bulunamadı.")
        self._send_feedback("--------------------------------------------------")
        
        return learned_count