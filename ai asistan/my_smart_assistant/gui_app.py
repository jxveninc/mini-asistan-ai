# my_smart_assistant/gui_app.py
import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading 

from assistant_core import SmartAssistant

class ChatGUI:
    def __init__(self, master):
        self.master = master
        master.title("Akıllı Öğrenen Asistan")
        master.geometry("600x600")
        master.configure(bg="#f0f2f5") 

        # Geri bildirim fonksiyonunu master.after ile GUI thread'ine bağlıyoruz
        feedback_func = lambda msg: self.master.after(0, lambda: self.display_feedback(msg))
        self.assistant = SmartAssistant(feedback_callback=feedback_func) # <-- Geri bildirim buraya iletiliyor

        # --- Stil Tanımlamaları ---
        self.font_large = ('Arial', 12)
        self.font_medium = ('Arial', 10)
        self.bg_color = "#f0f2f5"
        self.chat_bg = "#ffffff"
        self.user_color = "#2196F3" 
        self.bot_color = "#4CAF50" 
        self.button_color = "#007bff" 
        self.button_fg = "white"
        
        # --- Arayüz Bileşenleri ---
        self.chat_display = scrolledtext.ScrolledText(master, wrap=tk.WORD, state='disabled', 
                                                      font=self.font_medium, bg=self.chat_bg, bd=0, padx=10, pady=10)
        self.chat_display.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.chat_display.tag_config('user', foreground=self.user_color, font=(self.font_medium[0], self.font_medium[1], 'bold'))
        self.chat_display.tag_config('bot', foreground=self.bot_color, font=(self.font_medium[0], self.font_medium[1], 'bold'))
        self.chat_display.tag_config('feedback', foreground='#808080', font=(self.font_medium[0], self.font_medium[1], 'italic')) # Gri geri bildirim

        input_frame = tk.Frame(master, bg=self.bg_color)
        input_frame.pack(padx=10, pady=10, fill=tk.X)

        # Hata çözümü: padx/pady pack metoduna taşındı
        self.user_entry = tk.Entry(input_frame, font=self.font_large, bd=1, relief=tk.SOLID) 
        self.user_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), pady=8) 
        self.user_entry.bind("<Return>", self.send_message)

        # Hata çözümü: padx/pady pack metoduna taşındı
        self.send_button = tk.Button(input_frame, text="Gönder", command=self.send_message, 
                                     font=self.font_large, bg=self.button_color, fg=self.button_fg, 
                                     activebackground="#0056b3", activeforeground="white", bd=0) 
        self.send_button.pack(side=tk.RIGHT, padx=5, pady=5)

        self.display_message("Merhaba! Bana bir şeyler sorabilirsin. Bilmediğim konuları Wikipedia'dan araştırıp öğrenebilirim.", "bot")
        self.display_message(f"Hafızamda {self.assistant.kb.get_knowledge_count()} bilgi var.", "bot")
        self.is_learning_active = True # <-- Yeni Durum Değişkeni

        # Öğrenme Kontrol Çerçevesi
        control_frame = tk.Frame(master, bg=self.bg_color)
        control_frame.pack(padx=10, pady=(0, 10), fill=tk.X)
        
        # Butonu tanımla
        self.learn_toggle_button = tk.Button(control_frame, text="ÖĞRENMEYİ DURDUR", 
                                             command=self.toggle_self_learning,
                                             font=self.font_medium, bg="#ff4d4d", fg="white", 
                                             activebackground="#cc0000", activeforeground="white", bd=0, padx=10, pady=5)
        self.learn_toggle_button.pack(side=tk.LEFT, padx=5, pady=5) # <-- Yeni Buton
        
        # Bilgi Sayısını Göstermek İçin Etiket (Opsiyonel ama faydalı)
        self.knowledge_count_label = tk.Label(control_frame, 
                                            text=f"Toplam Bilgi: {self.assistant.kb.get_knowledge_count()}",
                                            font=self.font_medium, bg=self.bg_color, fg="#333333")
        self.knowledge_count_label.pack(side=tk.RIGHT, padx=5, pady=5)

        # KENDİ KENDİNE ÖĞRENME DÖNGÜSÜNÜ BAŞLAT
        self.start_self_learning_loop()

    def toggle_self_learning(self):
        """
        Kendi kendine öğrenme durumunu değiştirir (Aç/Kapa).
        """
        self.is_learning_active = not self.is_learning_active
        
        if self.is_learning_active:
            # Aktifleştirme
            self.learn_toggle_button.config(text="ÖĞRENMEYİ DURDUR", bg="#ff4d4d", activebackground="#cc0000")
            self.display_feedback("✅ Kendi Kendine Öğrenme BAŞLATILDI.")
            
        else:
            # Durdurma
            self.learn_toggle_button.config(text="ÖĞRENMEYİ BAŞLAT", bg="#4CAF50", activebackground="#388E3C")
            self.display_feedback("⏸️ Kendi Kendine Öğrenme DURDURULDU.")

    def display_message(self, message, sender):
        """Sohbet ekranına normal mesajı ekler."""
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, f"{'Sen' if sender == 'user' else 'Asistan'}: ", sender)
        self.chat_display.insert(tk.END, f"{message}\n\n") 
        self.chat_display.config(state='disabled')
        self.chat_display.yview(tk.END) 

    def display_feedback(self, message):
        """Asistandan gelen canlı geri bildirimleri (gri renkte) gösterir."""
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, f"⚙️ {message}\n", 'feedback')
        self.chat_display.config(state='disabled')
        self.chat_display.yview(tk.END)

    def send_message(self, event=None):
        """Kullanıcı girdisini işler ve asistanı tetikler."""
        user_text = self.user_entry.get().strip()
        if not user_text:
            return

        self.display_message(user_text, "user")
        self.user_entry.delete(0, tk.END)

        # UI'ı kilitle
        self.send_button.config(state=tk.DISABLED, text="Düşünüyor...")
        self.user_entry.config(state=tk.DISABLED)
        self.master.update_idletasks()

        # Asistanın cevabını ayrı bir iş parçacığında al
        threading.Thread(target=self._get_assistant_response, args=(user_text,)).start()

    def _get_assistant_response(self, user_text):
        """Asistanın chat ve öğrenme mantığını arka planda çalıştırır."""
        try:
            response = self.assistant.get_response(user_text)
            self.master.after(0, lambda: self._update_gui_with_response(response))
        except Exception as e:
            self.master.after(0, lambda: self._show_error_message(f"Beklenmedik bir hata oluştu: {e}"))

    def _update_gui_with_response(self, response):
        """Asistan cevabını GUI'ye yansıtır ve UI'yi açar."""
        self.display_message(response, "bot")
        self.send_button.config(state=tk.NORMAL, text="Gönder")
        self.user_entry.config(state=tk.NORMAL)
        self.user_entry.focus_set()

    def _show_error_message(self, message):
        """Hata mesajını gösterir ve UI'yi açar."""
        messagebox.showerror("Hata", message)
        self.send_button.config(state=tk.NORMAL, text="Gönder")
        self.user_entry.config(state=tk.NORMAL)
        self.user_entry.focus_set()
    
    def start_self_learning_loop(self):
        """
        Kendi kendine öğrenme döngüsünü başlatan metot.
        Her 5 saniyede bir döngü tetiklenir.
        """
        # Öğrenme süreci uzun sürebileceği için arayüzü dondurmamak adına thread kullanıyoruz.
        self_learn_thread = threading.Thread(target=self._run_self_learn_thread)
        self_learn_thread.daemon = True # Ana program kapandığında thread'i sonlandır
        self_learn_thread.start()

    def _run_self_learn_thread(self):
        """
        Kendi kendine öğrenme işlemini 5 saniye aralıklarla çalıştırır.
        """
        # Tekrar eden görev tanımlama
        self.master.after(5000, self._initiate_self_learn_cycle) 
    
    def _initiate_self_learn_cycle(self):
        """
        Asistanın kendi kendine öğrenme döngüsünü başlatır ve bir sonraki döngüyü ayarlar.
        Sadece is_learning_active True ise öğrenme işlemini yapar.
        """
        if self.is_learning_active: # <-- KONTROL EKLENDİ
            try:
                self.display_feedback("🤖 Kendi Kendine Öğrenme Aktif...")
                
                # Asıl öğrenme işlemi
                self.assistant.self_learn_cycle()
                
                # Bilgi sayısını güncelle (Başarılı öğrenme durumunda)
                self.knowledge_count_label.config(text=f"Toplam Bilgi: {self.assistant.kb.get_knowledge_count()}")
                
            except Exception as e:
                self.display_feedback(f"Kendi kendine öğrenme sırasında hata: {e}")


        # 5 saniye sonra kendini tekrar çağır (Sürekli Döngü)
        self.master.after(5000, self._initiate_self_learn_cycle)


if __name__ == "__main__":
    root = tk.Tk()
    app = ChatGUI(root)
    root.mainloop()