import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinterdnd2 import DND_FILES, TkinterDnD
from PIL import Image, ImageTk
import cv2
import numpy as np
import os
import io
import base64
from threading import Thread
import time

import easyocr
from ultralytics import YOLO

class ImageToTextApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Conversor de Imagem para Texto - YOLO + OCR")
        self.root.geometry("1000x700")
        self.root.configure(bg='#f0f0f0')
        
        # Variáveis
        self.current_image = None
        self.current_image_path = None
        self.yolo_model = None
        self.extracted_text = ""
        self.ocr_reader = None
        
        self.setup_ui()
        self.load_yolo_model()
        self.load_ocr_model()
        
    def setup_ui(self):
        # Título
        title_frame = tk.Frame(self.root, bg='#2c3e50', height=80)
        title_frame.pack(fill='x', padx=10, pady=(10, 0))
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(title_frame, text="Conversor de Imagem para Texto", 
                              font=('Arial', 20, 'bold'), fg='white', bg='#2c3e50')
        title_label.pack(expand=True)
        
        subtitle_label = tk.Label(title_frame, text="YOLO + OCR | Arraste, Cole ou Selecione Imagens", 
                                 font=('Arial', 12), fg='#ecf0f1', bg='#2c3e50')
        subtitle_label.pack()
        
        # Frame principal
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Frame esquerdo - Upload e Preview
        left_frame = tk.Frame(main_frame, bg='white', relief='raised', bd=2)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        # Área de upload
        self.upload_frame = tk.Frame(left_frame, bg='#ecf0f1', relief='ridge', bd=2)
        self.upload_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Configurar drag and drop
        self.upload_frame.drop_target_register(DND_FILES)
        self.upload_frame.dnd_bind('<<Drop>>', self.on_drop)
        
        upload_label = tk.Label(self.upload_frame, text="📷", font=('Arial', 48), 
                               bg='#ecf0f1', fg='#7f8c8d')
        upload_label.pack(pady=(50, 10))
        
        instruction_label = tk.Label(self.upload_frame, 
                                   text="Arraste e solte uma imagem aqui\nou clique para selecionar", 
                                   font=('Arial', 12), bg='#ecf0f1', fg='#2c3e50')
        instruction_label.pack(pady=10)
        
        # Botões de ação
        button_frame = tk.Frame(self.upload_frame, bg='#ecf0f1')
        button_frame.pack(pady=20)
        
        select_btn = tk.Button(button_frame, text="Selecionar Arquivo", 
                              command=self.select_file, font=('Arial', 10, 'bold'),
                              bg='#3498db', fg='white', padx=20, pady=10,
                              relief='flat', cursor='hand2')
        select_btn.pack(side='left', padx=5)
        
        paste_btn = tk.Button(button_frame, text="Colar Imagem (Ctrl+V)", 
                             command=self.paste_image, font=('Arial', 10, 'bold'),
                             bg='#2ecc71', fg='white', padx=20, pady=10,
                             relief='flat', cursor='hand2')
        paste_btn.pack(side='left', padx=5)
        
        # Frame para preview da imagem
        self.preview_frame = tk.Frame(left_frame, bg='white')
        
        # Canvas para imagem
        self.image_canvas = tk.Canvas(self.preview_frame, bg='white', width=400, height=300)
        self.image_canvas.pack(padx=20, pady=20)
        
        # Botão remover imagem
        remove_btn = tk.Button(self.preview_frame, text="Remover Imagem", 
                              command=self.remove_image, font=('Arial', 10),
                              bg='#e74c3c', fg='white', padx=15, pady=5,
                              relief='flat', cursor='hand2')
        remove_btn.pack(pady=(0, 20))
        
        # Frame direito - Resultados
        right_frame = tk.Frame(main_frame, bg='white', relief='raised', bd=2)
        right_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))
        
        # Abas para diferentes funcionalidades
        notebook = ttk.Notebook(right_frame)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Aba OCR
        ocr_frame = tk.Frame(notebook, bg='white')
        notebook.add(ocr_frame, text='Texto Extraído (OCR)')
        
        ocr_label = tk.Label(ocr_frame, text="Texto Extraído:", 
                            font=('Arial', 12, 'bold'), bg='white')
        ocr_label.pack(anchor='w', padx=10, pady=(10, 5))
        
        self.text_area = scrolledtext.ScrolledText(ocr_frame, wrap=tk.WORD, 
                                                  font=('Courier New', 10),
                                                  height=15, width=50)
        self.text_area.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Botões para texto
        text_button_frame = tk.Frame(ocr_frame, bg='white')
        text_button_frame.pack(fill='x', padx=10, pady=10)
        
        copy_btn = tk.Button(text_button_frame, text="Copiar Texto", 
                            command=self.copy_text, font=('Arial', 10),
                            bg='#9b59b6', fg='white', padx=15, pady=5,
                            relief='flat', cursor='hand2')
        copy_btn.pack(side='left', padx=5)
        
        save_btn = tk.Button(text_button_frame, text="Salvar como TXT", 
                            command=self.save_text, font=('Arial', 10),
                            bg='#f39c12', fg='white', padx=15, pady=5,
                            relief='flat', cursor='hand2')
        save_btn.pack(side='left', padx=5)
        
        # Aba YOLO
        yolo_frame = tk.Frame(notebook, bg='white')
        notebook.add(yolo_frame, text='Detecção de Objetos (YOLO)')
        
        yolo_label = tk.Label(yolo_frame, text="Objetos Detectados:", 
                             font=('Arial', 12, 'bold'), bg='white')
        yolo_label.pack(anchor='w', padx=10, pady=(10, 5))
        
        self.yolo_results = scrolledtext.ScrolledText(yolo_frame, wrap=tk.WORD, 
                                                     font=('Arial', 10),
                                                     height=15, width=50)
        self.yolo_results.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Barra de progresso
        self.progress_frame = tk.Frame(self.root, bg='#f0f0f0')
        
        self.progress_label = tk.Label(self.progress_frame, text="Pronto", 
                                      font=('Arial', 10), bg='#f0f0f0')
        self.progress_label.pack()
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode='indeterminate')
        self.progress_bar.pack(fill='x', padx=20, pady=5)
        
        # Bind eventos
        self.root.bind('<Control-v>', lambda e: self.paste_image())
        
    def load_yolo_model(self):
        """Carrega o modelo YOLO em thread separada"""
        def load_model():
            try:
                self.update_status("Carregando modelo YOLO...")
                self.yolo_model = YOLO('yolov8n.pt')
                self.update_status("Modelo YOLO carregado com sucesso!")
            except Exception as e:
                self.update_status(f"Erro ao carregar YOLO: {str(e)}")
        
        Thread(target=load_model, daemon=True).start()
    
    def load_ocr_model(self):
        """Carrega o modelo EasyOCR em thread separada"""
        def load_model():
            try:
                self.update_status("Carregando modelo OCR...")
                self.ocr_reader = easyocr.Reader(['pt', 'en'])  # português e inglês
                self.update_status("Modelo OCR carregado com sucesso!")
            except Exception as e:
                self.update_status(f"Erro ao carregar OCR: {str(e)}")
        
        Thread(target=load_model, daemon=True).start()
    
    def update_status(self, message):
        """Atualiza a barra de status"""
        self.progress_label.config(text=message)
        self.root.update()
    
    def on_drop(self, event):
        """Manipula arquivos arrastados"""
        files = self.root.tk.splitlist(event.data)
        if files:
            file_path = files[0]
            if self.is_image_file(file_path):
                self.load_image(file_path)
            else:
                messagebox.showerror("Erro", "Por favor, selecione um arquivo de imagem válido.")
    
    def select_file(self):
        """Abre diálogo para selecionar arquivo"""
        file_path = filedialog.askopenfilename(
            title="Selecionar Imagem",
            filetypes=[("Imagens", "*.png *.jpg *.jpeg *.gif *.bmp *.tiff *.webp")]
        )
        if file_path:
            self.load_image(file_path)
    
    def paste_image(self):
        """Cola imagem da área de transferência"""
        try:
            from PIL import ImageGrab
            image = ImageGrab.grabclipboard()
            if image:
                # Salva temporariamente
                temp_path = "temp_clipboard_image.png"
                image.save(temp_path)
                self.load_image(temp_path)
            else:
                messagebox.showinfo("Info", "Nenhuma imagem encontrada na área de transferência.")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao colar imagem: {str(e)}")
    
    def is_image_file(self, file_path):
        """Verifica se o arquivo é uma imagem"""
        valid_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp')
        return file_path.lower().endswith(valid_extensions)
    
    def load_image(self, file_path):
        """Carrega e exibe a imagem"""
        try:
            self.current_image_path = file_path
            
            # Carrega a imagem
            image = Image.open(file_path)
            self.current_image = image.copy()
            
            # Redimensiona para exibição
            display_image = image.copy()
            display_image.thumbnail((380, 280), Image.Resampling.LANCZOS)
            
            # Converte para PhotoImage
            self.photo = ImageTk.PhotoImage(display_image)
            
            # Exibe no canvas centralizada
            self.image_canvas.delete("all")
            # Força múltiplas atualizações do canvas para obter dimensões corretas
            self.image_canvas.update_idletasks()
            self.image_canvas.update()
            
            # Aguarda um momento para garantir que o canvas tenha as dimensões corretas
            self.root.after(10, lambda: self._center_image_on_canvas())
            
            # Mostra o frame de preview
            self.upload_frame.pack_forget()
            self.preview_frame.pack(fill='both', expand=True)
            self.progress_frame.pack(fill='x', pady=5)
            
            # Processa a imagem em thread separada
            Thread(target=self.process_image, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao carregar imagem: {str(e)}")
    
    def _center_image_on_canvas(self):
        """Centraliza a imagem no canvas após garantir que as dimensões estão corretas"""
        try:
            if hasattr(self, 'photo') and self.photo:
                canvas_width = self.image_canvas.winfo_width()
                canvas_height = self.image_canvas.winfo_height()
                
                # Se o canvas ainda não tem dimensões válidas, tenta novamente
                if canvas_width <= 1 or canvas_height <= 1:
                    self.root.after(50, lambda: self._center_image_on_canvas())
                    return
                
                # Centraliza a imagem no canvas
                x = canvas_width // 2
                y = canvas_height // 2
                self.image_canvas.create_image(x, y, anchor='center', image=self.photo)
        except Exception as e:
            print(f"Erro ao centralizar imagem: {e}")
    
    def remove_image(self):
        """Remove a imagem atual"""
        self.current_image = None
        self.current_image_path = None
        self.extracted_text = ""
        
        # Limpa as áreas de texto
        self.text_area.delete(1.0, tk.END)
        self.yolo_results.delete(1.0, tk.END)
        
        # Volta para a tela de upload
        self.preview_frame.pack_forget()
        self.progress_frame.pack_forget()
        self.upload_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        self.update_status("Pronto")
    
    def process_image(self):
        """Processa a imagem com YOLO e OCR"""
        if not self.current_image:
            return
        
        try:
            # OCR
            self.update_status("Extraindo texto da imagem...")
            self.progress_bar.start()
            
            # Converte PIL para OpenCV
            cv_image = cv2.cvtColor(np.array(self.current_image), cv2.COLOR_RGB2BGR)
            
            # OCR com EasyOCR
            if self.ocr_reader:
                # Converte PIL para numpy array
                img_array = np.array(self.current_image)
                results = self.ocr_reader.readtext(img_array)
                # Extrai apenas o texto dos resultados
                text = ' '.join([item[1] for item in results])
                self.extracted_text = text.strip()
            else:
                self.extracted_text = "Modelo OCR ainda não foi carregado. Aguarde..."
            
            # Atualiza a área de texto
            self.text_area.delete(1.0, tk.END)
            if self.extracted_text:
                self.text_area.insert(1.0, self.extracted_text)
            else:
                self.text_area.insert(1.0, "Nenhum texto encontrado na imagem.")
            
            # YOLO Detection
            if self.yolo_model:
                self.update_status("Detectando objetos...")
                
                results = self.yolo_model(cv_image)
                
                # Processa resultados
                detections = []
                for result in results:
                    boxes = result.boxes
                    if boxes is not None:
                        for box in boxes:
                            class_id = int(box.cls[0])
                            confidence = float(box.conf[0])
                            class_name = self.yolo_model.names[class_id]
                            
                            if confidence > 0.5:  # Threshold de confiança
                                detections.append(f"{class_name}: {confidence:.2f}")
                
                # Atualiza área YOLO
                self.yolo_results.delete(1.0, tk.END)
                if detections:
                    self.yolo_results.insert(1.0, "\n".join(detections))
                else:
                    self.yolo_results.insert(1.0, "Nenhum objeto detectado com confiança > 50%.")
            
            self.progress_bar.stop()
            self.update_status("Processamento concluído!")
            
        except Exception as e:
            self.progress_bar.stop()
            self.update_status("Erro no processamento")
            messagebox.showerror("Erro", f"Erro ao processar imagem: {str(e)}")
    
    def copy_text(self):
        """Copia o texto extraído"""
        if self.extracted_text:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.extracted_text)
            messagebox.showinfo("Sucesso", "Texto copiado para a área de transferência!")
        else:
            messagebox.showwarning("Aviso", "Nenhum texto para copiar.")
    
    def save_text(self):
        """Salva o texto em arquivo"""
        if self.extracted_text:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Arquivo de Texto", "*.txt")],
                title="Salvar Texto"
            )
            if file_path:
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(self.extracted_text)
                    messagebox.showinfo("Sucesso", f"Texto salvo em: {file_path}")
                except Exception as e:
                    messagebox.showerror("Erro", f"Erro ao salvar arquivo: {str(e)}")
        else:
            messagebox.showwarning("Aviso", "Nenhum texto para salvar.")

def main():
    root = TkinterDnD.Tk()
    app = ImageToTextApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()