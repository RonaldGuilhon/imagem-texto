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
import pickle
import json
from pathlib import Path

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
        
        # Variáveis para seleção de região
        self.selection_mode = False
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        self.selected_region = None
        
        # Variáveis de controle de zoom
        self.zoom_factor = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 5.0
        self.zoom_step = 0.1
        
        # Cache e configurações
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.config_file = self.cache_dir / "config.json"
        self.load_config()
        
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
        remove_btn.pack(pady=(0, 10))
        
        # Frame direito - Resultados
        right_frame = tk.Frame(main_frame, bg='white', relief='raised', bd=2)
        right_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))
        
        # Frame de controles
        controls_frame = tk.LabelFrame(right_frame, text="Controles", bg='white', font=('Arial', 10, 'bold'))
        controls_frame.pack(fill='x', padx=10, pady=(10, 5))
        
        # Seção 1: Botões de Área
        area_section = tk.Frame(controls_frame, bg='white')
        area_section.pack(fill='x', padx=8, pady=(8, 4))
        
        tk.Label(area_section, text="📍 Seleção de Área:", bg='white', font=('Arial', 9, 'bold')).pack(anchor='w')
        
        area_buttons_frame = tk.Frame(area_section, bg='white')
        area_buttons_frame.pack(fill='x', pady=(4, 0))
        
        self.select_region_btn = tk.Button(area_buttons_frame, text="Selecionar Área", command=self.toggle_region_selection,
                                           bg='#3498db', fg='white', relief='flat', cursor='hand2', font=('Arial', 9))
        self.select_region_btn.pack(side='left', fill='x', expand=True, padx=(0, 3))
        
        self.region_ocr_btn = tk.Button(area_buttons_frame, text="OCR da Região", command=self.process_region_ocr,
                                       bg='#e67e22', fg='white', relief='flat', cursor='hand2', font=('Arial', 9))
        self.region_ocr_btn.pack(side='right', fill='x', expand=True, padx=(3, 0))
        
        # Separador
        separator1 = tk.Frame(controls_frame, height=1, bg='#ddd')
        separator1.pack(fill='x', padx=8, pady=4)
        
        # Seção 2: Controles de Visualização
        view_section = tk.Frame(controls_frame, bg='white')
        view_section.pack(fill='x', padx=8, pady=4)
        
        tk.Label(view_section, text="🔍 Visualização:", bg='white', font=('Arial', 9, 'bold')).pack(anchor='w')
        
        # Zoom controls
        zoom_frame = tk.Frame(view_section, bg='white')
        zoom_frame.pack(fill='x', pady=(4, 0))
        
        tk.Label(zoom_frame, text="Zoom:", bg='white', font=('Arial', 9)).pack(side='left')
        
        self.zoom_label = tk.Label(zoom_frame, text="100%", bg='white', font=('Arial', 9, 'bold'))
        self.zoom_label.pack(side='left', padx=(8, 15))
        
        self.zoom_out_btn = tk.Button(zoom_frame, text="🔍-", command=self.zoom_out,
                                     bg='#e74c3c', fg='white', relief='flat', cursor='hand2', width=4, font=('Arial', 8))
        self.zoom_out_btn.pack(side='right', padx=(2, 0))
        
        self.zoom_reset_btn = tk.Button(zoom_frame, text="1:1", command=self.zoom_reset,
                                       bg='#95a5a6', fg='white', relief='flat', cursor='hand2', width=4, font=('Arial', 8))
        self.zoom_reset_btn.pack(side='right', padx=(2, 0))
        
        self.zoom_in_btn = tk.Button(zoom_frame, text="🔍+", command=self.zoom_in,
                                    bg='#27ae60', fg='white', relief='flat', cursor='hand2', width=4, font=('Arial', 8))
        self.zoom_in_btn.pack(side='right', padx=(2, 0))
        
        # Separador
        separator2 = tk.Frame(controls_frame, height=1, bg='#ddd')
        separator2.pack(fill='x', padx=8, pady=4)
        
        # Seção 3: Processamento
        process_section = tk.Frame(controls_frame, bg='white')
        process_section.pack(fill='x', padx=8, pady=4)
        
        tk.Label(process_section, text="⚡ Processamento:", bg='white', font=('Arial', 9, 'bold')).pack(anchor='w')
        
        process_frame = tk.Frame(process_section, bg='white')
        process_frame.pack(fill='x', pady=(4, 0))
        
        self.process_btn = tk.Button(process_frame, text="🔍 Processar Imagem", 
                                    command=lambda: Thread(target=self.process_image, daemon=True).start(),
                                    bg='#2ecc71', fg='white', relief='flat', cursor='hand2', 
                                    font=('Arial', 9, 'bold'), padx=20, pady=8)
        self.process_btn.pack(fill='x')
        
        # Separador
        separator3 = tk.Frame(controls_frame, height=1, bg='#ddd')
        separator3.pack(fill='x', padx=8, pady=4)
        
        # Seção 4: Rotação de Imagem
        rotation_section = tk.Frame(controls_frame, bg='white')
        rotation_section.pack(fill='x', padx=8, pady=4)
        
        tk.Label(rotation_section, text="🔄 Rotação:", bg='white', font=('Arial', 9, 'bold')).pack(anchor='w')
        
        # Botão de rotação automática
        auto_rotate_frame = tk.Frame(rotation_section, bg='white')
        auto_rotate_frame.pack(fill='x', pady=(4, 2))
        
        self.auto_rotate_btn = tk.Button(auto_rotate_frame, text="🔄 Auto Rotação", command=self.auto_rotate_image,
                                        bg='#9b59b6', fg='white', relief='flat', cursor='hand2', font=('Arial', 9))
        self.auto_rotate_btn.pack(fill='x')
        
        # Botões de rotação manual
        manual_rotate_frame = tk.Frame(rotation_section, bg='white')
        manual_rotate_frame.pack(fill='x', pady=(2, 0))
        
        tk.Label(manual_rotate_frame, text="Manual:", bg='white', font=('Arial', 8)).pack(side='left')
        
        self.rotate_left_btn = tk.Button(manual_rotate_frame, text="↺ 90°", 
                                        command=lambda: self.manual_rotate_image(90),
                                        bg='#e67e22', fg='white', relief='flat', cursor='hand2', 
                                        width=6, font=('Arial', 8))
        self.rotate_left_btn.pack(side='right', padx=(2, 0))
        
        self.rotate_180_btn = tk.Button(manual_rotate_frame, text="↻ 180°", 
                                       command=lambda: self.manual_rotate_image(180),
                                       bg='#e74c3c', fg='white', relief='flat', cursor='hand2', 
                                       width=6, font=('Arial', 8))
        self.rotate_180_btn.pack(side='right', padx=(2, 0))
        
        self.rotate_right_btn = tk.Button(manual_rotate_frame, text="↻ 90°", 
                                         command=lambda: self.manual_rotate_image(-90),
                                         bg='#f39c12', fg='white', relief='flat', cursor='hand2', 
                                         width=6, font=('Arial', 8))
        self.rotate_right_btn.pack(side='right', padx=(2, 0))
        
        # Separador
        separator3 = tk.Frame(controls_frame, height=1, bg='#ddd')
        separator3.pack(fill='x', padx=8, pady=4)
        
        # Seção 5: Configurações
        config_section = tk.Frame(controls_frame, bg='white')
        config_section.pack(fill='x', padx=8, pady=(4, 8))
        
        tk.Label(config_section, text="⚙️ Configurações:", bg='white', font=('Arial', 9, 'bold')).pack(anchor='w')
        
        theme_frame = tk.Frame(config_section, bg='white')
        theme_frame.pack(fill='x', pady=(4, 0))
        
        tk.Label(theme_frame, text="Tema:", bg='white', font=('Arial', 9)).pack(side='left')
        self.theme_btn = tk.Button(theme_frame, text="🌙 Escuro", command=self.toggle_theme,
                                  bg='#34495e', fg='white', relief='flat', cursor='hand2', font=('Arial', 9))
        self.theme_btn.pack(side='right')
        
        # Configuração de rotação automática
        rotation_config_frame = tk.Frame(config_section, bg='white')
        rotation_config_frame.pack(fill='x', pady=(4, 0))
        
        tk.Label(rotation_config_frame, text="Rotação Automática:", bg='white', font=('Arial', 9)).pack(side='left')
        self.auto_rotation_var = tk.BooleanVar(value=self.config.get('auto_rotation', True))
        self.auto_rotation_check = tk.Checkbutton(rotation_config_frame, variable=self.auto_rotation_var,
                                                 command=self.toggle_auto_rotation, bg='white', font=('Arial', 9))
        self.auto_rotation_check.pack(side='right')
        
        # Aplica tema inicial
        self.apply_theme()
        
        # Abas para diferentes funcionalidades
        notebook = ttk.Notebook(right_frame)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Aba OCR
        ocr_frame = tk.Frame(notebook, bg='white')
        notebook.add(ocr_frame, text='Texto Extraído (OCR)')
        
        ocr_label = tk.Label(ocr_frame, text="Texto Extraído:", 
                            font=('Arial', 12, 'bold'), bg='white')
        ocr_label.pack(anchor='w', padx=10, pady=(10, 5))
        
        # Frame para confiança do OCR
        confidence_frame = tk.Frame(ocr_frame, bg='white')
        confidence_frame.pack(fill='x', padx=10, pady=(0, 5))
        
        tk.Label(confidence_frame, text="Confiança:", bg='white').pack(side='left')
        
        self.confidence_var = tk.StringVar(value="N/A")
        self.confidence_label = tk.Label(confidence_frame, textvariable=self.confidence_var, bg='white')
        self.confidence_label.pack(side='right')
        
        # Barra de progresso para confiança
        self.confidence_progress = ttk.Progressbar(confidence_frame, length=100, mode='determinate')
        self.confidence_progress.pack(side='right', padx=(5, 10))
        
        self.text_area = scrolledtext.ScrolledText(ocr_frame, wrap=tk.WORD, 
                                                  font=('Consolas', 11),
                                                  height=15, width=50,
                                                  bg='#f8f9fa', fg='#2c3e50',
                                                  insertbackground='#3498db',
                                                  selectbackground='#3498db',
                                                  selectforeground='white',
                                                  relief='flat',
                                                  borderwidth=1,
                                                  highlightthickness=1,
                                                  highlightcolor='#3498db',
                                                  highlightbackground='#bdc3c7')
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
        
        # Bind eventos do canvas para seleção de região
        self.image_canvas.bind('<Button-1>', self.on_canvas_click)
        self.image_canvas.bind('<B1-Motion>', self.on_canvas_drag)
        self.image_canvas.bind('<ButtonRelease-1>', self.on_canvas_release)
    
    def load_config(self):
        """Carrega configurações do arquivo"""
        default_config = {
            "ocr_languages": ["pt", "en"],
            "selected_language": "pt",
            "theme": "light",
            "cache_models": True,
            "show_confidence": True,
            "auto_rotation": True
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                # Merge com configurações padrão
                for key, value in default_config.items():
                    if key not in self.config:
                        self.config[key] = value
            except Exception as e:
                print(f"Erro ao carregar config: {e}")
                self.config = default_config
        else:
            self.config = default_config
            self.save_config()
    
    def save_config(self):
        """Salva configurações no arquivo"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar config: {e}")
    
    def get_model_cache_path(self, model_type):
        """Retorna o caminho do cache para um modelo"""
        return self.cache_dir / f"{model_type}_model.pkl"
    
    def load_cached_model(self, model_type):
        """Carrega modelo do cache se existir"""
        if not self.config.get("cache_models", True):
            return None
            
        cache_path = self.get_model_cache_path(model_type)
        if cache_path.exists():
            try:
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"Erro ao carregar cache {model_type}: {e}")
                # Remove cache corrompido
                cache_path.unlink(missing_ok=True)
        return None
    
    def save_model_to_cache(self, model, model_type):
        """Salva modelo no cache"""
        if not self.config.get("cache_models", True):
            return
            
        cache_path = self.get_model_cache_path(model_type)
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(model, f)
        except Exception as e:
            print(f"Erro ao salvar cache {model_type}: {e}")
    

    
    def toggle_region_selection(self):
        """Ativa/desativa modo de seleção de região"""
        self.selection_mode = not self.selection_mode
        
        if self.selection_mode:
            self.region_btn.config(text="Cancelar Seleção", bg='#e74c3c')
            self.update_status("Modo seleção ativo - clique e arraste para selecionar região")
            # Limpa seleção anterior
            if self.rect_id:
                self.image_canvas.delete(self.rect_id)
                self.rect_id = None
            self.selected_region = None
            self.region_ocr_btn.config(state='disabled')
        else:
            self.region_btn.config(text="Selecionar Região", bg='#9b59b6')
            self.update_status("Modo seleção desativado")
    
    def on_canvas_click(self, event):
        """Inicia seleção de região"""
        if not self.selection_mode:
            return
            
        self.start_x = event.x
        self.start_y = event.y
        
        # Remove retângulo anterior
        if self.rect_id:
            self.image_canvas.delete(self.rect_id)
    
    def on_canvas_drag(self, event):
        """Atualiza seleção durante arraste"""
        if not self.selection_mode or self.start_x is None:
            return
            
        # Remove retângulo anterior
        if self.rect_id:
            self.image_canvas.delete(self.rect_id)
            
        # Desenha novo retângulo
        self.rect_id = self.image_canvas.create_rectangle(
            self.start_x, self.start_y, event.x, event.y,
            outline='red', width=2, dash=(5, 5)
        )
    
    def on_canvas_release(self, event):
        """Finaliza seleção de região"""
        if not self.selection_mode or self.start_x is None:
            return
            
        end_x = event.x
        end_y = event.y
        
        # Calcula coordenadas da região selecionada
        if abs(end_x - self.start_x) > 10 and abs(end_y - self.start_y) > 10:
            # Converte coordenadas do canvas para coordenadas da imagem
            self.selected_region = self.canvas_to_image_coords(
                min(self.start_x, end_x), min(self.start_y, end_y),
                max(self.start_x, end_x), max(self.start_y, end_y)
            )
            
            if self.selected_region:
                self.region_ocr_btn.config(state='normal')
                self.update_status("Região selecionada - clique em 'OCR da Região' para processar")
            else:
                self.update_status("Região inválida - tente novamente")
        else:
            # Seleção muito pequena
            if self.rect_id:
                self.image_canvas.delete(self.rect_id)
                self.rect_id = None
            self.update_status("Seleção muito pequena - tente novamente")
    
    def canvas_to_image_coords(self, x1, y1, x2, y2):
        """Converte coordenadas do canvas para coordenadas da imagem"""
        if not hasattr(self, 'current_image') or not self.current_image:
            return None
            
        canvas_width = 400
        canvas_height = 300
        
        img_width, img_height = self.current_image.size
        ratio = min(canvas_width/img_width, canvas_height/img_height)
        
        new_width = int(img_width * ratio)
        new_height = int(img_height * ratio)
        
        # Offset da imagem no canvas
        offset_x = (canvas_width - new_width) // 2
        offset_y = (canvas_height - new_height) // 2
        
        # Ajusta coordenadas
        x1 = max(0, x1 - offset_x)
        y1 = max(0, y1 - offset_y)
        x2 = min(new_width, x2 - offset_x)
        y2 = min(new_height, y2 - offset_y)
        
        # Converte para coordenadas da imagem original
        img_x1 = int(x1 / ratio)
        img_y1 = int(y1 / ratio)
        img_x2 = int(x2 / ratio)
        img_y2 = int(y2 / ratio)
        
        # Garante que as coordenadas estão dentro da imagem
        img_x1 = max(0, min(img_x1, img_width))
        img_y1 = max(0, min(img_y1, img_height))
        img_x2 = max(0, min(img_x2, img_width))
        img_y2 = max(0, min(img_y2, img_height))
        
        if img_x2 > img_x1 and img_y2 > img_y1:
            return (img_x1, img_y1, img_x2, img_y2)
        return None
    
    def process_region_ocr(self):
        """Processa OCR apenas na região selecionada"""
        # Verifica se há imagem carregada
        if not hasattr(self, 'current_image') or not self.current_image:
            messagebox.showwarning("Aviso", "Nenhuma imagem carregada!")
            return
            
        # Verifica se há região selecionada
        if not self.selected_region:
            messagebox.showwarning("Aviso", "Nenhuma região selecionada! Clique em 'Selecionar Área' e desenhe uma região na imagem.")
            return
            
        # Verifica se o OCR está carregado, se não, carrega
        if not hasattr(self, 'ocr_reader') or not self.ocr_reader:
            messagebox.showinfo("Carregando OCR", "Modelo OCR não está carregado. Carregando agora...")
            self.load_ocr_model()
            # Agenda nova tentativa após 3 segundos
            self.root.after(3000, self.process_region_ocr)
            return
        
        def process():
            try:
                self.update_status("Processando OCR da região selecionada...")
                
                # Recorta a região da imagem
                x1, y1, x2, y2 = self.selected_region
                region_image = self.current_image.crop((x1, y1, x2, y2))
                
                # Debug: informações da região selecionada
                region_width = x2 - x1
                region_height = y2 - y1
                print(f"[DEBUG OCR] Região selecionada: {x1},{y1} -> {x2},{y2} (tamanho: {region_width}x{region_height})")
                
                # Pré-processamento da região para melhorar OCR
                processed_image = self.preprocess_region_for_ocr(region_image)
                print(f"[DEBUG OCR] Pré-processamento concluído. Forma da imagem processada: {processed_image.shape}")
                
                # Processa OCR com múltiplas tentativas
                ocr_results = self.perform_ocr_with_fallback(processed_image, region_image)
                print(f"[DEBUG OCR] OCR concluído. Resultados encontrados: {len(ocr_results)}")
                
                # Debug: detalhes dos resultados
                for i, (bbox, text, confidence) in enumerate(ocr_results):
                    print(f"[DEBUG OCR] Resultado {i+1}: '{text}' (confiança: {confidence:.3f})")
                
                # Processa resultados
                extracted_text = ""
                confidence_info = ""
                confidences = []
                for (bbox, text, confidence) in ocr_results:
                    extracted_text += text + "\n"
                    confidences.append(confidence)
                    if self.config.get("show_confidence", True):
                        confidence_info += f"{text}: {confidence:.2f}\n"
                
                # Calcula confiança média
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                
                # Atualiza interface
                self.root.after(0, lambda: self.text_area.delete(1.0, tk.END))
                self.root.after(0, lambda: self.text_area.insert(1.0, f"[REGIÃO SELECIONADA]\n{extracted_text}"))
                
                # Atualiza confiança
                self.root.after(0, lambda: self.confidence_var.set(f"{avg_confidence:.1%}"))
                self.root.after(0, lambda: self.confidence_progress.config(value=avg_confidence*100))
                
                self.update_status("OCR da região concluído!")
                
            except Exception as e:
                self.update_status(f"Erro no OCR da região: {str(e)}")
                messagebox.showerror("Erro", f"Erro no OCR da região: {e}")
        
        thread = Thread(target=process)
        thread.daemon = True
        thread.start()
    
    def preprocess_region_for_ocr(self, region_image):
        """Aplica pré-processamento na região para melhorar a detecção de OCR"""
        try:
            # Converte PIL para OpenCV
            img_array = np.array(region_image)
            print(f"[DEBUG PREPROC] Imagem original: {img_array.shape}")
            
            # Se a imagem for muito pequena, redimensiona
            height, width = img_array.shape[:2]
            if height < 50 or width < 50:
                scale_factor = max(50/height, 50/width, 2.0)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                img_array = cv2.resize(img_array, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
                print(f"[DEBUG PREPROC] Imagem redimensionada: {img_array.shape} (fator: {scale_factor:.2f})")
            
            # Converte para escala de cinza se necessário
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array.copy()
            
            # Aplica filtro de desfoque gaussiano para reduzir ruído
            denoised = cv2.GaussianBlur(gray, (3, 3), 0)
            
            # Melhora o contraste usando CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)
            
            # Aplica sharpening para melhorar a definição do texto
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            sharpened = cv2.filter2D(enhanced, -1, kernel)
            
            return sharpened
            
        except Exception as e:
            print(f"Erro no pré-processamento: {e}")
            # Retorna a imagem original em caso de erro
            return np.array(region_image)
    
    def perform_ocr_with_fallback(self, processed_image, original_image):
        """Executa OCR com múltiplas estratégias de fallback"""
        try:
            # Primeira tentativa: imagem pré-processada
            print(f"[DEBUG FALLBACK] Tentativa 1: imagem pré-processada")
            results = self.ocr_reader.readtext(processed_image)
            print(f"[DEBUG FALLBACK] Tentativa 1 - Resultados: {len(results)}")
            
            # Se não encontrou texto suficiente, tenta com binarização
            if len(results) == 0 or (len(results) == 1 and len(results[0][1].strip()) < 2):
                print(f"[DEBUG FALLBACK] Poucos resultados, tentando binarização adaptativa")
                # Aplica binarização adaptativa
                if len(processed_image.shape) == 3:
                    gray = cv2.cvtColor(processed_image, cv2.COLOR_RGB2GRAY)
                else:
                    gray = processed_image
                
                # Binarização adaptativa
                binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
                results_binary = self.ocr_reader.readtext(binary)
                print(f"[DEBUG FALLBACK] Binarização adaptativa - Resultados: {len(results_binary)}")
                
                if len(results_binary) > len(results):
                    results = results_binary
                    print(f"[DEBUG FALLBACK] Usando resultados da binarização adaptativa")
                
                # Se ainda não encontrou, tenta com a imagem original
                if len(results) == 0:
                    print(f"[DEBUG FALLBACK] Tentando com imagem original")
                    original_array = np.array(original_image)
                    results = self.ocr_reader.readtext(original_array)
                    print(f"[DEBUG FALLBACK] Imagem original - Resultados: {len(results)}")
                
                # Última tentativa: binarização simples
                if len(results) == 0:
                    print(f"[DEBUG FALLBACK] Última tentativa: binarização OTSU")
                    _, binary_simple = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    results = self.ocr_reader.readtext(binary_simple)
                    print(f"[DEBUG FALLBACK] Binarização OTSU - Resultados: {len(results)}")
            
            return results
            
        except Exception as e:
            print(f"Erro no OCR com fallback: {e}")
            # Fallback final: OCR na imagem original
            try:
                return self.ocr_reader.readtext(np.array(original_image))
            except:
                return []
    
    def toggle_theme(self):
        """Alterna entre tema claro e escuro"""
        current_theme = self.config.get("theme", "light")
        new_theme = "dark" if current_theme == "light" else "light"
        
        self.config["theme"] = new_theme
        self.save_config()
        self.apply_theme()
    
    def toggle_auto_rotation(self):
        """Alterna a configuração de rotação automática"""
        self.config["auto_rotation"] = self.auto_rotation_var.get()
        self.save_config()
        print(f"Rotação automática: {'Ativada' if self.config['auto_rotation'] else 'Desativada'}")
    
    def apply_theme(self):
        """Aplica o tema atual à interface"""
        theme = self.config.get("theme", "light")
        
        if theme == "dark":
            # Cores do tema escuro
            bg_color = "#2c3e50"
            fg_color = "#ecf0f1"
            frame_bg = "#34495e"
            text_bg = "#2c3e50"
            text_fg = "#ecf0f1"
            button_bg = "#3498db"
            canvas_bg = "#34495e"
            
            self.theme_btn.config(text="☀️ Claro", bg="#f39c12")
        else:
            # Cores do tema claro
            bg_color = "white"
            fg_color = "black"
            frame_bg = "white"
            text_bg = "white"
            text_fg = "black"
            button_bg = "#3498db"
            canvas_bg = "white"
            
            self.theme_btn.config(text="🌙 Escuro", bg="#34495e")
        
        # Aplica cores aos widgets principais
        try:
            self.root.config(bg=bg_color)
            
            # Atualiza frames principais
            for widget in self.root.winfo_children():
                if isinstance(widget, (tk.Frame, tk.LabelFrame)):
                    widget.config(bg=frame_bg)
                    if hasattr(widget, 'config') and 'fg' in widget.keys():
                        widget.config(fg=fg_color)
            
            # Atualiza canvas
            if hasattr(self, 'image_canvas'):
                self.image_canvas.config(bg=canvas_bg)
            
            # Atualiza áreas de texto
            if hasattr(self, 'ocr_text'):
                self.ocr_text.config(bg=text_bg, fg=text_fg, insertbackground=text_fg)
            if hasattr(self, 'yolo_text'):
                self.yolo_text.config(bg=text_bg, fg=text_fg, insertbackground=text_fg)
            
            # Atualiza labels recursivamente
            self.update_widget_colors(self.root, bg_color, fg_color, frame_bg, text_bg, text_fg)
            
        except Exception as e:
            print(f"Erro ao aplicar tema: {e}")
    
    def update_widget_colors(self, parent, bg_color, fg_color, frame_bg, text_bg, text_fg):
        """Atualiza cores dos widgets recursivamente"""
        for child in parent.winfo_children():
            try:
                widget_class = child.winfo_class()
                
                if widget_class in ['Frame', 'LabelFrame']:
                    child.config(bg=frame_bg)
                    if 'fg' in child.keys():
                        child.config(fg=fg_color)
                elif widget_class == 'Label':
                    child.config(bg=frame_bg, fg=fg_color)
                elif widget_class == 'Text':
                    child.config(bg=text_bg, fg=text_fg, insertbackground=text_fg)
                elif widget_class == 'Canvas':
                    child.config(bg=frame_bg)
                
                # Recursão para widgets filhos
                self.update_widget_colors(child, bg_color, fg_color, frame_bg, text_bg, text_fg)
                
            except Exception as e:
                # Ignora erros de widgets que não suportam certas configurações
                 pass
    
    def zoom_in(self):
        """Aumenta o zoom da imagem"""
        if self.zoom_factor < self.max_zoom:
            self.zoom_factor = min(self.zoom_factor + self.zoom_step, self.max_zoom)
            self.update_zoom_display()
    
    def zoom_out(self):
        """Diminui o zoom da imagem"""
        if self.zoom_factor > self.min_zoom:
            self.zoom_factor = max(self.zoom_factor - self.zoom_step, self.min_zoom)
            self.update_zoom_display()
    
    def zoom_reset(self):
        """Reseta o zoom para 100%"""
        self.zoom_factor = 1.0
        self.update_zoom_display()
    
    def update_zoom_display(self):
        """Atualiza a exibição da imagem com o zoom atual"""
        # Atualiza o label do zoom
        zoom_percent = int(self.zoom_factor * 100)
        self.zoom_label.config(text=f"{zoom_percent}%")
        
        # Re-exibe a imagem com o novo zoom
        if hasattr(self, 'current_image') and self.current_image is not None:
            self.update_image_preview()
        
    def load_yolo_model(self):
        """Carrega o modelo YOLO em thread separada"""
        def load_model():
            try:
                # Tenta carregar do cache primeiro
                cached_model = self.load_cached_model("yolo")
                if cached_model:
                    self.yolo_model = cached_model
                    self.update_status("Modelo YOLO carregado do cache!")
                else:
                    self.update_status("Carregando modelo YOLO...")
                    self.yolo_model = YOLO('yolov8n.pt')
                    # Salva no cache para próximas execuções
                    self.save_model_to_cache(self.yolo_model, "yolo")
                    self.update_status("Modelo YOLO carregado e salvo no cache!")
            except Exception as e:
                self.update_status(f"Erro ao carregar YOLO: {str(e)}")
        
        Thread(target=load_model, daemon=True).start()
    
    def load_ocr_model(self):
        """Carrega o modelo EasyOCR em thread separada"""
        def load_model():
            try:
                # Desabilita botão OCR durante carregamento
                self.root.after(0, lambda: self.region_ocr_btn.config(state='disabled', text='Carregando OCR...'))
                
                # Tenta carregar do cache primeiro
                cached_model = self.load_cached_model("ocr")
                if cached_model:
                    self.ocr_reader = cached_model
                    self.update_status("Modelo OCR carregado do cache!")
                else:
                    self.update_status("Carregando modelo OCR...")
                    languages = self.config.get("ocr_languages", ['pt', 'en'])
                    self.ocr_reader = easyocr.Reader(languages)
                    # Salva no cache para próximas execuções
                    self.save_model_to_cache(self.ocr_reader, "ocr")
                    self.update_status("Modelo OCR carregado e salvo no cache!")
                
                # Reabilita botão OCR após carregamento
                self.root.after(0, lambda: self.region_ocr_btn.config(state='normal', text='OCR da Região'))
                
            except Exception as e:
                self.update_status(f"Erro ao carregar OCR: {str(e)}")
                # Reabilita botão mesmo em caso de erro
                self.root.after(0, lambda: self.region_ocr_btn.config(state='normal', text='OCR da Região'))
        
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
                self.original_image = image
                self.current_image = image.copy()
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
            self.original_image = image.copy()
            self.current_image = image.copy()
            
            # Verifica se é imagem colada (arquivo temporário)
            is_pasted_image = file_path == "temp_clipboard_image.png"
            
            # Para imagens coladas, mantém tamanho real; para arquivos, redimensiona
            if is_pasted_image:
                display_image = image.copy()  # Mantém tamanho real
                # Ajusta o canvas para acomodar a imagem
                img_width, img_height = display_image.size
                canvas_width = min(800, img_width + 40)  # Máximo 800px de largura
                canvas_height = min(600, img_height + 40)  # Máximo 600px de altura
                self.image_canvas.config(width=canvas_width, height=canvas_height)
            else:
                display_image = image.copy()
                display_image.thumbnail((380, 280), Image.Resampling.LANCZOS)
                # Restaura tamanho padrão do canvas para arquivos
                self.image_canvas.config(width=400, height=300)
            
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
    
    def display_image(self):
        """Exibe a imagem no canvas"""
        if hasattr(self, 'current_image') and self.current_image:
            self.update_image_preview()
    
    def update_image_preview(self):
        """Atualiza o preview da imagem no canvas com zoom e centralização aprimorada"""
        if not hasattr(self, 'current_image') or self.current_image is None:
            return
            
        # Obtém as dimensões reais do canvas
        canvas_width = self.image_canvas.winfo_width()
        canvas_height = self.image_canvas.winfo_height()
        
        # Se o canvas ainda não foi renderizado, usa dimensões padrão e reagenda
        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width = 400
            canvas_height = 300
            self.root.after(50, self.update_image_preview)
        
        img_width, img_height = self.current_image.size
        base_ratio = min(canvas_width/img_width, canvas_height/img_height)
        
        # Aplica o zoom ao fator de escala
        final_ratio = base_ratio * self.zoom_factor
        
        new_width = int(img_width * final_ratio)
        new_height = int(img_height * final_ratio)
        
        resized_image = self.current_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(resized_image)
        
        # Limpa o canvas e centraliza a imagem perfeitamente
        self.image_canvas.delete("all")
        
        # Centralização perfeita usando o centro do canvas
        center_x = canvas_width // 2
        center_y = canvas_height // 2
        
        # Cria a imagem centralizada usando anchor='center'
        self.image_canvas.create_image(center_x, center_y, anchor='center', image=self.photo)
        
        # Armazena as dimensões para uso posterior (ajustado para centralização)
        self.display_scale = final_ratio
        self.display_offset_x = (canvas_width - new_width) // 2
        self.display_offset_y = (canvas_height - new_height) // 2
    
    # Funcionalidade de seleção de área removida
    
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
    
    def format_extracted_text(self, ocr_results):
        """Formata o texto extraído de forma estruturada e organizada"""
        if not ocr_results:
            return "Nenhum texto encontrado na imagem."
        
        # Organiza os resultados por posição vertical (linha)
        sorted_results = sorted(ocr_results, key=lambda x: x[0][0][1])  # Ordena por coordenada Y
        
        formatted_text = ""
        current_line_y = None
        line_tolerance = 20  # Tolerância para considerar textos na mesma linha
        current_line_texts = []
        
        for bbox, text, confidence in sorted_results:
            # Pega a coordenada Y do centro do texto
            text_y = (bbox[0][1] + bbox[2][1]) / 2
            
            # Se é uma nova linha ou primeira iteração
            if current_line_y is None or abs(text_y - current_line_y) > line_tolerance:
                # Processa a linha anterior se existir
                if current_line_texts:
                    # Ordena textos da linha por posição X
                    current_line_texts.sort(key=lambda x: x[1])  # Ordena por X
                    line_text = " ".join([t[0] for t in current_line_texts])
                    formatted_text += line_text.strip() + "\n"
                
                # Inicia nova linha
                current_line_y = text_y
                current_line_texts = [(text.strip(), bbox[0][0])]  # (texto, coordenada X)
            else:
                # Adiciona à linha atual
                current_line_texts.append((text.strip(), bbox[0][0]))
        
        # Processa a última linha
        if current_line_texts:
            current_line_texts.sort(key=lambda x: x[1])
            line_text = " ".join([t[0] for t in current_line_texts])
            formatted_text += line_text.strip() + "\n"
        
        # Remove linhas vazias e espaços extras
        lines = [line.strip() for line in formatted_text.split('\n') if line.strip()]
        
        # Junta linhas que parecem ser continuação (heurística simples)
        final_lines = []
        for i, line in enumerate(lines):
            if i == 0:
                final_lines.append(line)
            else:
                # Se a linha anterior não termina com pontuação e a atual não começa com maiúscula
                prev_line = final_lines[-1]
                if (not prev_line.endswith(('.', '!', '?', ':', ';')) and 
                    line and not line[0].isupper() and 
                    len(prev_line) > 0):
                    # Junta com a linha anterior
                    final_lines[-1] = prev_line + " " + line
                else:
                    final_lines.append(line)
        
        return "\n".join(final_lines) if final_lines else "Nenhum texto encontrado na imagem."
    
    def add_text_metadata(self, formatted_text, ocr_results, avg_confidence):
        """Adiciona metadados úteis ao texto extraído"""
        if not ocr_results:
            return formatted_text
        
        metadata = []
        metadata.append("=" * 50)
        metadata.append("TEXTO EXTRAÍDO")
        metadata.append("=" * 50)
        metadata.append("")
        
        # Adiciona o texto formatado
        text_lines = formatted_text.split('\n')
        for line in text_lines:
            if line.strip():
                metadata.append(line)
        
        metadata.append("")
        metadata.append("-" * 50)
        metadata.append("INFORMAÇÕES TÉCNICAS")
        metadata.append("-" * 50)
        metadata.append(f"• Blocos de texto detectados: {len(ocr_results)}")
        metadata.append(f"• Confiança média: {avg_confidence:.1%}")
        
        # Estatísticas de confiança
        confidences = [conf for _, _, conf in ocr_results]
        if confidences:
            metadata.append(f"• Confiança mínima: {min(confidences):.1%}")
            metadata.append(f"• Confiança máxima: {max(confidences):.1%}")
        
        # Contagem de caracteres e palavras
        clean_text = formatted_text.replace('\n', ' ').strip()
        word_count = len(clean_text.split()) if clean_text else 0
        char_count = len(clean_text)
        
        metadata.append(f"• Total de palavras: {word_count}")
        metadata.append(f"• Total de caracteres: {char_count}")
        
        return "\n".join(metadata)
    
    def detect_and_correct_rotation(self, image):
        """Detecta e corrige automaticamente a rotação da imagem para melhor OCR"""
        try:
            # Converte PIL para OpenCV se necessário
            if hasattr(image, 'mode'):  # PIL Image
                cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            else:  # Já é numpy array
                cv_image = image
            
            # Converte para escala de cinza
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Aplica threshold para binarizar
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Detecta linhas usando Hough Transform com parâmetros mais rigorosos
            edges = cv2.Canny(binary, 50, 150, apertureSize=3)
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=200)  # Threshold aumentado
            
            if lines is not None and len(lines) >= 10:  # Precisa de pelo menos 10 linhas
                angles = []
                for line in lines[:30]:  # Analisa mais linhas para melhor precisão
                    rho, theta = line[0]
                    angle = theta * 180 / np.pi
                    # Normaliza o ângulo para -90 a 90 graus
                    if angle > 90:
                        angle = angle - 180
                    elif angle < -90:
                        angle = angle + 180
                    angles.append(angle)
                
                if len(angles) >= 10:  # Precisa de pelo menos 10 ângulos válidos
                    # Filtra outliers usando desvio padrão
                    angles_array = np.array(angles)
                    mean_angle = np.mean(angles_array)
                    std_angle = np.std(angles_array)
                    
                    # Remove outliers (ângulos muito distantes da média)
                    filtered_angles = angles_array[np.abs(angles_array - mean_angle) <= 2 * std_angle]
                    
                    if len(filtered_angles) >= 5:  # Precisa de pelo menos 5 ângulos após filtragem
                        # Calcula o ângulo médio dos dados filtrados
                        median_angle = np.median(filtered_angles)
                        
                        # Só corrige se o ângulo for significativo (> 3 graus) e consistente
                        if abs(median_angle) > 3 and std_angle < 15:  # Threshold aumentado e verifica consistência
                            print(f"[DEBUG] Rotação detectada: {median_angle:.2f}° (std: {std_angle:.2f}°)")
                            
                            # Rotaciona a imagem
                            if hasattr(image, 'mode'):  # PIL Image
                                corrected_image = image.rotate(-median_angle, expand=True, fillcolor='white')
                                return corrected_image, median_angle
                            else:
                                # Para numpy array
                                height, width = cv_image.shape[:2]
                                center = (width // 2, height // 2)
                                rotation_matrix = cv2.getRotationMatrix2D(center, -median_angle, 1.0)
                                
                                # Calcula novas dimensões
                                cos_angle = abs(rotation_matrix[0, 0])
                                sin_angle = abs(rotation_matrix[0, 1])
                                new_width = int((height * sin_angle) + (width * cos_angle))
                                new_height = int((height * cos_angle) + (width * sin_angle))
                                
                                # Ajusta a matriz de rotação
                                rotation_matrix[0, 2] += (new_width / 2) - center[0]
                                rotation_matrix[1, 2] += (new_height / 2) - center[1]
                                
                                rotated = cv2.warpAffine(cv_image, rotation_matrix, (new_width, new_height), 
                                                       borderValue=(255, 255, 255))
                                
                                # Converte de volta para PIL
                                corrected_image = Image.fromarray(cv2.cvtColor(rotated, cv2.COLOR_BGR2RGB))
                                return corrected_image, median_angle
                        else:
                            print(f"[DEBUG] Rotação não significativa: {median_angle:.2f}° (std: {std_angle:.2f}°)")
                    else:
                        print(f"[DEBUG] Poucos ângulos válidos após filtragem: {len(filtered_angles)}")
                else:
                    print(f"[DEBUG] Poucos ângulos detectados: {len(angles)}")
            else:
                print(f"[DEBUG] Poucas linhas detectadas: {len(lines) if lines is not None else 0}")
            
            # Se não detectou rotação significativa, retorna a imagem original
            return image, 0
            
        except Exception as e:
            print(f"[DEBUG] Erro na detecção de rotação: {e}")
            return image, 0
    
    def auto_rotate_image(self):
        """Aplica correção automática de rotação na imagem atual"""
        if not hasattr(self, 'current_image') or not self.current_image:
            messagebox.showwarning("Aviso", "Nenhuma imagem carregada.")
            return
        
        try:
            self.update_status("Detectando rotação da imagem...")
            
            # Detecta e corrige rotação
            corrected_image, rotation_angle = self.detect_and_correct_rotation(self.current_image)
            
            if abs(rotation_angle) > 1:
                # Atualiza a imagem atual
                self.current_image = corrected_image
                
                # Atualiza a visualização
                self.display_image()
                
                self.update_status(f"Imagem rotacionada em {-rotation_angle:.1f}° automaticamente")
                messagebox.showinfo("Sucesso", f"Rotação corrigida automaticamente: {-rotation_angle:.1f}°")
            else:
                self.update_status("Nenhuma rotação significativa detectada")
                messagebox.showinfo("Info", "A imagem já está com orientação adequada.")
                
        except Exception as e:
            self.update_status("Erro na correção automática")
            messagebox.showerror("Erro", f"Erro ao corrigir rotação: {str(e)}")
    
    def manual_rotate_image(self, angle):
        """Rotaciona manualmente a imagem pelo ângulo especificado"""
        if not hasattr(self, 'current_image') or not self.current_image:
            messagebox.showwarning("Aviso", "Nenhuma imagem carregada.")
            return
        
        try:
            # Rotaciona a imagem
            rotated_image = self.current_image.rotate(angle, expand=True, fillcolor='white')
            
            # Atualiza a imagem atual
            self.current_image = rotated_image
            
            # Atualiza a visualização
            self.display_image()
            
            self.update_status(f"Imagem rotacionada em {angle}°")
            
        except Exception as e:
            self.update_status("Erro na rotação manual")
            messagebox.showerror("Erro", f"Erro ao rotacionar imagem: {str(e)}")
    
    def process_image(self):
        """Processa a imagem com YOLO e OCR"""
        if not hasattr(self, 'current_image') or not self.current_image:
            messagebox.showwarning("Aviso", "Nenhuma imagem carregada.")
            return
        
        try:
            self.update_status("Processando imagem...")
            
            # Primeiro, detecta e corrige automaticamente a rotação (se habilitado)
            if self.config.get('auto_rotation', True):
                corrected_image, rotation_angle = self.detect_and_correct_rotation(self.current_image)
                
                if abs(rotation_angle) > 1:
                    print(f"[DEBUG] Imagem corrigida automaticamente: {-rotation_angle:.1f}°")
                    # Atualiza a imagem atual com a versão corrigida
                    self.current_image = corrected_image
                    # Atualiza a visualização
                    self.display_image()
                else:
                    corrected_image = self.current_image
            else:
                corrected_image = self.current_image
                print("[DEBUG] Rotação automática desabilitada")
            
            # OCR
            self.update_status("Extraindo texto da imagem...")
            self.progress_bar.start()
            
            # Converte PIL para OpenCV
            cv_image = cv2.cvtColor(np.array(corrected_image), cv2.COLOR_RGB2BGR)
            
            # OCR com EasyOCR
            if self.ocr_reader:
                # Converte PIL para numpy array
                img_array = np.array(self.current_image)
                results = self.ocr_reader.readtext(img_array)
                # Formata o texto de forma estruturada
                formatted_text = self.format_extracted_text(results)
                
                # Calcula confiança média
                confidences = [confidence for (bbox, text, confidence) in results]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                
                # Adiciona metadados se configurado
                if self.config.get("show_metadata", True):
                    self.extracted_text = self.add_text_metadata(formatted_text, results, avg_confidence)
                else:
                    self.extracted_text = formatted_text
                
                # Atualiza confiança
                self.confidence_var.set(f"{avg_confidence:.1%}")
                self.confidence_progress.config(value=avg_confidence*100)
            else:
                self.extracted_text = "Modelo OCR ainda não foi carregado. Aguarde..."
                self.confidence_var.set("N/A")
                self.confidence_progress.config(value=0)
            
            # Atualiza a área de texto
            self.text_area.delete(1.0, tk.END)
            if self.extracted_text:
                # Adiciona formatação visual ao texto
                self.text_area.insert(1.0, self.extracted_text)
                
                # Configura tags para diferentes tipos de texto
                self.text_area.tag_configure("metadata", foreground="#7f8c8d", font=('Consolas', 10, 'italic'))
                self.text_area.tag_configure("content", foreground="#2c3e50", font=('Consolas', 11))
                self.text_area.tag_configure("separator", foreground="#95a5a6", font=('Consolas', 10))
                
                # Aplica formatação baseada no conteúdo
                lines = self.extracted_text.split('\n')
                current_line = 1
                for line in lines:
                    if line.startswith('=') or line.startswith('-'):
                        # Separadores
                        self.text_area.tag_add("separator", f"{current_line}.0", f"{current_line}.end")
                    elif line.startswith('•') or 'Confiança' in line or 'palavras:' in line or 'caracteres:' in line:
                        # Metadados
                        self.text_area.tag_add("metadata", f"{current_line}.0", f"{current_line}.end")
                    else:
                        # Conteúdo principal
                        self.text_area.tag_add("content", f"{current_line}.0", f"{current_line}.end")
                    current_line += 1
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