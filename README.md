# Conversor de Imagem para Texto - Desktop

Aplicação desktop em Python que combina **YOLO** para detecção de objetos e **EasyOCR** para extração de texto de imagens.

## 🚀 Funcionalidades

- ✅ **Múltiplas formas de input**:
  - Arrastar e soltar imagens
  - Colar imagens da área de transferência (Ctrl+V)
  - Seleção manual de arquivos

- ✅ **Processamento avançado**:
  - **OCR (Optical Character Recognition)** com EasyOCR
  - **Detecção de objetos** com YOLO v8
  - Suporte a múltiplos formatos de imagem

- ✅ **Interface moderna**:
  - Interface gráfica intuitiva com Tkinter
  - Abas separadas para OCR e YOLO
  - Preview de imagens centralizado
  - Barra de progresso
  - Design responsivo e moderno

- ✅ **Funcionalidades de saída**:
  - Copiar texto extraído
  - Salvar texto como arquivo .txt
  - Visualização de objetos detectados

## 📋 Pré-requisitos

### 1. Python 3.8+
Certifique-se de ter Python 3.8 ou superior instalado.

### 2. EasyOCR
O EasyOCR será instalado automaticamente via pip junto com as dependências do projeto. Não é necessária instalação manual adicional.

## 🛠️ Instalação

### 1. Clone o repositório
```bash
git clone <url-do-repositorio>
cd imagem-texto
```

### 2. Crie um ambiente virtual local (recomendado)
```bash
python -m venv dependencias
```

### 3. Instale as dependências no ambiente virtual
```bash
# Windows
dependencias\Scripts\python.exe -m pip install -r requirements.txt

# Linux/macOS
dependencias/bin/python -m pip install -r requirements.txt
```

**Ou instale manualmente:**
```bash
# Windows
dependencias\Scripts\python.exe -m pip install tkinterdnd2 pillow opencv-python easyocr numpy matplotlib ultralytics

# Linux/macOS
dependencias/bin/python -m pip install tkinterdnd2 pillow opencv-python easyocr numpy matplotlib ultralytics
```

**Nota:** A primeira execução pode demorar mais, pois:
- O YOLO baixará automaticamente o modelo `yolov8n.pt` (~6MB)
- O EasyOCR baixará os modelos de detecção e reconhecimento de texto (~100MB)

## 🚀 Como usar

### Executar a aplicação

**Opção 1 - Usando o script de inicialização (Windows):**
```bash
executar.bat
```

**Opção 2 - Usando o ambiente virtual diretamente:**
```bash
# Windows
dependencias\Scripts\python.exe app.py

# Linux/macOS
dependencias/bin/python app.py
```

**Opção 3 - Usando Python global (se as dependências estiverem instaladas globalmente):**
```bash
python app.py
```

### Usando a interface

1. **Adicionar imagem**:
   - **Arrastar e soltar**: Arraste uma imagem da pasta para a área de upload
   - **Colar**: Copie uma imagem (Ctrl+C) e cole na aplicação (Ctrl+V)
   - **Selecionar**: Clique em "Selecionar Arquivo" para escolher uma imagem

2. **Visualizar resultados**:
   - **Aba "Texto Extraído (OCR)"**: Mostra o texto encontrado na imagem
   - **Aba "Detecção de Objetos (YOLO)"**: Lista os objetos detectados com nível de confiança

3. **Ações disponíveis**:
   - **Copiar Texto**: Copia o texto extraído para a área de transferência
   - **Salvar como TXT**: Salva o texto em um arquivo
   - **Remover Imagem**: Remove a imagem atual e volta à tela inicial

## 📁 Estrutura do Projeto

```
imagem-texto/
├── app.py              # Aplicação principal
├── requirements.txt    # Dependências Python
├── README.md          # Este arquivo
├── executar.bat       # Script de inicialização (Windows)
├── dependencias/      # Ambiente virtual local
│   ├── Scripts/       # Executáveis do Python (Windows)
│   ├── Lib/          # Bibliotecas instaladas
│   └── ...
├── index.html         # Versão web (opcional)
├── script.js          # JavaScript da versão web
└── styles.css         # Estilos da versão web
```

## 🔧 Dependências Principais

- **tkinter**: Interface gráfica (incluído no Python)
- **tkinterdnd2**: Funcionalidade drag-and-drop
- **Pillow (PIL)**: Manipulação de imagens
- **OpenCV**: Processamento de imagens
- **easyocr**: OCR (Optical Character Recognition) moderno
- **ultralytics**: YOLO v8 para detecção de objetos
- **torch/torchvision**: Backend para YOLO e EasyOCR

## 🎯 Formatos Suportados

- PNG
- JPG/JPEG
- GIF
- BMP
- TIFF
- WEBP

## ⚡ Dicas de Performance

1. **Qualidade da imagem**: Imagens com maior resolução e contraste produzem melhores resultados no OCR
2. **Texto claro**: Textos com fundo contrastante são mais fáceis de detectar
3. **Primeira execução**: O modelo YOLO será baixado automaticamente na primeira vez
4. **Memória**: Para imagens muito grandes, a aplicação pode usar mais RAM durante o processamento

## 🐛 Solução de Problemas

### Erro ao carregar modelos EasyOCR
- Verifique sua conexão com a internet (primeira execução)
- Aguarde o download dos modelos (pode demorar alguns minutos)
- Certifique-se de que há espaço suficiente em disco (~100MB)

### Erro ao carregar modelo YOLO
- Verifique sua conexão com a internet (primeira execução)
- Certifique-se de que o torch está instalado corretamente

### Interface não responde
- O processamento é feito em thread separada, mas imagens muito grandes podem demorar
- Aguarde a conclusão do carregamento dos modelos
- Reinicie a aplicação se necessário

### Erro "Failed loading language"
- Este é um aviso normal do EasyOCR durante a inicialização
- Não afeta o funcionamento da aplicação
- Os modelos serão carregados automaticamente

## 📝 Licença

Este projeto é de código aberto. Sinta-se livre para usar, modificar e distribuir.

## 🤝 Contribuições

Contribuições são bem-vindas! Sinta-se à vontade para:
- Reportar bugs
- Sugerir melhorias
- Enviar pull requests

---

**Desenvolvido com ❤️ usando Python, YOLO e EasyOCR**